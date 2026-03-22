from backend.core.exceptions import CredentialsException, UserAlreadyExistsException
from backend.core.security import (
    verify_password, get_password_hash, decode_token,
    create_access_token, create_refresh_token
)
from backend.features.auth.schemas import (
    UserCreate, UserResponse, TokenResponse
)
from backend.config import Config
from redis.asyncio import Redis
from asyncpg import Connection
import uuid


class AuthService:
    @staticmethod
    async def create_user(user: UserCreate, db: Connection) -> UserResponse:
        existing = await db.fetchrow(
            Config.CHECK_USER_EXISTS_QUERY,
            user.email, user.username
        )
        if existing:
            raise UserAlreadyExistsException()

        new_id = str(uuid.uuid4())
        hashed_pw = get_password_hash(user.password)

        await db.execute(
            Config.INSERT_USER_QUERY,
            new_id, user.username, user.email, hashed_pw
        )

        return UserResponse(id=new_id, username=user.username, email=user.email)

    @staticmethod
    async def authenticate_user(
        email_or_username: str,
        password: str,
        db: Connection
    ) -> TokenResponse:
        user_record = await db.fetchrow(
            Config.GET_USER_AUTH_QUERY,
            email_or_username
        )
        if not user_record:
            raise CredentialsException("Invalid email or password")

        if not verify_password(password, user_record["hashed_password"]):
            raise CredentialsException("Invalid email or password")

        user_id = user_record["id"]

        access_token = create_access_token(data={"sub": user_id})
        refresh_token = create_refresh_token(data={"sub": user_id})

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def refresh_tokens(refresh_token: str, db: Connection, redis: Redis) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")

        user_id = payload.get("sub")
        jti = payload.get("jti")

        is_revoked = await redis.get(f"{Config.REDIS_BLACKLIST_PREFIX}{jti}")
        if is_revoked:
            raise CredentialsException("Refresh token is revoked. Please login again.")

        refresh_ttl = Config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        await redis.setex(f"{Config.REDIS_BLACKLIST_PREFIX}{jti}", refresh_ttl, "true")

        new_access = create_access_token(data={"sub": user_id})
        new_refresh = create_refresh_token(data={"sub": user_id})

        return TokenResponse(access_token=new_access, refresh_token=new_refresh)

    @staticmethod
    async def logout(access_token: str, refresh_token: str, redis: Redis) -> dict:
        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token, expected_type="refresh")

        acc_jti = access_payload.get("jti")
        ref_jti = refresh_payload.get("jti")

        access_ttl = Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_ttl = Config.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        await redis.setex(f"{Config.REDIS_BLACKLIST_PREFIX}{acc_jti}", access_ttl, "true")
        await redis.setex(f"{Config.REDIS_BLACKLIST_PREFIX}{ref_jti}", refresh_ttl, "true")

        return {
            "msg": "Successfully logged out across global networks"
        }
