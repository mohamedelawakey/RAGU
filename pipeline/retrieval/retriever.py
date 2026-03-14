from backend.db.connections.postgres import PostgresDBConnection
from pipeline.search.hybrid_search import HybridSearch
from typing import List, Dict, Any, Optional
from utils.logger import get_logger
from pipeline.config import Config

logger = get_logger("retriever.module")


class Retriever:
    def __init__(
        self,
        top_k: int = Config.HYBRID_SEARCH_TOP_K
    ):
        self.hybrid_search = HybridSearch(top_k=top_k)

    async def retrieve(
        self,
        query: str,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided to Retriever.")
            return []

        logger.info(f"Retriever: running hybrid search [query_length={len(query)}, user_id={user_id}]")
        search_results = await self.hybrid_search.search(query, user_id)

        if search_results is None:
            logger.error("Retriever: hybrid search returned None (backend failure).")
            return None

        if not search_results:
            logger.info("Retriever: no relevant chunks found for the query.")
            return []

        ranked_chunk_ids: List[str] = [r["chunk_id"] for r in search_results]
        score_by_id: Dict[str, float] = {r["chunk_id"]: r["score"] for r in search_results}

        logger.info(f"Retriever: fetching text for {len(ranked_chunk_ids)} chunks from Postgres...")
        try:
            async with PostgresDBConnection.get_db_connection() as conn:
                rows = await conn.fetch(
                    Config.FETCH_CHUNKS_BY_IDS,
                    list(ranked_chunk_ids)
                )
        except Exception:
            logger.exception("Retriever: failed to fetch chunk text from Postgres.")
            return None

        if not rows:
            logger.warning("Retriever: no rows returned from Postgres for the chunk IDs.")
            return []

        text_by_id: Dict[str, str] = {row["id"]: row["text_content"] for row in rows}

        chunks = []
        for chunk_id in ranked_chunk_ids:
            text = text_by_id.get(chunk_id)
            if not text:
                logger.warning(f"Retriever: no text found for chunk_id '{chunk_id}'. Skipping.")
                continue

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "score": score_by_id[chunk_id],
                    "text_content": text.strip()
                }
            )

        logger.info(f"Retriever: returned {len(chunks)} chunks ready for reranking.")
        return chunks
