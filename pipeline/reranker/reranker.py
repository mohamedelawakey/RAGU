from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from pipeline.config import Config
from pipeline.reranker.use_api import ApiReranker
from pipeline.reranker.use_local import LocalReranker

logger = get_logger("reranker.module")


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

        if Config.USE_LOCAL_RERANKER:
            return LocalReranker.rerank(query, chunks, top_n)
        else:
            return ApiReranker.rerank(query, chunks, top_n)
