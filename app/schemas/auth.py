from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# NOTE: email-validator is required by Pydantic for EmailStr validation
# Pydantic uses email-validator under the hood for the EmailStr type
# See: https://docs.pydantic.dev/latest/api/networks/#emailstr

# Registration schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserRegisterResponse(BaseModel):
    user_id: str
    email: EmailStr
    message: str


# Email verification schemas
class EmailVerify(BaseModel):
    email: EmailStr
    otp: str


class EmailVerifyResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    expires_in: int


# Login schemas
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    login_request_id: str
    expires_in: int


# Login verification schemas
class LoginVerify(BaseModel):
    login_request_id: str
    otp: str


class LoginVerifyResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user_id: str


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    exp: int


# Refresh token schemas
class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Social login response schema
class GoogleLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user_id: str
    is_new_user: bool


# Password reset schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetResponse(BaseModel):
    message: str
    reset_request_id: str
    expires_in: int


class PasswordResetComplete(BaseModel):
    reset_request_id: str
    otp: str
    new_password: str = Field(..., min_length=8)


class PasswordResetCompleteResponse(BaseModel):
    message: str


# Error response schema
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail 