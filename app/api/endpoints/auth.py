from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

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
    DirectLoginResponse,
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


@router.post("/login", response_model=Union[LoginResponse, DirectLoginResponse])
async def login(login_data: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    Authenticate a user with email and password.
    If the user hasn't logged in for more than 7 days, an OTP will be sent for verification.
    Otherwise, return access tokens directly.
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

    # Refresh user from database to get the most recent last_login_at value
    db.refresh(user)

    # Check if OTP is required based on last login time
    otp_required = AuthService.is_otp_required_for_login(user)
    
    if not otp_required:
        # User has logged in recently (within 7 days), provide tokens directly
        access_token = AuthService.create_access_token(user.id)
        refresh_token = AuthService.create_refresh_token(db, user.id)
        
        # Update last login time
        AuthService.update_last_login(db, user.id)
        
        return DirectLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_token,
            user_id=str(user.id),
            message="Login successful - welcome back!",
            otp_required=False,
        )
    else:
        # User hasn't logged in for more than 7 days, require OTP verification
        otp, expires_at = AuthService.create_otp(
            db, user.id, user.email, "login", expires_in=300
        )
        
        # Send login OTP via email
        from app.services.email import EmailService
        email_service = EmailService()
        email_service.send_login_otp(user.email, otp, user.username)

        return LoginResponse(
            message="For security, please verify with the OTP sent to your email",
            login_request_id=str(user.id),
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
    
    # Update last login time after successful OTP verification
    AuthService.update_last_login(db, user.id)

    return LoginVerifyResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        user_id=str(user.id),
    )


@router.get("/google/login", response_model=GoogleLoginUrlResponse)
async def google_login(
    redirect_uri: Optional[str] = None,
    state: Optional[str] = None
) -> Any:
    """
    Generates Google OAuth authorization URL for user authentication.
    Returns a JSON response with the authorization URL - never redirects.
    
    Args:
        redirect_uri: The frontend URL where user should be redirected after successful authentication
                     (e.g., 'http://localhost:8080/dashboard', NOT the backend callback URL)
        state: Optional state parameter for CSRF protection
    """
    # Validate that redirect_uri is not the backend callback URL
    if redirect_uri and redirect_uri == settings.GOOGLE_CALLBACK_URL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri should be your frontend URL, not the backend callback URL"
        )
    
    # The redirect_uri parameter here is the FRONTEND redirect URL where user should end up
    # The actual Google OAuth redirect_uri is always our backend callback
    frontend_redirect_uri = redirect_uri or f"{settings.FRONTEND_URL}/dashboard"
    
    # Use the frontend redirect URI as the state parameter if no state provided
    # This way we can redirect back to the correct frontend page after authentication
    if not state:
        state = frontend_redirect_uri
    
    # Use fastapi_sso to generate the login redirect
    # Always use the backend callback URL for Google OAuth redirect_uri
    async with google_sso:
        redirect_response = await google_sso.get_login_redirect(
            redirect_uri=settings.GOOGLE_CALLBACK_URL,
            state=state,
            params={
                "prompt": "consent", 
                "access_type": "offline"
            }
        )
    
    # Extract the URL from the redirect response
    authorization_url = str(redirect_response.headers.get("location", ""))
    
    return GoogleLoginUrlResponse(
        authorization_url=authorization_url,
        state=state
    )


@router.get("/google/callback")
async def google_callback_get(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """
    Handles the Google OAuth callback via GET redirect from Google.
    This is the traditional OAuth flow where Google redirects directly to this endpoint.
    Redirects user back to frontend with authentication tokens.
    """
    try:
        # Use fastapi_sso to verify and process the callback
        async with google_sso:
            google_user = await google_sso.verify_and_process(request)
        
        if not google_user:
            # Redirect to frontend with error
            frontend_url = request.query_params.get("state") or settings.FRONTEND_URL
            return RedirectResponse(
                url=f"{frontend_url}?error=authentication_failed",
                status_code=302
            )
        
        # Process the user data
        auth_response = await _process_google_user(google_user, db)
        
        # Extract the original redirect URI from state or use default
        redirect_uri = request.query_params.get("state") or f"{settings.FRONTEND_URL}/dashboard"
        
        # Create redirect URL with tokens
        redirect_url = (
            f"{redirect_uri}"
            f"?access_token={auth_response.access_token}"
            f"&refresh_token={auth_response.refresh_token}"
            f"&token_type={auth_response.token_type}"
            f"&expires_in={auth_response.expires_in}"
            f"&user_id={auth_response.user_id}"
            f"&email={auth_response.email}"
            f"&username={auth_response.username}"
            f"&provider={auth_response.provider}"
            f"&first_login={str(auth_response.first_login).lower()}"
            f"&profile_complete={str(auth_response.profile_complete).lower()}"
            f"&is_new_user={str(auth_response.is_new_user).lower()}"
        )
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException as e:
        # Redirect to frontend with error
        frontend_url = request.query_params.get("state") or settings.FRONTEND_URL
        return RedirectResponse(
            url=f"{frontend_url}?error={e.detail}",
            status_code=302
        )
    except Exception as e:
        # Redirect to frontend with error
        frontend_url = request.query_params.get("state") or settings.FRONTEND_URL
        return RedirectResponse(
            url=f"{frontend_url}?error=authentication_failed",
            status_code=302
        )


async def _process_google_user(google_user: Any, db: Session) -> GoogleLoginResponse:
    """
    Process Google user data and create/update user in database.
    """
    # Validate required user info from Google
    if not google_user.email or not google_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user information received from Google",
        )

    # Check if user exists by OAuth provider and ID
    user = AuthService.get_user_by_oauth(db, "google", google_user.id)
    is_new_user = False
    first_login = False

    if not user:
        # Check if a user already exists with this email but different provider
        existing_user = AuthService.get_user_by_email(db, google_user.email)
        
        if existing_user:
            # Link Google account to existing user
            existing_user.oauth_provider = "google"
            existing_user.oauth_id = google_user.id
            existing_user.is_verified = True
            db.commit()
            user = existing_user
            first_login = False
        else:
            # Create new user with unique username handling
            base_username = google_user.email.split("@")[0]
            username = AuthService.generate_unique_username(db, base_username)
            
            is_new_user = True
            first_login = True
            user = User(
                email=google_user.email,
                username=username,
                full_name=getattr(google_user, 'display_name', '') or getattr(google_user, 'name', ''),
                oauth_provider="google",
                oauth_id=google_user.id,
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

    # Update last login time for Google OAuth users
    AuthService.update_last_login(db, user.id)

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


@router.get("/debug/login-status")
async def debug_login_status(
    email: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Debug endpoint to check user's login status and OTP requirements.
    This is for debugging purposes only.
    """
    user = AuthService.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    otp_required = AuthService.is_otp_required_for_login(user)
    
    return {
        "user_id": user.id,
        "email": user.email,
        "last_login_at": user.last_login_at,
        "otp_required": otp_required,
        "threshold_days": settings.LOGIN_OTP_THRESHOLD_DAYS,
        "current_time": datetime.utcnow(),
        "time_since_last_login": (datetime.utcnow() - user.last_login_at) if user.last_login_at else None,
    } 