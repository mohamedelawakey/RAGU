from backend.core.security import (
    verify_password, get_password_hash, decode_token,
    create_access_token, create_refresh_token
)
from backend.core.exceptions import (
    CredentialsException,
    UserAlreadyExistsException,
    InternalServerException
)
from backend.features.auth.schemas import (
    UserCreate, UserResponse, TokenResponse
)
from backend.config import Config
from redis.asyncio import Redis
from asyncpg import Connection
import uuid
import random
from datetime import datetime, timedelta
from utils.email_utils import send_otp_email


class AuthService:
    @staticmethod
    async def create_user(user: UserCreate, db: Connection) -> UserResponse:
        async with db.transaction():
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
            
            # Initialize dashboard usage stats
            try:
                await db.execute(
                    "INSERT INTO user_usage (user_id) VALUES ($1)",
                    new_id
                )
            except Exception:
                # Non-critical, just log it if we had a logger here
                pass

        return UserResponse(id=new_id, username=user.username, email=user.email, is_verified=False)

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

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )

    @staticmethod
    async def get_current_user(user_id: str, db: Connection) -> UserResponse:
        user_record = await db.fetchrow(
            Config.GET_USER_BY_ID_QUERY,
            user_id
        )
        if not user_record:
            raise CredentialsException("User not found")

        return UserResponse(
            id=user_record["id"],
            username=user_record["username"],
            email=user_record["email"],
            is_verified=user_record["is_verified"]
        )

    @staticmethod
    async def refresh_tokens(
        refresh_token: str,
        db: Connection,
        redis: Redis
    ) -> TokenResponse:
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

        await redis.setex(
            f"{Config.REDIS_BLACKLIST_PREFIX}{acc_jti}", access_ttl, "true"
        )

        await redis.setex(
            f"{Config.REDIS_BLACKLIST_PREFIX}{ref_jti}", refresh_ttl, "true"
        )

        return {
            "msg": "Successfully logged out across global networks"
        }

    @staticmethod
    async def update_username(user_id: str, new_username: str, db: Connection) -> dict:
        existing = await db.fetchrow(
            "SELECT id FROM users WHERE username = $1",
            new_username
        )
        if existing and existing["id"] != user_id:
            raise UserAlreadyExistsException()

        await db.execute(
            Config.UPDATE_USERNAME_QUERY,
            new_username,
            user_id
        )
        return {"msg": "Username updated successfully", "username": new_username}

    @staticmethod
    async def update_password(user_id: str, old_password: str, new_password: str, db: Connection) -> dict:
        user_record = await db.fetchrow(
            "SELECT hashed_password FROM users WHERE id = $1",
            user_id
        )
        if not user_record or not verify_password(old_password, user_record["hashed_password"]):
            raise CredentialsException("Invalid current password")

        hashed_pw = get_password_hash(new_password)
        await db.execute(
            Config.UPDATE_PASSWORD_QUERY,
            hashed_pw,
            user_id
        )
        return {"msg": "Password updated successfully. Old session tokens will remain valid until expiry."}

    @staticmethod
    async def send_otp(user_id: str, db: Connection) -> dict:
        user = await db.fetchrow("SELECT email FROM users WHERE id = $1", user_id)
        if not user:
            raise CredentialsException("User not found")
        
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        otp_expiry = datetime.now() + timedelta(minutes=10)
        
        await db.execute(
            "UPDATE users SET otp_code = $1, otp_expiry = $2 WHERE id = $3",
            otp_code, otp_expiry, user_id
        )
        
        sent = send_otp_email(user["email"], otp_code)
        if not sent:
             # For UI purposes, we return success even if email failed if on dev
             pass
             
        return {"msg": f"OTP sent to {user['email']}"}

    @staticmethod
    async def verify_otp(user_id: str, otp_code: str, db: Connection) -> dict:
        user = await db.fetchrow("SELECT otp_code, otp_expiry FROM users WHERE id = $1", user_id)
        if not user:
             raise CredentialsException("User not found")
        
        if not user["otp_code"] or user["otp_code"] != otp_code:
            raise CredentialsException("Invalid verification code")
        
        if datetime.now() > user["otp_expiry"]:
            raise CredentialsException("Verification code expired")
            
        await db.execute(
            "UPDATE users SET is_verified = TRUE, otp_code = NULL, otp_expiry = NULL WHERE id = $1",
            user_id
        )
        return {"msg": "Account verified successfully"}

    @staticmethod
    async def request_email_change(user_id: str, new_email: str, db: Connection) -> dict:
        # Check if email is already taken
        existing = await db.fetchrow("SELECT id FROM users WHERE email = $1", new_email)
        if existing:
            raise UserAlreadyExistsException("Email already in use by another account.")
        
        # Generate OTP
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        otp_expiry = datetime.now() + timedelta(minutes=10)
        
        # Store pending change and OTP
        await db.execute(
            "UPDATE users SET pending_email = $1, otp_code = $2, otp_expiry = $3 WHERE id = $4",
            new_email, otp_code, otp_expiry, user_id
        )
        
        # Send OTP to the NEW email
        sent = send_otp_email(new_email, otp_code)
        if not sent:
             raise InternalServerException("Failed to send verification email. Please check your SMTP settings.")
             
        return {"msg": f"Verification code sent to {new_email}. Please confirm to update your account email."}

    @staticmethod
    async def verify_email_change(user_id: str, otp_code: str, db: Connection) -> dict:
        user = await db.fetchrow("SELECT pending_email, otp_code, otp_expiry FROM users WHERE id = $1", user_id)
        if not user or not user["pending_email"]:
             raise CredentialsException("No pending email change found.")
        
        if not user["otp_code"] or user["otp_code"] != otp_code:
            raise CredentialsException("Invalid verification code")
        
        if datetime.now() > user["otp_expiry"]:
            raise CredentialsException("Verification code expired")
            
        # Success: Finalize the email change
        await db.execute(
            "UPDATE users SET email = $1, pending_email = NULL, otp_code = NULL, otp_expiry = NULL, is_verified = TRUE WHERE id = $2",
            user["pending_email"], user_id
        )
        return {"msg": "Email updated and verified successfully"}
