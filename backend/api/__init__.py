from .dependencies import get_db, get_redis, get_current_user
from .middlewares import setup_middlewares
from .base_router import api_router


__all__ = [
    "api_router",
    "setup_middlewares",
    "get_db",
    "get_redis",
    "get_current_user",
]
