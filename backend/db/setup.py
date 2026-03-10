from backend.db.models.milvus_collections import get_chunk_schema
from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.utils.logger import get_logger
from pymilvus import Collection, utility
import asyncio
import os

logger = get_logger("milvus.setup")


async def init_milvus_collections():
    try:
        logger.info("Connecting to Milvus...")
        await AsyncMilvusDBConnection.get_connection()

        collection_name = "edu_chunks"

        if utility.has_collection(collection_name):
            logger.info(f"Collection '{collection_name}' already exists.")
        else:
            logger.info(f"Creating Collection '{collection_name}'...")
            schema = get_chunk_schema()
            collection = Collection(name=collection_name, schema=schema)

            hnsw_m = int(os.getenv("HNSW_M", 8))
            hnsw_ef = int(os.getenv("HNSW_EF_CONSTRUCTION", 64))

            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": hnsw_m, "efConstruction": hnsw_ef}
            }

            logger.info(f"Creating index for '{collection_name}'...")
            collection.create_index(field_name="embedding", index_params=index_params)

            logger.info(f"Loading '{collection_name}' into memory...")
            collection.load()
            logger.info("Milvus setup completed successfully!")

    except Exception as e:
        logger.exception(f"Milvus setup failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_milvus_collections())
