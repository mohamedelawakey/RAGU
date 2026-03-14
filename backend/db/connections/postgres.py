from contextlib import asynccontextmanager
from backend.config import Config
from . import get_logger
import asyncpg
import asyncio

logger = get_logger("postgres.module")


class PostgresDBConnection:
    _pool = None
    _lock = asyncio.Lock()

    @classmethod
    async def init_pool(cls):

        if cls._pool is None:
            async with cls._lock:
                if cls._pool is None:
                    try:
                        cls._pool = await asyncpg.create_pool(
                            user=Config.DB_USER,
                            password=Config.DB_PASSWORD,
                            database=Config.DB_NAME,
                            host=Config.DB_HOST,
                            port=Config.DB_PORT,
                            min_size=Config.MIN_CONNECTIONS,
                            max_size=Config.MAX_CONNECTIONS,
                        )
                        logger.info("Async PostgreSQL connection pool initialized")
                    except Exception:
                        logger.exception("Error initializing Async PostgreSQL connection pool")
                        raise

    @classmethod
    async def close_pool(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Async PostgreSQL connection pool closed")

    @classmethod
    @asynccontextmanager
    async def get_db_connection(cls):
        if cls._pool is None:
            await cls.init_pool()

        async with cls._pool.acquire() as conn:
            async with conn.transaction():
                yield conn
