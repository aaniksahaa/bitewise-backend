from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    EmailVerify,
    EmailVerifyResponse,
    GoogleLoginResponse,
    LoginResponse,
    LoginVerify,
    LoginVerifyResponse,
    PasswordResetComplete,
    PasswordResetCompleteResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RefreshTokenRequest,
    Token,
    UserLogin,
    UserRegister,
    UserRegisterResponse,
)
from app.services.auth import AuthService

router = APIRouter()

# Initialize Google SSO
google_sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_CALLBACK_URL,
    allow_insecure_http=True,  # Only for development
)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRegisterResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user with email and password.
    An OTP verification email will be sent to the provided email address.
    """
    # Check if email already exists
    existing_user = AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=AuthService.get_password_hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create and send OTP
    otp, _ = AuthService.create_otp(
        db, user.id, user.email, "register", expires_in=300
    )
    from app.services.email import EmailService
    email_service = EmailService()
    email_service.send_verification_email(user.email, otp, user.username)

    return UserRegisterResponse(
        user_id=str(user.id),
        email=user.email,
        message="Verification email sent. Please check your inbox to verify your account.",
    )


@router.post("/verify-email", response_model=EmailVerifyResponse)
async def verify_email(verification_data: EmailVerify, db: Session = Depends(get_db)) -> Any:
    """
    Verify the user's email address using the OTP sent to their email.
    """
    user = AuthService.verify_otp(
        db, verification_data.email, verification_data.otp, "register"
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP or OTP expired",
        )

    # Activate and verify the user
    user.is_active = True
    user.is_verified = True
    db.commit()

    # Generate access token
    access_token = AuthService.create_access_token(user.id)
    
    return EmailVerifyResponse(
        message="Email verified successfully",
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=LoginResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate a user with email and password.
    An OTP will be sent to the user's email for two-factor authentication.
    """
    user = AuthService.get_user_by_email(db, login_data.email)
    if not user or not AuthService.verify_password(
        login_data.password, user.hashed_password or ""
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not active",
        )

    # Create and send OTP
    otp, expires_at = AuthService.create_otp(
        db, user.id, user.email, "login", expires_in=300
    )
    
    # Send login OTP via email
    from app.services.email import EmailService
    email_service = EmailService()
    email_service.send_login_otp(user.email, otp, user.username)

    return LoginResponse(
        message="OTP sent to your email for verification",
        login_request_id=str(user.id),  # Using user ID as login request ID for simplicity
        expires_in=300,  # 5 minutes
    )


@router.post("/verify-login", response_model=LoginVerifyResponse)
async def verify_login(verification_data: LoginVerify, db: Session = Depends(get_db)) -> Any:
    """
    Verify the login OTP and return an access token upon successful verification.
    """
    user_id = verification_data.login_request_id
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify OTP
    otp_verification = AuthService.verify_otp(
        db, user.email, verification_data.otp, "login"
    )
    if not otp_verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP or OTP expired",
        )

    # Generate tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(db, user.id)

    return LoginVerifyResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user_id=str(user.id),
    )


@router.get("/google/login")
async def google_login(request: Request) -> Any:
    """
    Initiates the Google OAuth2 login flow by redirecting to Google's authentication page.
    """
    return await google_sso.get_login_redirect(request)


@router.get("/google/callback", response_model=GoogleLoginResponse)
async def google_callback(request: Request, db: Session = Depends(get_db)) -> Any:
    """
    Handles the callback from Google OAuth2 after successful authentication.
    """
    try:
        user_info = await google_sso.verify_and_process(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )

    # Check if user exists
    user = AuthService.get_user_by_oauth(db, "google", user_info.id)
    is_new_user = False

    if not user:
        # Create new user
        is_new_user = True
        user = User(
            email=user_info.email,
            username=user_info.email.split("@")[0],  # Simple username from email
            full_name=user_info.display_name,
            oauth_provider="google",
            oauth_id=user_info.id,
            is_active=True,
            is_verified=True,  # Google users are pre-verified
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Send welcome email for new users
        from app.services.email import EmailService
        email_service = EmailService()
        email_service.send_account_activation_email(user.email, user.username)

    # Generate tokens
    access_token = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(db, user.id)

    return GoogleLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user_id=str(user.id),
        is_new_user=is_new_user,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token_data: RefreshTokenRequest, db: Session = Depends(get_db)
) -> Any:
    """
    Obtain a new access token using a refresh token.
    """
    result = AuthService.refresh_access_token(db, refresh_token_data.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, _ = result

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user),
) -> Any:
    """
    Invalidate the current access token and associated refresh tokens.
    """
    AuthService.revoke_all_refresh_tokens(db, current_user.id)
    return {"message": "Successfully logged out"}


@router.post("/reset-password/request", response_model=PasswordResetResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest, db: Session = Depends(get_db)
) -> Any:
    """
    Initiate a password reset by sending a reset link to the user's email.
    """
    user = AuthService.get_user_by_email(db, reset_data.email)
    if not user:
        # Don't reveal whether the email exists for security
        return PasswordResetResponse(
            message="Password reset instructions sent to your email if the account exists",
            reset_request_id="",
            expires_in=900,  # 15 minutes
        )

    # Create reset request and OTP
    request_id, expires_at = AuthService.create_password_reset_request(
        db, user.id, expires_in=900
    )
    otp, _ = AuthService.create_otp(
        db, user.id, user.email, "reset-password", expires_in=900
    )

    # Send password reset email
    from app.services.email import EmailService
    email_service = EmailService()
    email_service.send_password_reset_email(user.email, otp, user.username)

    return PasswordResetResponse(
        message="Password reset instructions sent to your email",
        reset_request_id=request_id,
        expires_in=900,  # 15 minutes
    )


@router.post("/reset-password/complete", response_model=PasswordResetCompleteResponse)
async def complete_password_reset(
    reset_data: PasswordResetComplete, db: Session = Depends(get_db)
) -> Any:
    """
    Complete the password reset process with the OTP and new password.
    """
    user = AuthService.verify_password_reset_request(
        db, reset_data.reset_request_id, reset_data.otp
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request or OTP",
        )

    # Update password
    AuthService.update_password(db, user.id, reset_data.new_password)

    return PasswordResetCompleteResponse(message="Password reset successful") 