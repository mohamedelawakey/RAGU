from backend.db.connections.redis import AsyncRedisDBConnection
from fastapi_limiter.depends import RateLimiter
from utils.logger import get_logger
from pyrate_limiter import (
    Limiter, Rate, RateItem
)
from pyrate_limiter.clocks import MonotonicClock as TimeClock
from pyrate_limiter.abstracts import BucketFactory
from pyrate_limiter.buckets import RedisBucket

logger = get_logger("core.rate_limit")


class AsyncRedisBucketFactory(BucketFactory):
    def __init__(self, rates):
        self.rates = rates
        self.clock = TimeClock()
        self.redis_pool = None

    async def _get_redis(self):
        if self.redis_pool is None:
            self.redis_pool = await AsyncRedisDBConnection.get_connection()
        return self.redis_pool

    def wrap_item(self, name: str, weight: int = 1) -> RateItem:
        now = self.clock.now()
        return RateItem(name, now, weight=weight)

    async def get(self, item: RateItem) -> RedisBucket:
        redis_pool = await self._get_redis()
        return await RedisBucket.init(self.rates, redis_pool, f"ratelimit:{item.name}")


def RateLimit(times: int, seconds: int) -> RateLimiter:
    rates = [Rate(times, seconds * 1000)]
    factory = AsyncRedisBucketFactory(rates)
    return RateLimiter(limiter=Limiter(factory))


async def init_rate_limiter():
    logger.info("FastAPI rate limiter initialized with pyrate_limiter 0.2.0 RedisBucket factory.")
