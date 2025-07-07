"""
Unit tests for AuthService.

This module contains focused unit tests for the AuthService class,
testing the core authentication functionality including:
- Password hashing and verification
- OTP generation
- JWT token creation
- User retrieval operations

Tests are kept simple and focused on essential functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import jwt
import bcrypt
from fastapi import HTTPException, status

from app.services.auth import AuthService
from app.models.user import User
from app.core.config import settings


class TestAuthServiceCore:
    """Test core AuthService functionality."""

    def test_password_hashing_and_verification(self):
        """
        Test password hashing and verification works correctly.
        
        This test ensures that passwords are properly hashed and
        can be verified correctly.
        """
        # Arrange: A test password
        password = "secure_password123"
        
        # Act: Hash the password
        hashed = AuthService.get_password_hash(password)
        
        # Assert: Hash should be valid and verifiable
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert AuthService.verify_password(password, hashed) is True
        assert AuthService.verify_password("wrong_password", hashed) is False

    def test_otp_generation(self):
        """
        Test OTP generation produces valid codes.
        
        This test ensures that OTP codes are generated correctly
        with the right format and length.
        """
        # Act: Generate OTP with default length
        otp = AuthService.generate_otp()
        
        # Assert: Should be 6 digits
        assert len(otp) == 6
        assert otp.isdigit()
        
        # Test custom length
        otp_custom = AuthService.generate_otp(8)
        assert len(otp_custom) == 8
        assert otp_custom.isdigit()

    def test_random_string_generation(self):
        """
        Test random string generation for tokens.
        
        This test ensures that random strings are generated
        with correct length and format.
        """
        # Act: Generate random string
        random_str = AuthService.generate_random_string()
        
        # Assert: Should be 32 characters and alphanumeric
        assert len(random_str) == 32
        assert random_str.isalnum()
        
        # Test custom length
        random_str_custom = AuthService.generate_random_string(16)
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
        token = AuthService.create_access_token(user_id)
        
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

    def test_create_otp_database_interaction(self):
        """
        Test OTP creation with database interaction.
        
        This test ensures that OTP records are created correctly
        in the database with proper data.
        """
        # Arrange: Mock database and test data
        mock_db = MagicMock()
        user_id = 1
        email = "test@example.com"
        purpose = "login"
        
        # Act: Create OTP
        otp_code, expires_at = AuthService.create_otp(
            mock_db, user_id, email, purpose
        )
        
        # Assert: OTP should be created correctly
        assert len(otp_code) == 6
        assert otp_code.isdigit()
        assert isinstance(expires_at, datetime)
        
        # Database operations should be called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # OTP record should have correct data
        otp_record = mock_db.add.call_args[0][0]
        assert otp_record.user_id == user_id
        assert otp_record.email == email
        assert otp_record.code == otp_code
        assert otp_record.purpose == purpose

    def test_verify_otp_success(self):
        """
        Test successful OTP verification.
        
        This test ensures that valid OTPs are verified correctly
        and marked as used.
        """
        # Arrange: Mock database with valid OTP
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_otp_record = MagicMock()
        mock_otp_record.user_id = 1
        mock_otp_record.is_used = False
        
        # Mock database query chain
        mock_db.query.return_value.filter.return_value.first.return_value = mock_otp_record
        
        # Mock user query (second call to query)
        def mock_query_side_effect(model):
            mock_query = MagicMock()
            if model == User:
                mock_query.filter.return_value.first.return_value = mock_user
            else:
                mock_query.filter.return_value.first.return_value = mock_otp_record
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        
        # Act: Verify OTP
        result = AuthService.verify_otp(mock_db, "test@example.com", "123456", "login")
        
        # Assert: Should return user and mark OTP as used
        assert result == mock_user
        assert mock_otp_record.is_used is True
        mock_db.commit.assert_called()

    def test_verify_otp_not_found(self):
        """
        Test OTP verification when OTP doesn't exist.
        
        This test ensures that invalid OTPs return None gracefully.
        """
        # Arrange: Mock database with no OTP found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act: Try to verify non-existent OTP
        result = AuthService.verify_otp(mock_db, "test@example.com", "123456", "login")
        
        # Assert: Should return None
        assert result is None

    def test_get_user_by_email(self):
        """
        Test retrieving user by email address.
        
        This test ensures that users can be found by their email
        and returns None when not found.
        """
        # Arrange: Mock database and user
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        # Test user found
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        result = AuthService.get_user_by_email(mock_db, "test@example.com")
        assert result == mock_user
        
        # Test user not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        result = AuthService.get_user_by_email(mock_db, "nonexistent@example.com")
        assert result is None 


    def test_get_current_user_with_valid_token(self):
        """
        Test getting current user with valid JWT token.
        
        This test ensures that valid tokens return the correct user.
        """
        # Arrange: Create valid token and mock user
        user_id = 123
        token = AuthService.create_access_token(user_id)
        mock_user = MagicMock()
        mock_user.id = user_id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Act: Get current user
        result = AuthService.get_current_user(mock_db, token)
        
        # Assert: Should return the user
        assert result == mock_user

    def test_get_current_user_with_invalid_token(self):
        """
        Test getting current user with invalid JWT token.
        
        This test ensures that invalid tokens raise HTTP exceptions.
        """
        # Arrange: Invalid token
        invalid_token = "invalid.jwt.token"
        mock_db = MagicMock()
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            AuthService.get_current_user(mock_db, invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    def test_get_current_active_user(self):
        """
        Test active user validation.
        
        This test ensures that only active users are allowed through
        and inactive users are rejected.
        """
        # Test active user
        mock_active_user = MagicMock()
        mock_active_user.is_active = True
        result = AuthService.get_current_active_user(mock_active_user)
        assert result == mock_active_user
        
        # Test inactive user
        mock_inactive_user = MagicMock()
        mock_inactive_user.is_active = False
        
        with pytest.raises(HTTPException) as exc_info:
            AuthService.get_current_active_user(mock_inactive_user)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Inactive user" in exc_info.value.detail

    def test_refresh_token_operations(self):
        """
        Test refresh token creation and usage.
        
        This test ensures that refresh tokens are created and
        can be used to generate new access tokens.
        """
        # Test refresh token creation
        mock_db = MagicMock()
        user_id = 123
        
        token = AuthService.create_refresh_token(mock_db, user_id)
        
        # Assert: Token should be created correctly
        assert isinstance(token, str)
        assert len(token) == 64
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Test refresh token usage
        mock_token_record = MagicMock()
        mock_token_record.user_id = user_id
        mock_token_record.is_revoked = False
        mock_token_record.expires_at = datetime.utcnow() + timedelta(days=1)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_token_record
        
        result = AuthService.refresh_access_token(mock_db, "valid_refresh_token")
        assert result is not None
        new_access_token, returned_user_id = result
        assert isinstance(new_access_token, str)
        assert returned_user_id == user_id

    def test_password_update(self):
        """
        Test password update functionality.
        
        This test ensures that user passwords can be updated correctly.
        """
        # Arrange: Mock database and user
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 123
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Act: Update password
        new_password = "new_secure_password"
        AuthService.update_password(mock_db, 123, new_password)
        
        # Assert: Password should be updated and verifiable
        assert hasattr(mock_user, 'hashed_password')
        assert AuthService.verify_password(new_password, mock_user.hashed_password)
        mock_db.commit.assert_called_once()

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    def test_password_verification_with_wrong_password(self):
        """
        Negative Test: Password verification should fail with wrong password.
        
        This test ensures that incorrect passwords are properly rejected
        during verification.
        """
        # Arrange: Hash a password
        correct_password = "correct_password123"
        hashed = AuthService.get_password_hash(correct_password)
        
        # Act & Assert: Wrong password should fail verification
        wrong_password = "wrong_password456"
        assert AuthService.verify_password(wrong_password, hashed) is False

    def test_jwt_token_validation_with_invalid_token(self):
        """
        Negative Test: JWT token validation should fail with malformed token.
        
        This test ensures that invalid or malformed tokens are rejected
        and raise appropriate exceptions.
        """
        # Arrange: Invalid token
        invalid_token = "invalid.malformed.token"
        mock_db = MagicMock()
        
        # Act & Assert: Should raise HTTPException for invalid token
        with pytest.raises(HTTPException) as exc_info:
            AuthService.get_current_user(mock_db, invalid_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    def test_otp_verification_with_expired_or_invalid_otp(self):
        """
        Negative Test: OTP verification should fail with invalid OTP.
        
        This test ensures that non-existent or invalid OTPs are rejected
        and return None appropriately.
        """
        # Arrange: Mock database with no OTP found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act: Try to verify invalid OTP
        result = AuthService.verify_otp(mock_db, "test@example.com", "999999", "login")
        
        # Assert: Should return None for invalid OTP
        assert result is None 