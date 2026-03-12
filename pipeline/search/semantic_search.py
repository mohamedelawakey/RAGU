from backend.db.connections.milvus import AsyncMilvusDBConnection
from pipeline.embeddings.embedding import Embedding
from typing import List, Dict, Any, Optional
from pymilvus import Collection, utility
from . import get_logger
from . import Config

logger = get_logger("semantic_search.module")


class SemanticSearch:
    def __init__(
        self,
        collection_name: str = Config.COLLECTION_NAME,
        top_k: int = Config.SEMANTIC_SEARCH_TOP_K
    ):
        self.collection_name = collection_name
        self.top_k = top_k
        self.search_params = {
            "metric_type": Config.SEARCH_PARAMS_METRIC_TYPE,
            "params": {
                "nprobe": Config.SEARCH_PARAMS_NPROBE
            }
        }

    async def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        if not query or not query.strip():
            logger.warning("Empty query provided for semantic search.")
            return []

        logger.info(f"Starting semantic search for query: '{query}'")

        logger.info("Generating embedding for the query...")
        query_embedding = Embedding.embed([query])

        if not query_embedding or len(query_embedding) == 0:
            logger.error("Failed to generate embedding for the search query.")
            return None

        vector_to_search = query_embedding[0]

        try:
            logger.info("Connecting to Milvus for vector search...")
            await AsyncMilvusDBConnection.get_connection()

            if not utility.has_collection(self.collection_name):
                logger.error(f"Milvus collection '{self.collection_name}' does not exist.")
                return None

            collection = Collection(self.collection_name)

            collection.load()

            logger.info("Executing search query in Milvus...")
            results = collection.search(
                data=[vector_to_search],
                anns_field="embedding",
                param=self.search_params,
                limit=self.top_k,
                output_fields=["chunk_id", "document_id"]
            )

            if not results or len(results) == 0:
                logger.info("No semantic matches found in Milvus.")
                return []

            search_hits = results[0]
            chunk_ids = []
            milvus_scores = {}

            for hit in search_hits:
                chunk_id = hit.entity.get('chunk_id')
                chunk_ids.append(chunk_id)
                milvus_scores[chunk_id] = hit.distance

            if not chunk_ids:
                return []

            logger.info(f"Found {len(chunk_ids)} semantic matches in Milvus.")

            final_results = []
            for chunk_id in chunk_ids:
                final_results.append({
                    "chunk_id": chunk_id,
                    "score": milvus_scores.get(chunk_id, 0.0)
                })

            final_results.sort(key=lambda x: x['score'], reverse=True)
            return final_results

        except Exception as e:
            logger.exception(f"Error during semantic search process: {e}")
            return None
