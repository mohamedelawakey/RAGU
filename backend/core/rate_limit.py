from backend.db.connections.redis import AsyncRedisDBConnection
from fastapi_limiter import FastAPILimiter
from utils.logger import get_logger

logger = get_logger("core.rate_limit")


async def init_rate_limiter():
    try:
        redis_pool = await AsyncRedisDBConnection.get_connection()
        await FastAPILimiter.init(redis_pool)

        logger.info(
            "FastAPI rate limiter successfully initialized with Redis."
        )

    except Exception as e:
        logger.error(f"Failed to initialize global rate limiter: {e}")
        raise
