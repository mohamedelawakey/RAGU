from backend.db.connections.postgres import PostgresDBConnection
from backend.db.connections.redis import AsyncRedisDBConnection
from fastapi.security import OAuth2PasswordBearer
from backend.core import security, exceptions
from utils.logger import get_logger
from backend.config import Config
from fastapi import Depends

logger = get_logger("api.dependencies")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_db():
    async with PostgresDBConnection.get_db_connection() as conn:
        yield conn


async def get_redis():
    return await AsyncRedisDBConnection.get_connection()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis=Depends(get_redis)
) -> str:
    payload = security.decode_token(token)

    user_id: str = payload.get("sub")
    jti: str = payload.get("jti")

    if user_id is None or jti is None:
        logger.warning(
            f"Malformed access token payload: {payload}"
        )
        raise exceptions.CredentialsException(
            "Invalid authentication credentials"
        )

    try:
        is_revoked = await redis.get(f"{Config.REDIS_BLACKLIST_PREFIX}{jti}")
        if is_revoked:
            logger.warning(f"Attempted access with revoked token JTI: {jti}")
            raise exceptions.CredentialsException(
                "Session has been revoked. Please log in again."
            )
    except Exception as e:
        logger.error(
            f"Redis failure during Token Blacklist verification: {e}"
        )
        raise

    return user_id
