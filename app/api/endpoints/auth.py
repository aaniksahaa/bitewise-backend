from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
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
    GoogleLoginUrlResponse,
    GoogleCallbackRequest,
)
from app.services.auth import AuthService, get_current_active_user

router = APIRouter()

# Initialize Google SSO
google_sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=settings.GOOGLE_CALLBACK_URL,
    allow_insecure_http=settings.ENVIRONMENT == "development",  # Only for development
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


@router.get("/google/login", response_model=GoogleLoginUrlResponse)
async def google_login(
    redirect_uri: str,  # Make this required as per frontend requirements
    state: Optional[str] = None
) -> Any:
    """
    Generates Google OAuth authorization URL for user authentication.
    Returns a JSON response with the authorization URL - never redirects.
    """
    # Generate state if not provided
    if not state:
        import secrets
        state = secrets.token_urlsafe(32)
    
    # Build Google OAuth authorization URL according to OAuth2 spec
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    
    return GoogleLoginUrlResponse(
        authorization_url=google_auth_url,
        state=state
    )


@router.get("/google/callback", response_model=GoogleLoginResponse)
async def google_callback_get(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Handles the Google OAuth callback via GET redirect from Google.
    This is the traditional OAuth flow where Google redirects directly to this endpoint.
    """
    try:
        # Extract code and state from query parameters
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code not provided"
            )
        
        # Process the callback using the same logic
        return await _process_google_callback(code, state, db)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )


@router.post("/google/callback", response_model=GoogleLoginResponse)
async def google_callback_post(
    callback_data: GoogleCallbackRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Handles the Google OAuth callback via POST request from frontend.
    This is for frontend applications that capture the callback and send it as API call.
    """
    try:
        return await _process_google_callback(callback_data.code, callback_data.state, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}",
        )


async def _process_google_callback(code: str, state: Optional[str], db: Session) -> GoogleLoginResponse:
    """
    Common function to process Google OAuth callback for both GET and POST endpoints.
    """
    # Exchange authorization code for access token with Google
    import httpx
    
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.GOOGLE_CALLBACK_URL,
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        
    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code for access token"
        )
        
    token_info = token_response.json()
    access_token = token_info.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received from Google"
        )
    
    # Get user info from Google
    user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
    
    async with httpx.AsyncClient() as client:
        user_response = await client.get(user_info_url)
        
    if user_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to fetch user information from Google"
        )
        
    user_info = user_response.json()
    
    # Validate required user info from Google
    if not user_info.get("email") or not user_info.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user information received from Google",
        )

    # Check if user exists by OAuth provider and ID
    user = AuthService.get_user_by_oauth(db, "google", user_info["id"])
    is_new_user = False
    first_login = False

    if not user:
        # Check if a user already exists with this email but different provider
        existing_user = AuthService.get_user_by_email(db, user_info["email"])
        
        if existing_user:
            # Link Google account to existing user
            existing_user.oauth_provider = "google"
            existing_user.oauth_id = user_info["id"]
            existing_user.is_verified = True
            db.commit()
            user = existing_user
            first_login = False
        else:
            # Create new user with unique username handling
            base_username = user_info["email"].split("@")[0]
            username = AuthService.generate_unique_username(db, base_username)
            
            is_new_user = True
            first_login = True
            user = User(
                email=user_info["email"],
                username=username,
                full_name=user_info.get("name", ""),
                oauth_provider="google",
                oauth_id=user_info["id"],
                is_active=True,
                is_verified=True,  # Google users are pre-verified
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Send welcome email for new users
            try:
                from app.services.email import EmailService
                email_service = EmailService()
                email_service.send_account_activation_email(user.email, user.username)
            except Exception as e:
                # Log the error but don't fail the authentication
                print(f"Failed to send welcome email: {str(e)}")
    else:
        # Existing Google user
        first_login = False

    # Ensure user is active and verified for OAuth users
    if not user.is_active:
        user.is_active = True
        db.commit()
    
    if not user.is_verified:
        user.is_verified = True
        db.commit()

    # Check if profile is complete (has required fields)
    profile_complete = bool(
        user.full_name and 
        user.username and 
        user.email
    )

    # Generate YOUR app's JWT tokens (not Google's)
    access_token_jwt = AuthService.create_access_token(user.id)
    refresh_token = AuthService.create_refresh_token(db, user.id)

    return GoogleLoginResponse(
        access_token=access_token_jwt,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user_id=str(user.id),
        email=user.email,
        username=user.username,
        provider="google",
        first_login=first_login,
        profile_complete=profile_complete,
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
    current_user: User = Depends(get_current_active_user),
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


# Add a direct token endpoint for Swagger UI authentication
@router.post("/token", response_model=Token)
async def login_for_access_token(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    This endpoint is primarily for Swagger UI authentication.
    """
    from fastapi.security import OAuth2PasswordRequestForm
    from fastapi import Form

    user = AuthService.get_user_by_email(db, username)
    if not user or not AuthService.verify_password(password, user.hashed_password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not active",
        )

    # Generate tokens
    access_token = AuthService.create_access_token(user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    ) 