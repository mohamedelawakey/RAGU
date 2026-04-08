from backend.db.models.milvus_collections import (
    get_chunk_schema,
    get_chat_memory_schema
)
from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from pymilvus import Collection, utility
from utils.logger import get_logger
import asyncio

logger = get_logger("milvus.setup")


async def init_milvus_collections():
    try:
        logger.info("Connecting to Milvus...")
        from backend.config import Config
        await AsyncMilvusDBConnection.get_connection()

        collection_name = Config.DOC_COLLECTION_NAME
        index_params = {
            "metric_type": Config.MILVUS_METRIC_TYPE,
            "index_type": Config.MILVUS_INDEX_TYPE,
            "params": {
                "M": Config.MILVUS_HNSW_M,
                "efConstruction": Config.MILVUS_HNSW_EF_CONSTRUCTION
            }
        }

        if utility.has_collection(collection_name):
            logger.info(f"Collection '{collection_name}' already exists.")
        else:
            logger.info(f"Creating Collection '{collection_name}'...")
            schema = get_chunk_schema()
            collection = Collection(name=collection_name, schema=schema)
            logger.info(f"Creating index for '{collection_name}'...")
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            logger.info(f"Loading '{collection_name}' into memory...")
            collection.load()

        chat_collection = Config.CHAT_MEMORY_COLLECTION_NAME
        if utility.has_collection(chat_collection):
            logger.info(f"Collection '{chat_collection}' already exists.")
        else:
            logger.info(f"Creating Collection '{chat_collection}'...")
            schema = get_chat_memory_schema()
            collection = Collection(name=chat_collection, schema=schema)
            logger.info(f"Creating index for '{chat_collection}'...")
            collection.create_index(
                field_name="embedding",
                index_params=index_params
            )
            logger.info(f"Loading '{chat_collection}' into memory...")
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

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id VARCHAR(100) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id VARCHAR(100) PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)

            logger.info("Postgres setup (extensions, indexes, and chat tables) completed successfully!")
    except Exception as e:
        logger.exception(f"Postgres setup failed: {e}")
        raise


async def run_setup():
    await init_milvus_collections()
    await init_postgres_db()


if __name__ == "__main__":
    asyncio.run(run_setup())
