from backend.db.connections.postgres import PostgresDBConnection
from typing import List, Dict, Any, Optional
from pipeline import get_logger
from pipeline import Config

logger = get_logger("bm25_search.module")


class BM25Search:
    def __init__(self, top_k: int = Config.BM25_TOP_K):
        self.top_k = top_k

    async def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided for BM25 search.")
            return []

        logger.info(f"Starting BM25 search for query: '{query}'")

        try:
            logger.info("Executing full-text search query in Postgres...")

            async with PostgresDBConnection.get_db_connection() as conn:
                sql_query = Config.BM25_QUERY

                rows = await conn.fetch(sql_query, query, self.top_k)

                if not rows:
                    logger.info("No lexical matches found in Postgres.")
                    return []

                final_results = []
                for row in rows:
                    final_results.append(
                        {
                            "chunk_id": row['chunk_id'],
                            "score": row['rank_score']
                        }
                    )

                logger.info(f"Successfully retrieved {len(final_results)} BM25 result IDs.")
                return final_results

        except Exception as e:
            logger.exception(f"Error during BM25 search process: {e}")
            return None
