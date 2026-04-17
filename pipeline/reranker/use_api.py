from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from pipeline.config import Config
import cohere
import os

logger = get_logger("reranker.api")


class ApiReranker:
    @staticmethod
    def rerank(
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int
    ) -> Optional[List[Dict[str, Any]]]:
        api_key = os.getenv("COHERE_API_KEY")
        if not api_key:
            logger.error(
                "Reranker [API]: COHERE_API_KEY is missing. Cannot rerank."
            )
            return None

        documents = [chunk["text_content"] for chunk in chunks]

        try:
            logger.info(
                f"Reranker [API]: reranking {len(chunks)} chunks "
                f"(top_n={top_n}) using '{Config.RERANKER_MODEL}'..."
            )

            co = cohere.ClientV2(api_key=api_key)
            response = co.rerank(
                model=Config.RERANKER_MODEL,
                query=query,
                documents=documents,
                top_n=top_n,
            )

            reranked = []
            for result in response.results:
                original_chunk = chunks[result.index]
                reranked.append(
                    {
                        "chunk_id": original_chunk["chunk_id"],
                        "rrf_score": original_chunk["score"],
                        "rerank_score": result.relevance_score,
                        "text_content": original_chunk["text_content"],
                        "filename": original_chunk.get("filename", "Unknown"),
                    }
                )

            logger.info(
                f"Reranker [LOCAL]: successfully reranked to "
                f"{len(reranked)} top chunks."
            )
            return reranked

        except Exception as e:
            logger.exception(
                f"Reranker [API]: critical error during reranking: {e}"
            )
            return None
