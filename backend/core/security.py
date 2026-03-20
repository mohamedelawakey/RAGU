from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from utils.logger import get_logger
from . import exceptions
from backend.config import Config
from jose import jwt
import uuid

logger = get_logger("core.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        logger.debug("Verifying password...")
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Failed to verify password: {e}")
        raise exceptions.InternalServerException("Server cryptography verification failure")


def get_password_hash(password: str) -> str:
    try:
        logger.debug("Hashing password...")
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Failed to hash password: {e}")
        raise exceptions.InternalServerException("Server cryptography execution failure")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    try:
        logger.debug("Creating access token...")

        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "type": "access"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            Config.SECRET_KEY,
            algorithm=Config.ALGORITHM
        )

        logger.debug("Access token created successfully")
        return encoded_jwt

    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise exceptions.InternalServerException("Failed to securely generate access token")


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    try:
        logger.debug("Creating refresh token...")

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            Config.SECRET_KEY,
            algorithm=Config.ALGORITHM
        )

        return encoded_jwt

    except Exception as e:
        logger.error(f"Failed to create refresh token: {e}")
        raise exceptions.InternalServerException("Failed to securely generate refresh token")


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])

        if payload.get("type") != expected_type:
            raise exceptions.CredentialsException("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        logger.error("Token has naturally expired.")
        raise exceptions.CredentialsException("Token has expired")

    except jwt.JWTError as e:
        logger.error(f"JWT Validation error: {e}")
        raise exceptions.CredentialsException("Invalid token payload or signature")
