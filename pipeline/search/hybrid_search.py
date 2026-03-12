from typing import List, Dict, Any, Optional
from .semantic_search import SemanticSearch
from .bm25_search import BM25Search
from pipeline.config import Config
from pipeline import get_logger
import asyncio

logger = get_logger("hybrid_search.module")


class HybridSearch:
    def __init__(
        self,
        top_k: int = Config.HYBRID_SEARCH_TOP_K,
        rrf_k: int = Config.RRF_K
    ):
        self.semantic_search = SemanticSearch()
        self.bm25_search = BM25Search()
        self.top_k = top_k
        self.rrf_k = rrf_k

    async def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided for hybrid search.")
            return []

        logger.info(f"Starting hybrid search (Semantic + BM25) for query: '{query}'")

        try:
            semantic_results_task = self.semantic_search.search(query)
            bm25_results_task = self.bm25_search.search(query)

            semantic_results, bm25_results = await asyncio.gather(
                semantic_results_task,
                bm25_results_task
            )

            if semantic_results is None: 
                semantic_results = []
            if bm25_results is None: 
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
