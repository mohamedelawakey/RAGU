from backend.api.dependencies import get_db, get_redis, oauth2_scheme
from backend.features.auth.schemas import (
    UserCreate, UserResponse, LogoutRequest, TokenResponse,
    RefreshTokenRequest, UpdateUsernameRequest, UpdatePasswordRequest
)
from backend.core.security import decode_token
from fastapi.security import OAuth2PasswordRequestForm
from backend.features.auth.service import AuthService
from fastapi import APIRouter, Depends, status
from backend.core.rate_limit import RateLimit
from utils.logger import get_logger
from backend.core import exceptions
from redis.asyncio import Redis
from asyncpg import Connection

logger = get_logger("features.auth.router")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimit(times=5, seconds=60))]
)
async def register(user: UserCreate, db: Connection = Depends(get_db)):
    try:
        return await AuthService.create_user(user, db)
    except exceptions.UserAlreadyExistsException:
        raise
    except Exception as e:
        logger.error(f"Registration Error: {e}")
        raise exceptions.InternalServerException()


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimit(times=5, seconds=60))]
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Connection = Depends(get_db)
):
    try:
        return await AuthService.authenticate_user(form_data.username, form_data.password, db)
    except exceptions.CredentialsException:
        raise
    except Exception as e:
        logger.error(f"Login Server Error: {e}")
        raise exceptions.InternalServerException()


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(RateLimit(times=10, seconds=60))]
)
async def get_me(
    access_token: str = Depends(oauth2_scheme),
    db: Connection = Depends(get_db)
):
    try:
        payload = decode_token(access_token)
        user_id = payload.get("sub")
        return await AuthService.get_current_user(user_id, db)
    except exceptions.CredentialsException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()

        logger.error(f"Get Me Error: {e}")
        raise exceptions.InternalServerException()


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimit(times=10, seconds=60))]
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Connection = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    try:
        return await AuthService.refresh_tokens(request.refresh_token, db, redis)
    except exceptions.CredentialsException:
        raise
    except Exception as e:
        logger.error(f"Token Refresh Engine Error: {e}")
        raise exceptions.InternalServerException()


@router.post(
    "/logout",
    dependencies=[Depends(RateLimit(times=5, seconds=60))]
)
async def logout(
    request: LogoutRequest,
    access_token: str = Depends(oauth2_scheme),
    redis: Redis = Depends(get_redis)
):
    try:
        return await AuthService.logout(access_token, request.refresh_token, redis)
    except exceptions.CredentialsException:
        raise
    except Exception as e:
        logger.error(f"Logout Protocol Error: {e}")
        raise exceptions.InternalServerException()


@router.put(
    "/username",
    dependencies=[Depends(RateLimit(times=5, seconds=60))]
)
async def update_username(
    request: UpdateUsernameRequest,
    access_token: str = Depends(oauth2_scheme),
    db: Connection = Depends(get_db)
):
    try:
        payload = decode_token(access_token)
        user_id = payload.get("sub")
        return await AuthService.update_username(user_id, request.username, db)
    except exceptions.UserAlreadyExistsException:
        raise
    except Exception as e:
        logger.error(f"Update Username Error: {e}")
        raise exceptions.InternalServerException()


@router.put(
    "/password",
    dependencies=[Depends(RateLimit(times=5, seconds=60))]
)
async def update_password(
    request: UpdatePasswordRequest,
    access_token: str = Depends(oauth2_scheme),
    db: Connection = Depends(get_db)
):
    try:
        payload = decode_token(access_token)
        user_id = payload.get("sub")
        return await AuthService.update_password(user_id, request.new_password, db)
    except Exception as e:
        logger.error(f"Update Password Error: {e}")
        raise exceptions.InternalServerException()
