from backend.db.connections.milvus import AsyncMilvusDBConnection
from sqlalchemy.ext.asyncio import create_async_engine
from backend.db.models.postgres_models import Base
from dotenv import load_dotenv
from pymilvus import utility
import asyncio
import os

load_dotenv()


async def reset_dbs():
    print("Resetting databases...")

    print("Connecting to Milvus...")
    await AsyncMilvusDBConnection.get_connection()
    collections = ["edu_chunks", "edu_chat_memory"]
    for collection_name in collections:
        if utility.has_collection(collection_name):
            print(f"Dropping Milvus collection '{collection_name}'...")
            utility.drop_collection(collection_name)
        else:
            print(f"Milvus collection '{collection_name}' does not exist.")

    print("Connecting to Postgres...")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_user = os.getenv("DB_USER", "postgres")
        db_pass = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "edu_rag")
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    if "postgresql+asyncpg://" not in db_url:
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    print(f"Connecting to Postgres at {db_host}:{db_port}...")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        print("Dropping Postgres tables (documents, document_chunks)...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Recreating Postgres tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Database reset complete.")


if __name__ == "__main__":
    asyncio.run(reset_dbs())
