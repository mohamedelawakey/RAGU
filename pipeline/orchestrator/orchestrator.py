from pipeline.prompting.prompt_builder import PromptBuilder
from pipeline.LLM.cohere_client import CohereClient
from pipeline.retrieval.retriever import Retriever
from pipeline.reranker.reranker import Reranker
from pipeline.config import Config
from typing import Generator, Optional
from utils.logger import get_logger

logger = get_logger("rag_pipeline.module")


class RAGPipeline:
    def __init__(self, top_k: int = Config.HYBRID_SEARCH_TOP_K):
        self.retriever = Retriever(top_k=top_k)

    async def query(self, user_question: str, user_id: str) -> Optional[Generator]:
        if not user_question or not user_question.strip():
            logger.warning("RAGPipeline: empty question received.")
            return None

        logger.info(f"RAGPipeline: [1/4] Retrieving relevant chunks for user '{user_id}'...")
        chunks = await self.retriever.retrieve(user_question, user_id)

        if chunks is None:
            logger.error("RAGPipeline: Retriever failed (backend error).")
            return None 

        if not chunks:
            logger.warning("RAGPipeline: No relevant chunks found for the query.")
            return None

        logger.info("RAGPipeline: [2/4] Reranking chunks...")
        reranked = Reranker.rerank(user_question, chunks)

        if reranked is None:
            logger.error("RAGPipeline: Reranker failed. Falling back to raw retrieval order.")
            reranked = chunks

        if not reranked:
            logger.warning("RAGPipeline: Reranker returned empty list.")
            return None

        logger.info("RAGPipeline: [3/4] Building prompt...")
        context = Config.CONTEXT_SEPARATOR.join(
            chunk["text_content"] for chunk in reranked
        )

        try:
            prompt = PromptBuilder.build(
                user_question=user_question,
                context=context
            )
        except ValueError as e:
            logger.error(f"RAGPipeline: PromptBuilder failed: {e}")
            return None

        logger.info("RAGPipeline: [4/4] Streaming LLM response...")
        try:
            return CohereClient.cohere_chat(prompt)
        except Exception:
            logger.exception("RAGPipeline: CohereClient failed to generate response.")
            return None
