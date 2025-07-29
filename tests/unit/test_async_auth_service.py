"""
Async unit tests for AsyncAuthService.

This module contains focused async unit tests for the AsyncAuthService class,
testing the core authentication functionality including:
- Password hashing and verification
- OTP generation and verification
- JWT token creation and validation
- User retrieval operations
- Async database operations

Tests use async patterns and fixtures for proper async testing.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import jwt
import bcrypt
from fastapi import HTTPException, status

from app.services.async_auth import AsyncAuthService
from app.models.user import User
from app.models.auth import OTPCode, RefreshToken
from app.core.config import settings
from tests.async_test_utils import AsyncDatabaseTestUtils, AsyncTestCase


class TestAsyncAuthServiceCore(AsyncTestCase):
    """Test core AsyncAuthService functionality."""

    def test_password_hashing_and_verification(self):
        """
        Test password hashing and verification works correctly.
        
        This test ensures that passwords are properly hashed and
        can be verified correctly using async service methods.
        """
        # Arrange: A test password
        password = "secure_password123"
        
        # Act: Hash the password
        hashed = AsyncAuthService.get_password_hash(password)
        
        # Assert: Hash should be valid and verifiable
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert AsyncAuthService.verify_password(password, hashed) is True
        assert AsyncAuthService.verify_password("wrong_password", hashed) is False

    def test_otp_generation(self):
        """
        Test OTP generation produces valid codes.
        
        This test ensures that OTP codes are generated correctly
        with the right format and length.
        """
        # Act: Generate OTP with default length
        otp = AsyncAuthService.generate_otp()
        
        # Assert: Should be 6 digits
        assert len(otp) == 6
        assert otp.isdigit()
        
        # Test custom length
        otp_custom = AsyncAuthService.generate_otp(8)
        assert len(otp_custom) == 8
        assert otp_custom.isdigit()

    def test_random_string_generation(self):
        """
        Test random string generation for tokens.
        
        This test ensures that random strings are generated
        with correct length and format.
        """
        # Act: Generate random string
        random_str = AsyncAuthService.generate_random_string()
        
        # Assert: Should be 32 characters and alphanumeric
        assert len(random_str) == 32
        assert random_str.isalnum()
        
        # Test custom length
        random_str_custom = AsyncAuthService.generate_random_string(16)
        assert len(random_str_custom) == 16
        assert random_str_custom.isalnum()

    def test_jwt_token_creation_and_validation(self):
        """
        Test JWT token creation and validation.
        
        This test ensures that access tokens are created correctly
        and contain the right information.
        """
        # Arrange: User ID
        user_id = 123
        
        # Act: Create access token
        token = AsyncAuthService.create_access_token(user_id)
        
        # Assert: Token should be valid and contain correct data
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify token contents
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["sub"] == str(user_id)
        assert "exp" in payload

    @pytest_asyncio.fixture
    async def mock_async_session(self):
        """Create a mock async session for testing."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_otp_database_interaction(self, mock_async_session):
        """
        Test OTP creation with async database interaction.
        
        This test ensures that OTP records are created correctly
        in the database with proper async data operations.
        """
        # Arrange: Test data
        user_id = 1
        email = "test@example.com"
        purpose = "login"
        
        # Act: Create OTP
        otp_code, expires_at = await AsyncAuthService.create_otp(
            mock_async_session, user_id, email, purpose
        )
        
        # Assert: OTP should be created correctly
        assert len(otp_code) == 6
        assert otp_code.isdigit()
        assert isinstance(expires_at, datetime)
        
        # Database operations should be called
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        
        # OTP record should have correct data
        otp_record = mock_async_session.add.call_args[0][0]
        assert otp_record.user_id == user_id
        assert otp_record.email == email
        assert otp_record.code == otp_code
        assert otp_record.purpose == purpose

    @pytest.mark.asyncio
    async def test_verify_otp_success(self, mock_async_session):
        """
        Test successful async OTP verification.
        
        This test ensures that valid OTPs are verified correctly
        and marked as used using async database operations.
        """
        # Arrange: Mock database with valid OTP
        mock_user = MagicMock()
        mock_user.id = 1
        mock_otp_record = MagicMock()
        mock_otp_record.user_id = 1
        mock_otp_record.is_used = False
        
        # Mock async database query results
        mock_otp_result = AsyncMock()
        mock_otp_result.scalar_one_or_none.return_value = mock_otp_record
        mock_async_session.execute.return_value = mock_otp_result
        
        # Mock user retrieval
        mock_async_session.get.return_value = mock_user
        
        # Act: Verify OTP
        result = await AsyncAuthService.verify_otp(
            mock_async_session, "test@example.com", "123456", "login"
        )
        
        # Assert: Should return user and mark OTP as used
        assert result == mock_user
        assert mock_otp_record.is_used is True
        mock_async_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_verify_otp_not_found(self, mock_async_session):
        """
        Test async OTP verification when OTP doesn't exist.
        
        This test ensures that invalid OTPs return None gracefully
        in async operations.
        """
        # Arrange: Mock database with no OTP found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to verify non-existent OTP
        result = await AsyncAuthService.verify_otp(
            mock_async_session, "test@example.com", "123456", "login"
        )
        
        # Assert: Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, mock_async_session):
        """
        Test async user retrieval by email address.
        
        This test ensures that users can be found by their email
        using async database operations.
        """
        # Arrange: Mock user and database result
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result
        
        # Act: Get user by email
        result = await AsyncAuthService.get_user_by_email(
            mock_async_session, "test@example.com"
        )
        
        # Assert: Should return the user
        assert result == mock_user
        
        # Test user not found
        mock_result.scalar_one_or_none.return_value = None
        result = await AsyncAuthService.get_user_by_email(
            mock_async_session, "nonexistent@example.com"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_oauth(self, mock_async_session):
        """
        Test async user retrieval by OAuth provider and ID.
        
        This test ensures that OAuth users can be found correctly
        using async database operations.
        """
        # Arrange: Mock OAuth user
        mock_user = MagicMock()
        mock_user.oauth_provider = "google"
        mock_user.oauth_id = "12345"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_async_session.execute.return_value = mock_result
        
        # Act: Get user by OAuth
        result = await AsyncAuthService.get_user_by_oauth(
            mock_async_session, "google", "12345"
        )
        
        # Assert: Should return the OAuth user
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_create_user(self, mock_async_session):
        """
        Test async user creation.
        
        This test ensures that new users are created correctly
        using async database operations.
        """
        # Arrange: User data
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "hashed_password": "hashed_password_123"
        }
        
        # Mock the created user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = user_data["email"]
        
        # Act: Create user
        result = await AsyncAuthService.create_user(mock_async_session, user_data)
        
        # Assert: User should be created
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, mock_async_session):
        """
        Test getting current user with valid JWT token using async operations.
        
        This test ensures that valid tokens return the correct user
        through async database operations.
        """
        # Arrange: Create valid token and mock user
        user_id = 123
        token = AsyncAuthService.create_access_token(user_id)
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_async_session.get.return_value = mock_user
        
        # Act: Get current user
        result = await AsyncAuthService.get_current_user(mock_async_session, token)
        
        # Assert: Should return the user
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, mock_async_session):
        """
        Test getting current user with invalid JWT token in async context.
        
        This test ensures that invalid tokens raise HTTP exceptions
        in async operations.
        """
        # Arrange: Invalid token
        invalid_token = "invalid.jwt.token"
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await AsyncAuthService.get_current_user(mock_async_session, invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    def test_get_current_active_user(self):
        """
        Test active user validation in async context.
        
        This test ensures that only active users are allowed through
        and inactive users are rejected.
        """
        # Test active user
        mock_active_user = MagicMock()
        mock_active_user.is_active = True
        result = AsyncAuthService.get_current_active_user(mock_active_user)
        assert result == mock_active_user
        
        # Test inactive user
        mock_inactive_user = MagicMock()
        mock_inactive_user.is_active = False
        
        with pytest.raises(HTTPException) as exc_info:
            AsyncAuthService.get_current_active_user(mock_inactive_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Inactive user" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, mock_async_session):
        """
        Test async refresh token creation.
        
        This test ensures that refresh tokens are created correctly
        using async database operations.
        """
        # Arrange: User ID
        user_id = 123
        
        # Act: Create refresh token
        token = await AsyncAuthService.create_refresh_token(mock_async_session, user_id)
        
        # Assert: Token should be created correctly
        assert isinstance(token, str)
        assert len(token) == 64
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_access_token(self, mock_async_session):
        """
        Test async refresh token usage to generate new access tokens.
        
        This test ensures that refresh tokens can be used to generate
        new access tokens using async database operations.
        """
        # Arrange: Mock valid refresh token
        user_id = 123
        mock_token_record = MagicMock()
        mock_token_record.user_id = user_id
        mock_token_record.is_revoked = False
        mock_token_record.expires_at = datetime.utcnow() + timedelta(days=1)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_token_record
        mock_async_session.execute.return_value = mock_result
        
        # Act: Refresh access token
        result = await AsyncAuthService.refresh_access_token(
            mock_async_session, "valid_refresh_token"
        )
        
        # Assert: Should return new access token and user ID
        assert result is not None
        new_access_token, returned_user_id = result
        assert isinstance(new_access_token, str)
        assert returned_user_id == user_id

    @pytest.mark.asyncio
    async def test_update_password(self, mock_async_session):
        """
        Test async password update functionality.
        
        This test ensures that user passwords can be updated correctly
        using async database operations.
        """
        # Arrange: Mock user
        user_id = 123
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_async_session.get.return_value = mock_user
        
        # Act: Update password
        new_password = "new_secure_password"
        await AsyncAuthService.update_password(mock_async_session, user_id, new_password)
        
        # Assert: Password should be updated and verifiable
        assert hasattr(mock_user, 'hashed_password')
        assert AsyncAuthService.verify_password(new_password, mock_user.hashed_password)
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_otp_required(self, mock_async_session):
        """
        Test async OTP requirement logic.
        
        This test ensures that OTP requirements are determined correctly
        based on user's last login time.
        """
        # Arrange: Mock user with recent login
        mock_user = MagicMock()
        mock_user.last_login_at = datetime.utcnow() - timedelta(days=3)
        
        # Act: Check if OTP is required
        result = await AsyncAuthService.is_otp_required(mock_user)
        
        # Assert: Should not require OTP for recent login
        assert result is False
        
        # Test with old login
        mock_user.last_login_at = datetime.utcnow() - timedelta(days=10)
        result = await AsyncAuthService.is_otp_required(mock_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_last_login(self, mock_async_session):
        """
        Test async last login update.
        
        This test ensures that user's last login time is updated
        correctly using async database operations.
        """
        # Arrange: Mock user
        user_id = 123
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_async_session.get.return_value = mock_user
        
        # Act: Update last login
        await AsyncAuthService.update_last_login(mock_async_session, user_id)
        
        # Assert: Last login should be updated
        assert hasattr(mock_user, 'last_login_at')
        assert isinstance(mock_user.last_login_at, datetime)
        mock_async_session.commit.assert_called_once()

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    def test_password_verification_with_wrong_password(self):
        """
        Negative Test: Password verification should fail with wrong password.
        
        This test ensures that incorrect passwords are properly rejected
        during verification in async context.
        """
        # Arrange: Hash a password
        correct_password = "correct_password123"
        hashed = AsyncAuthService.get_password_hash(correct_password)
        
        # Act & Assert: Wrong password should fail verification
        wrong_password = "wrong_password456"
        assert AsyncAuthService.verify_password(wrong_password, hashed) is False

    @pytest.mark.asyncio
    async def test_jwt_token_validation_with_invalid_token(self, mock_async_session):
        """
        Negative Test: JWT token validation should fail with malformed token.
        
        This test ensures that invalid or malformed tokens are rejected
        and raise appropriate exceptions in async operations.
        """
        # Arrange: Invalid token
        invalid_token = "invalid.malformed.token"
        
        # Act & Assert: Should raise HTTPException for invalid token
        with pytest.raises(HTTPException) as exc_info:
            await AsyncAuthService.get_current_user(mock_async_session, invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_otp_verification_with_expired_or_invalid_otp(self, mock_async_session):
        """
        Negative Test: OTP verification should fail with invalid OTP.
        
        This test ensures that non-existent or invalid OTPs are rejected
        and return None appropriately in async operations.
        """
        # Arrange: Mock database with no OTP found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to verify invalid OTP
        result = await AsyncAuthService.verify_otp(
            mock_async_session, "test@example.com", "999999", "login"
        )
        
        # Assert: Should return None for invalid OTP
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, mock_async_session):
        """
        Negative Test: Refresh token should fail when expired.
        
        This test ensures that expired refresh tokens are rejected
        appropriately in async operations.
        """
        # Arrange: Mock expired refresh token
        mock_token_record = MagicMock()
        mock_token_record.expires_at = datetime.utcnow() - timedelta(days=1)  # Expired
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_token_record
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to use expired refresh token
        result = await AsyncAuthService.refresh_access_token(
            mock_async_session, "expired_refresh_token"
        )
        
        # Assert: Should return None for expired token
        assert result is None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, mock_async_session):
        """
        Negative Test: User creation should handle duplicate email gracefully.
        
        This test ensures that duplicate email creation is handled
        appropriately in async operations.
        """
        # Arrange: User data with duplicate email
        user_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "full_name": "User One"
        }
        
        # Mock database integrity error
        from sqlalchemy.exc import IntegrityError
        mock_async_session.commit.side_effect = IntegrityError("", "", "")
        
        # Act & Assert: Should handle integrity error
        with pytest.raises(IntegrityError):
            await AsyncAuthService.create_user(mock_async_session, user_data)