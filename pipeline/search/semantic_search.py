from backend.db.connections.milvus import AsyncMilvusDBConnection
from typing import ClassVar, List, Dict, Any, Optional, Set
from pipeline.embeddings.query_embedding import QueryEmbedding
from pymilvus import Collection, utility
from utils.logger import get_logger
from pipeline.config import Config
import asyncio

logger = get_logger("semantic_search.module")


class SemanticSearch:
    _loaded_collections: ClassVar[Set[str]] = set()
    _load_locks: ClassVar[Dict[str, asyncio.Lock]] = {}

    def __init__(
        self,
        collection_name: str = Config.COLLECTION_NAME,
        top_k: int = Config.SEMANTIC_SEARCH_TOP_K,
        alias: str = Config.MILVUS_ALIAS
    ):
        self.collection_name = collection_name
        self.top_k = top_k
        self.alias = alias
        self.search_params = {
            "metric_type": Config.SEARCH_PARAMS_METRIC_TYPE,
            "params": {
                "ef": Config.SEARCH_PARAMS_EF
            }
        }

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def search(self, query: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided for semantic search.")
            return []

        logger.info(f"Starting semantic search [query_length={len(query)}]")

        try:
            logger.info("Generating embedding for the query...")
            query_embedding_vector = await self._run_in_executor(QueryEmbedding.embed_query, query)

            if not query_embedding_vector or len(query_embedding_vector) == 0:
                logger.error("Failed to generate embedding for the search query.")
                return None

            vector_to_search = query_embedding_vector

            logger.info("Connecting to Milvus for vector search...")
            await AsyncMilvusDBConnection.get_connection(alias=self.alias)

            exists = await self._run_in_executor(utility.has_collection, self.collection_name, using=self.alias)
            if not exists:
                logger.error(f"Milvus collection '{self.collection_name}' does not exist on alias '{self.alias}'.")
                return None

            collection = await self._run_in_executor(Collection, self.collection_name, using=self.alias)

            if self.collection_name not in SemanticSearch._load_locks:
                SemanticSearch._load_locks[self.collection_name] = asyncio.Lock()

            async with SemanticSearch._load_locks[self.collection_name]:
                if self.collection_name not in SemanticSearch._loaded_collections:
                    logger.info(f"Loading collection '{self.collection_name}' into memory (first time)...")
                    await self._run_in_executor(collection.load)
                    SemanticSearch._loaded_collections.add(self.collection_name)

            logger.info("Executing search query in Milvus...")
            results = await self._run_in_executor(
                collection.search,
                data=[vector_to_search],
                anns_field="embedding",
                param=self.search_params,
                limit=self.top_k,
                expr=f"user_id == '{user_id}'",
                output_fields=["chunk_id", "document_id"]
            )

            if not results or len(results) == 0:
                logger.info("No semantic matches found in Milvus.")
                return []

            search_hits = results[0]
            chunk_ids = []
            milvus_scores = {}

            for hit in search_hits:
                chunk_id = hit.entity.get('chunk_id')
                if chunk_id is None:
                    logger.warning("Skipping Milvus hit with missing chunk_id.")
                    continue
                chunk_ids.append(chunk_id)
                milvus_scores[chunk_id] = hit.distance

            if not chunk_ids:
                return []

            logger.info(f"Found {len(chunk_ids)} semantic matches in Milvus.")

            final_results = []
            for chunk_id in chunk_ids:
                final_results.append({
                    "chunk_id": chunk_id,
                    "score": milvus_scores.get(chunk_id, 0.0)
                })

            metric_type = str(self.search_params.get("metric_type", "")).upper()
            higher_is_better = metric_type in {"IP", "COSINE"}
            final_results.sort(key=lambda x: x["score"], reverse=higher_is_better)
            return final_results

        except Exception as e:
            logger.exception(f"Error during semantic search process: {e}")
            return None
