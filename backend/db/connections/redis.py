from . import get_logger
from backend.config import Config
import asyncio
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from redis.asyncio import Redis, ConnectionPool

logger = get_logger("redis.module")


class AsyncRedisDBConnection:
    _instance: Redis | None = None
    _pool: ConnectionPool | None = None
    _lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    async def get_connection(
        retries: int = Config.REDIS_RETRIES,
        retry_delay: float = Config.REDIS_RETRY_DELAY
    ) -> Redis:

        if AsyncRedisDBConnection._instance:
            return AsyncRedisDBConnection._instance

        async with AsyncRedisDBConnection._lock:
            if AsyncRedisDBConnection._instance:
                return AsyncRedisDBConnection._instance

            try:
                if AsyncRedisDBConnection._pool is None:
                    AsyncRedisDBConnection._pool = ConnectionPool(
                        host=Config.REDIS_HOST,
                        port=Config.REDIS_PORT,
                        db=Config.REDIS_DB,
                        password=Config.REDIS_PASSWORD,
                        decode_responses=True,
                        max_connections=Config.MAX_CONNECTIONS,
                        retry_on_timeout=True
                    )

                attempt = 0
                while attempt < retries:
                    try:
                        redis = Redis(
                            connection_pool=AsyncRedisDBConnection._pool
                        )
                        await redis.ping()

                        AsyncRedisDBConnection._instance = redis
                        logger.info("Connected to Redis (async) successfully")

                        return redis

                    except (RedisError, RedisConnectionError) as e:
                        attempt += 1
                        logger.warning(
                            f"Async Redis connection attempt {attempt}/{retries} failed: {e}"
                        )
                        await asyncio.sleep(retry_delay)

                raise RedisConnectionError(
                    f"Failed to connect to Redis after {retries} attempts"
                )

            except RedisConnectionError:
                raise
            except Exception as e:
                logger.error(
                    f"Async Redis connection fatal error: {e}", exc_info=True
                )
                raise
