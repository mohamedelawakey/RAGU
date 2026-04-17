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

    async def _get_fallback(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Retriever: Triggering fallback for user {user_id}...")
            async with PostgresDBConnection.get_db_connection() as conn:
                rows = await conn.fetch(
                    Config.RETRIEVER_FALLBACK_QUERY,
                    user_id,
                    Config.RETRIEVER_FALLBACK_LIMIT
                )
                if rows:
                    logger.info(
                        f"Retriever: Fallback successful. Retrieved {len(rows)} chunks."
                    )
                    return [
                        {
                            "chunk_id": row["id"],
                            "score": Config.RETRIEVER_FALLBACK_SCORE,
                            "text_content": row["text_content"].strip(),
                            "filename": row.get("filename", "Unknown")
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Retriever: Fallback failed: {e}")
        return []

    async def retrieve(
        self,
        query: str,
        user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided to Retriever.")
            return []

        logger.info(
            f"Retriever: running hybrid search "
            f"[query_length={len(query)}, user_id={user_id}]"
        )
        search_results = await self.hybrid_search.search(query, user_id)

        if search_results is None:
            logger.error("Retriever: hybrid search returned None (backend failure).")
            return None

        if not search_results:
            logger.info("Retriever: no relevant chunks found in index. Falling back...")
            return await self._get_fallback(user_id)

        ranked_chunk_ids: List[str] = [r["chunk_id"] for r in search_results]
        score_by_id: Dict[str, float] = {r["chunk_id"]: r["score"] for r in search_results}

        logger.info(f"Retriever: fetching text for {len(ranked_chunk_ids)} chunks from Postgres... IDs: {list(ranked_chunk_ids)[:5]}...")
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
            logger.warning("Retriever: Milvus matches not found in Postgres (Sync Issue). Falling back...")
            return await self._get_fallback(user_id)

        text_by_id: Dict[str, str] = {row["id"]: row["text_content"] for row in rows}
        filename_by_id: Dict[str, str] = {
            row["id"]: row.get("filename", "Unknown") for row in rows
        }

        chunks = []
        for chunk_id in ranked_chunk_ids:
            text = text_by_id.get(chunk_id)
            if not text:
                continue

            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "score": score_by_id[chunk_id],
                    "text_content": text.strip(),
                    "filename": filename_by_id.get(chunk_id, "Unknown")
                }
            )

        logger.info(f"Retriever: returned {len(chunks)} chunks ready for reranking.")
        return chunks
