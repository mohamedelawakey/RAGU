from backend.db.connections.postgres import PostgresDBConnection
from backend.db.connections.redis import AsyncRedisDBConnection
from backend.config import Config as BackendConfig

from pipeline.retrieval.chat_retriever import ChatMemoryRetriever
from pipeline.prompting.prompt_builder import PromptBuilder
from pipeline.LLM.cohere_client import CohereClient
from pipeline.retrieval.retriever import Retriever
from pipeline.reranker.reranker import Reranker
from typing import Generator, Optional
from utils.logger import get_logger
from pipeline.config import Config

logger = get_logger("rag_pipeline.module")


class RAGPipeline:
    def __init__(self, top_k: int = Config.HYBRID_SEARCH_TOP_K):
        self.retriever = Retriever(top_k=top_k)

    async def query(
        self,
        user_question: str,
        user_id: str,
        session_id: str = None,
        history: list = None
    ) -> Optional[Generator]:
        if not user_question or not user_question.strip():
            logger.warning("RAGPipeline: empty question received.")
            return None

        doc_count = 0
        try:
            logger.info("RAGPipeline: Connecting to Postgres...")
            async with PostgresDBConnection.get_db_connection() as conn:
                logger.info(
                    "RAGPipeline: Postgres connection acquired. "
                    "Fetching..."
                )
                doc_count = await conn.fetchval(
                    BackendConfig.CHECK_USER_DOCUMENT_QUOTA_QUERY,
                    user_id
                )
                logger.info(f"RAGPipeline: Doc Count: {doc_count}")
        except Exception as e:
            logger.error(
                f"RAGPipeline: Error checking document count: {e}"
            )

        redis_client = None
        query_count = 0
        if doc_count == 0:
            try:
                logger.info("RAGPipeline: Connecting to Redis...")
                redis_client = await AsyncRedisDBConnection.get_connection()
                logger.info(
                    "RAGPipeline: Redis connection acquired. "
                    "Fetching..."
                )
                query_count_str = await redis_client.get(
                    f"user:{user_id}:queries_count"
                )
                query_count = (
                    int(query_count_str) if query_count_str else 0
                )
                logger.info(f"RAGPipeline: Query Count: {query_count}")
            except Exception as e:
                logger.error(
                    f"RAGPipeline: Error checking Redis queries count: {e}"
                )

        if query_count >= 3:
            logger.warning(
                f"RAGPipeline: User '{user_id}' "
                "exceeded general QA limit."
            )
            raise ValueError("RATE_LIMIT_EXCEEDED")

        search_query = user_question
        if history and len(history) > 0:
            logger.info(
                "RAGPipeline: Attempting to reformulate query contextually..."
            )
            try:
                import asyncio
                search_query = await asyncio.to_thread(
                    CohereClient.reformulate_query,
                    user_question,
                    history
                )
            except Exception as e:
                logger.error(
                    f"RAGPipeline: Reformulation failed, "
                    f"using raw query: {e}"
                )

        logger.info(
            f"RAGPipeline: [1/4] Retrieving relevant chunks for "
            f"user '{user_id}'..."
        )
        chunks = await self.retriever.retrieve(search_query, user_id)

        if chunks is None:
            logger.error("RAGPipeline: Retriever failed (backend error).")
        if not chunks and doc_count == 0:
            logger.info(
                "RAGPipeline: User has 0 documents, using general knowledge QA."
            )
            if redis_client:
                try:
                    await redis_client.incr(f"user:{user_id}:queries_count")
                except Exception as e:
                    logger.error(
                        f"RAGPipeline: Error incrementing Redis query "
                        f"count: {e}"
                    )

            reranked = []
            context = ""
        else:
            if not chunks:
                logger.info(
                    "RAGPipeline: No relevant chunks found. "
                    "Passing to LLM to handle identity/greetings "
                    "or reject."
                )
                reranked = []
            else:
                logger.info("RAGPipeline: [2/4] Reranking chunks...")
                reranked = Reranker.rerank(user_question, chunks)

                if reranked is None:
                    logger.error(
                        "RAGPipeline: Reranker failed. "
                        "Falling back to raw retrieval order."
                    )
                    reranked = chunks

                if not reranked:
                    logger.warning("RAGPipeline: Reranker returned empty list.")
                    reranked = []

            context = "\n\n".join(
                chunk["text_content"] for chunk in reranked
            )

        logger.info("RAGPipeline: [3/4] Building prompt...")

        long_term_memory_context = ""
        exclude_ids = [msg["id"] for msg in (history or [])]
        if session_id:
            chat_retriever = ChatMemoryRetriever()
            memory_hits = await chat_retriever.search_memory(
                search_query,
                user_id,
                session_id,
                exclude_message_ids=exclude_ids,
                top_k=10
            )
            if memory_hits:
                memory_blocks = []
                for hit in memory_hits:
                    memory_blocks.append(
                        f"[{hit['role'].upper()}]: {hit['content']}"
                    )
                long_term_memory_context = "\n\n".join(memory_blocks)

        system_context = ""
        if long_term_memory_context:
            system_context += (
                "### PREVIOUS CONVERSATION CONTEXT (LONG-TERM MEMORY):\n"
            )
            system_context += (
                "Use the following previous semantic chat messages to "
                "provide context if needed:\n"
            )
            system_context += long_term_memory_context + "\n\n"

        if context:
            system_context += "### RELEVANT DOCUMENT CONTEXT:\n"
            system_context += context

        try:
            messages = PromptBuilder.build(
                user_question=user_question,
                context=system_context,
                history=history
            )
        except ValueError as e:
            logger.error(
                f"RAGPipeline: PromptBuilder failed: {e}"
            )
            return None

        try:
            import asyncio
            return await asyncio.to_thread(
                CohereClient.cohere_chat, messages
            )
        except Exception as e:
            logger.exception(
                f"RAGPipeline: CohereClient failed to generate "
                f"response: {e}"
            )

            return None
