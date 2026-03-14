from typing import List, Dict, Any, Optional
from .semantic_search import SemanticSearch
from .bm25_search import BM25Search
from utils.logger import get_logger
from pipeline.config import Config
import asyncio

logger = get_logger("hybrid_search.module")


class HybridSearch:
    def __init__(
        self,
        top_k: int = Config.HYBRID_SEARCH_TOP_K,
        rrf_k: int = Config.RRF_K
    ):
        self.semantic_search = SemanticSearch(top_k=top_k)
        self.bm25_search = BM25Search(top_k=top_k)
        self.top_k = top_k
        self.rrf_k = rrf_k

    async def search(self, query: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided for hybrid search.")
            return []

        logger.info(f"Starting hybrid search (Semantic + BM25) [query_length={len(query)}]")

        try:
            semantic_results_task = self.semantic_search.search(query, user_id)
            bm25_results_task = self.bm25_search.search(query, user_id)

            semantic_results, bm25_results = await asyncio.gather(
                semantic_results_task,
                bm25_results_task
            )

            if semantic_results is None and bm25_results is None:
                logger.error("Hybrid search failed: both Semantic and BM25 backends returned None.")
                return None

            if semantic_results is None:
                logger.warning("Semantic search backend failed (returned None). Proceeding with BM25 results only.")
                semantic_results = []

            if bm25_results is None:
                logger.warning("BM25 search backend failed (returned None). Proceeding with Semantic results only.")
                bm25_results = []

            rrf_scores: Dict[str, float] = {}

            for rank, result in enumerate(semantic_results, start=1):
                chunk_id = result["chunk_id"]
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

            for rank, result in enumerate(bm25_results, start=1):
                chunk_id = result["chunk_id"]
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

            sorted_results = sorted(
                rrf_scores.items(),
                key=lambda item: item[1],
                reverse=True
            )

            final_results = []
            for chunk_id, score in sorted_results[:self.top_k]:
                final_results.append({
                    "chunk_id": chunk_id,
                    "score": score
                })

            logger.info(f"Hybrid search completed. Found {len(final_results)} fused results.")
            return final_results

        except Exception as e:
            logger.exception(f"Error during hybrid search process: {e}")
            return None
