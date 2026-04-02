from backend.db.connections.milvus import AsyncMilvusDBConnection
from backend.db.connections.postgres import PostgresDBConnection
from backend.db.connections.redis import AsyncRedisDBConnection
from backend.core.rate_limit import init_rate_limiter
from backend.api.middlewares import setup_middlewares
from backend.db.models.milvus_collections import (
    get_chat_memory_schema,
    get_chunk_schema
)
from backend.api.base_router import api_router
from contextlib import asynccontextmanager
from backend.config import Config
from utils.logger import get_logger
from fastapi import FastAPI

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    logger.info("Initializing backend services...")

    await PostgresDBConnection.init_pool()
    logger.info("Postgres pool ready.")

    await AsyncRedisDBConnection.get_connection()
    logger.info("Redis connection ready.")

    await init_rate_limiter()
    logger.info("Rate limiter initialized.")

    await AsyncMilvusDBConnection.initialize_collection(
        Config.DOC_COLLECTION_NAME, get_chunk_schema()
    )
    await AsyncMilvusDBConnection.initialize_collection(
        Config.CHAT_MEMORY_COLLECTION_NAME, get_chat_memory_schema()
    )
    logger.info("Milvus collections initialized.")

    logger.info("All services initialized successfully.")

    yield

    # ── Shutdown ──
    logger.info("Shutting down backend services...")

    await PostgresDBConnection.close_pool()
    logger.info("Postgres pool closed.")

    await AsyncRedisDBConnection.close()
    logger.info("Redis connection closed.")

    logger.info("All services shut down cleanly.")


app = FastAPI(
    title="EDU RAG API",
    description="Educational RAG Platform Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middlewares ──
setup_middlewares(app)

# ── Routers ──
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}
