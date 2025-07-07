import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.auth import OTP, PasswordResetRequest, RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPayload
from app.services.email import EmailService

# Update OAuth2 to use the correct tokenUrl
# The token endpoint is specifically for Swagger UI authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/token")

# Email service instance
email_service = EmailService()


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password for storage."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate a random OTP code."""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """Generate a random string for tokens and request IDs."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @classmethod
    def is_otp_required_for_login(cls, user: User, otp_threshold_days: int = None) -> bool:
        """
        Check if OTP verification is required based on last login time.
        
        Args:
            user: The user attempting to login
            otp_threshold_days: Number of days since last login to require OTP (if None, uses config setting)
            
        Returns:
            bool: True if OTP is required, False otherwise
        """
        if otp_threshold_days is None:
            otp_threshold_days = settings.LOGIN_OTP_THRESHOLD_DAYS
            
        # Debug logging
        print(f"[DEBUG] Checking OTP requirement for user {user.id}")
        print(f"[DEBUG] User last_login_at: {user.last_login_at}")
        print(f"[DEBUG] Threshold days: {otp_threshold_days}")
        
        # Always require OTP for first-time users (no previous login)
        if not user.last_login_at:
            print(f"[DEBUG] No previous login found - OTP required")
            return True
            
        # Calculate time since last login
        time_since_last_login = datetime.utcnow() - user.last_login_at
        print(f"[DEBUG] Time since last login: {time_since_last_login}")
        print(f"[DEBUG] Threshold timedelta: {timedelta(days=otp_threshold_days)}")
        
        # Require OTP if last login was more than threshold days ago
        otp_required = time_since_last_login > timedelta(days=otp_threshold_days)
        print(f"[DEBUG] OTP required: {otp_required}")
        
        return otp_required

    @classmethod
    def update_last_login(cls, db: Session, user_id: int) -> None:
        """Update the user's last login timestamp."""
        print(f"[DEBUG] Updating last_login_at for user {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            old_last_login = user.last_login_at
            user.last_login_at = datetime.utcnow()
            db.commit()
            db.refresh(user)  # Refresh to ensure we get the updated value
            print(f"[DEBUG] Updated last_login_at from {old_last_login} to {user.last_login_at}")
        else:
            print(f"[DEBUG] User {user_id} not found for last_login_at update")

    @classmethod
    def generate_unique_username(cls, db: Session, base_username: str) -> str:
        """Generate a unique username by checking for collisions and appending numbers if needed."""
        # First, get all existing usernames that start with the base_username in one query
        # This reduces database calls from potentially 100+ to just 1-2
        existing_usernames = db.query(User.username).filter(
            User.username.like(f"{base_username}%")
        ).all()
        
        # Convert to a set for O(1) lookup performance
        existing_username_set = {username[0] for username in existing_usernames}
        
        # Start with the base username
        username = base_username
        if username not in existing_username_set:
            return username
            
        # Find the first available username with a number suffix
        counter = 1
        max_attempts = 100  # Safety limit
        
        while counter <= max_attempts:
            username = f"{base_username}{counter}"
            if username not in existing_username_set:
                return username
            counter += 1
            
        # If we've exhausted attempts, add a random suffix (very unlikely scenario)
        random_suffix = cls.generate_random_string(8)
        username = f"{base_username}_{random_suffix}"
        
        return username

    @classmethod
    def create_otp(
        cls, db: Session, user_id: int, email: str, purpose: str, expires_in: int = 300
    ) -> Tuple[str, datetime]:
        """Create a new OTP and store it in the database."""
        otp_code = cls.generate_otp()
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Create the OTP record
        otp_record = OTP(
            user_id=user_id,
            email=email,
            code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
        )
        db.add(otp_record)
        db.commit()
        
        return otp_code, expires_at

    @classmethod
    def verify_otp(cls, db: Session, email: str, otp: str, purpose: str) -> Optional[User]:
        """Verify an OTP code for a specific email and purpose."""
        otp_record = (
            db.query(OTP)
            .filter(
                OTP.email == email,
                OTP.code == otp,
                OTP.purpose == purpose,
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow(),
            )
            .first()
        )
        
        if not otp_record:
            return None
        
        # Mark OTP as used
        otp_record.is_used = True
        db.commit()
        
        # Return the associated user
        return db.query(User).filter(User.id == otp_record.user_id).first()

    @classmethod
    def verify_login_request_otp(
        cls, db: Session, login_request_id: str, otp: str
    ) -> Optional[User]:
        """Verify an OTP for a login request."""
        otp_record = (
            db.query(OTP)
            .filter(
                OTP.id == login_request_id,
                OTP.code == otp,
                OTP.purpose == "login",
                OTP.is_used == False,
                OTP.expires_at > datetime.utcnow(),
            )
            .first()
        )
        
        if not otp_record:
            return None
        
        # Mark OTP as used
        otp_record.is_used = True
        db.commit()
        
        # Return the associated user
        return db.query(User).filter(User.id == otp_record.user_id).first()

    @classmethod
    def create_access_token(cls, user_id: int, expires_delta: timedelta = None) -> str:
        """Create a new JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": str(user_id), "exp": expire}
        
        return jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    @classmethod
    def create_refresh_token(cls, db: Session, user_id: int) -> str:
        """Create a new refresh token."""
        token = cls.generate_random_string(64)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Create the refresh token record
        refresh_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.add(refresh_token)
        db.commit()
        
        return token

    @classmethod
    def refresh_access_token(cls, db: Session, refresh_token: str) -> Optional[Tuple[str, int]]:
        """Generate a new access token using a refresh token."""
        token_record = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token == refresh_token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
            .first()
        )
        
        if not token_record:
            return None
        
        # Create a new access token
        access_token = cls.create_access_token(token_record.user_id)
        
        return access_token, token_record.user_id

    @classmethod
    def revoke_all_refresh_tokens(cls, db: Session, user_id: int) -> None:
        """Revoke all refresh tokens for a user (logout from all devices)."""
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        ).update({"is_revoked": True})
        db.commit()

    @classmethod
    def get_user_by_email(cls, db: Session, email: str) -> Optional[User]:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()

    @classmethod
    def get_user_by_oauth(cls, db: Session, provider: str, oauth_id: str) -> Optional[User]:
        """Get a user by OAuth provider and ID."""
        return (
            db.query(User)
            .filter(User.oauth_provider == provider, User.oauth_id == oauth_id)
            .first()
        )

    @classmethod
    def create_password_reset_request(
        cls, db: Session, user_id: int, expires_in: int = 900
    ) -> Tuple[str, datetime]:
        """Create a password reset request."""
        request_id = cls.generate_random_string()
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Create the reset request record
        reset_request = PasswordResetRequest(
            user_id=user_id,
            request_id=request_id,
            expires_at=expires_at,
        )
        db.add(reset_request)
        db.commit()
        
        return request_id, expires_at

    @classmethod
    def verify_password_reset_request(
        cls, db: Session, reset_request_id: str, otp: str
    ) -> Optional[User]:
        """Verify a password reset request with OTP."""
        reset_request = (
            db.query(PasswordResetRequest)
            .filter(
                PasswordResetRequest.request_id == reset_request_id,
                PasswordResetRequest.is_used == False,
                PasswordResetRequest.expires_at > datetime.utcnow(),
            )
            .first()
        )
        
        if not reset_request:
            return None
        
        # Get the user
        user = db.query(User).filter(User.id == reset_request.user_id).first()
        if not user:
            return None
        
        # Verify the OTP for this user
        otp_valid = cls.verify_otp(db, user.email, otp, "reset-password")
        if not otp_valid:
            return None
        
        # Mark reset request as used
        reset_request.is_used = True
        db.commit()
        
        return user

    @classmethod
    def update_password(cls, db: Session, user_id: int, new_password: str) -> None:
        """Update a user's password."""
        hashed_password = cls.get_password_hash(new_password)
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.hashed_password = hashed_password
            db.commit()

    @classmethod
    def get_current_user(
        cls, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
    ) -> User:
        """Get the current authenticated user from the token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            token_data = TokenPayload(**payload)
            
            if datetime.fromtimestamp(token_data.exp) < datetime.utcnow():
                raise credentials_exception
                
        except jwt.PyJWTError:
            raise credentials_exception
            
        user = db.query(User).filter(User.id == int(token_data.sub)).first()
        if user is None:
            raise credentials_exception
            
        return user

    @classmethod
    def get_current_active_user(cls, current_user: User = Depends(get_current_user)) -> User:
        """Check if the current user is active."""
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user",
            )
        return current_user


# Standalone dependency functions for FastAPI
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """Get the current authenticated user from the token."""
    return AuthService.get_current_user(db, token)

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user 