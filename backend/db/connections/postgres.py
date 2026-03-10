import asyncpg
import asyncio
from . import get_logger
from contextlib import asynccontextmanager
from backend.config import Config

logger = get_logger("postgres.module")


class PostgresDBConnection:
    _pool = None
    _lock = None

    @classmethod
    async def init_pool(cls):
        """
        Ensure the class-level asyncpg connection pool is created and stored on first use.
        
        Initializes an asyncio.Lock if needed, then creates a singleton asyncpg pool using configuration values and assigns it to `cls._pool`. Logs successful initialization; any exception raised by pool creation is propagated.
        Raises:
            Exception: If creating the asyncpg connection pool fails.
        """
        if cls._lock is None:
            cls._lock = asyncio.Lock()

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
                    except Exception as e:
                        logger.error(f"Error initializing Async PostgreSQL connection pool: {e}")
                        raise

    @classmethod
    async def close_pool(cls):
        """
        Close the class-level asyncpg connection pool if one exists.
        
        If a pool is present, it is closed and the action is logged; if no pool exists, the call does nothing.
        """
        if cls._pool:
            await cls._pool.close()
            logger.info("Async PostgreSQL connection pool closed")

    @classmethod
    @asynccontextmanager
    async def get_db_connection(cls):
        """
        Provide a pooled asyncpg connection to use within an automatic transaction scope.
        
        Ensures the connection pool is initialized, acquires a connection from the pool, and yields it inside an open transaction. The transaction will be committed if the caller exits normally or rolled back if an exception is raised.
        
        Returns:
            conn: An asyncpg connection object yielded inside an active transaction.
        """
        if cls._pool is None:
            await cls.init_pool()

        async with cls._pool.acquire() as conn:
            async with conn.transaction():
                yield conn
