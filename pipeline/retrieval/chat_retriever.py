from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from pipeline.embeddings.query_embedding import QueryEmbedding
from pipeline.config import Config as PConfig
from utils.logger import get_logger
from typing import List, Dict, Any
from backend.config import Config
from pymilvus import Collection
import asyncio

logger = get_logger("chat_retriever.module")


class ChatMemoryRetriever:
    def __init__(self):
        self.collection_name = Config.CHAT_MEMORY_COLLECTION_NAME

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def insert_memory(
        self,
        message_id: str,
        session_id: str,
        user_id: str,
        role: str,
        content: str
    ) -> bool:
        if not content or not content.strip():
            return False

        try:
            logger.info(f"ChatMemoryRetriever: Embedding '{role}' message (ID: {message_id}).")
            text_to_embed = f"{role}: {content}"
            embedding = await self._run_in_executor(QueryEmbedding.embed_query, text_to_embed)

            if not embedding:
                logger.error("ChatMemoryRetriever: Model failed to emit valid array.")
                return False

            await AsyncMilvusDBConnection.get_connection()
            collection = await self._run_in_executor(Collection, self.collection_name)

            data = [
                [message_id],
                [session_id],
                [user_id],
                [embedding]
            ]

            await self._run_in_executor(collection.insert, data)
            logger.info(f"ChatMemoryRetriever: Vector inserted successfully '{message_id}'.")
            return True
        except Exception as e:
            logger.exception(f"ChatMemoryRetriever: Failed to construct vector memory: {e}")
            return False

    async def search_memory(
        self,
        query: str,
        user_id: str,
        session_id: str,
        exclude_message_ids: List[str] = None,
        top_k: int = PConfig.CHAT_RETRIEVER_TOP_K
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        try:
            logger.info(f"ChatMemoryRetriever: Probing semantic memory for '{user_id}'...")
            query_embedding = await self._run_in_executor(QueryEmbedding.embed_query, query)

            if not query_embedding:
                logger.error("ChatMemoryRetriever: Failed to embed contextual query.")
                return []

            await AsyncMilvusDBConnection.get_connection()
            collection = await self._run_in_executor(Collection, self.collection_name)
            await self._run_in_executor(collection.load)

            search_params = {
                "metric_type": PConfig.CHAT_RETRIEVER_METRIC_TYPE,
                "params": {"ef": PConfig.CHAT_RETRIEVER_EF}
            }

            expr = f"user_id == '{user_id}'"
            if exclude_message_ids:
                ids_str = ", ".join([f"'{mid}'" for mid in exclude_message_ids])
                expr += f" and message_id not in [{ids_str}]"

            results = await self._run_in_executor(
                collection.search,
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=expr,
                output_fields=["message_id", "session_id", "user_id"]
            )

            if not results or not results[0]:
                return []

            hits = results[0]
            if len(hits) == 0:
                return []

            message_ids = [hit.entity.get("message_id") for hit in hits]

            async with PostgresDBConnection.get_db_connection() as conn:
                rows = await conn.fetch(
                    PConfig.FETCH_CHAT_MESSAGES_QUERY,
                    message_ids
                )

            text_by_id = {
                row["id"]: {
                    "role": row["role"],
                    "content": row["content"],
                    "session_id": row["session_id"]
                } for row in rows
            }

            memory_chunks = []
            for hit in hits:
                msg_id = hit.entity.get("message_id")
                score = hit.distance
                if msg_id in text_by_id:
                    memory_chunks.append({
                        "message_id": msg_id,
                        "session_id": text_by_id[msg_id]["session_id"],
                        "role": text_by_id[msg_id]["role"],
                        "content": text_by_id[msg_id]["content"],
                        "score": score
                    })

            return memory_chunks

        except Exception as e:
            logger.exception(f"ChatMemoryRetriever: Exception triggered searching semantic graphs: {e}")
            return []
