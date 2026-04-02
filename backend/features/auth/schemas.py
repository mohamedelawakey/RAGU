from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UpdateUsernameRequest(BaseModel):
    username: str

    @validator('username')
    def validate_words(cls, v):
        if len(v.strip().split()) > 2:
            raise ValueError("Username cannot exceed 2 words")
        if not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()


class UpdatePasswordRequest(BaseModel):
    new_password: str
