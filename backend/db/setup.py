from backend.db.models.milvus_collections import get_chunk_schema
from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from pymilvus import Collection, utility
from utils.logger import get_logger
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


async def init_postgres_db():
    try:
        logger.info("Connecting to Postgres for setup...")
        async with PostgresDBConnection.get_db_connection() as conn:
            logger.info("Creating pg_trgm extension if it doesn't exist...")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

            logger.info("Creating GIN indexes on document_chunks table...")

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_text_tsvector 
                ON document_chunks USING GIN(to_tsvector('simple', text_content));
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_text_trgm 
                ON document_chunks USING GIN(text_content gin_trgm_ops);
            """)

            logger.info("Postgres setup (extensions and indexes) completed successfully!")
    except Exception as e:
        logger.exception(f"Postgres setup failed: {e}")
        raise


async def run_setup():
    await init_milvus_collections()
    await init_postgres_db()


if __name__ == "__main__":
    asyncio.run(run_setup())
