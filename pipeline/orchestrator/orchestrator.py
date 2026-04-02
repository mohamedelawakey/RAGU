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
        history: list = None,
        doc_count: int = 0
    ) -> Optional[Generator]:
        if not user_question or not user_question.strip():
            logger.warning("RAGPipeline: empty question received.")
            return None

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
        exclude_ids = [msg.get("message_id") or msg.get("id") for msg in (history or []) if (msg.get("message_id") or msg.get("id"))]
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
