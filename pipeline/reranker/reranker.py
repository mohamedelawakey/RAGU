from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from pipeline.config import Config
from dotenv import load_dotenv
import cohere
import os

logger = get_logger("reranker.module")

load_dotenv()
api_key = os.getenv("COHERE_API_KEY")


class Reranker:
    @staticmethod
    def rerank(
        query: str,
        chunks: List[Dict[str, Any]],
        top_n: int = Config.RERANKER_TOP_N
    ) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Reranker: empty query provided.")
            return None

        if not chunks:
            logger.warning("Reranker: no chunks provided to rerank.")
            return []

        if not api_key:
            logger.error("Reranker: COHERE_API_KEY is missing. Cannot rerank.")
            return None

        documents = [chunk["text_content"] for chunk in chunks]

        try:
            logger.info(
                f"Reranker: reranking {len(chunks)} chunks "
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
                    }
                )

            logger.info(
                f"Reranker: successfully reranked to {len(reranked)} top chunks."
            )

            return reranked

        except Exception as e:
            logger.exception(f"Reranker: critical error during reranking: {e}")
            return None
