"""
Unit tests for EmailService.

This module tests the email service functionality including:
- Email sending operations
- Email template generation
- Email parameter handling

Tests use mocking to avoid actual email sending during tests.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.email import EmailService


class TestEmailService:
    """Test EmailService functionality."""

    def test_send_email_basic(self):
        """
        Test basic email sending functionality.
        
        This test ensures that emails are sent with correct parameters
        and the Resend API is called properly.
        """
        # Arrange: Mock the Resend API
        with patch('resend.Emails.send') as mock_send:
            mock_send.return_value = {"id": "email_id_123", "status": "sent"}
            
            email_service = EmailService()
            
            # Act: Send basic email
            result = email_service.send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<h1>Test Content</h1>"
            )
            
            # Assert: Email should be sent with correct parameters
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            
            assert call_args["to"] == ["test@example.com"]
            assert call_args["subject"] == "Test Subject"
            assert call_args["html"] == "<h1>Test Content</h1>"
            assert "from" in call_args
            assert result["id"] == "email_id_123"

    def test_send_email_with_optional_parameters(self):
        """
        Test email sending with optional parameters like CC, BCC, reply-to.
        
        This test ensures that optional email parameters are correctly
        included in the request when provided.
        """
        # Arrange: Mock the Resend API
        with patch('resend.Emails.send') as mock_send:
            mock_send.return_value = {"id": "email_id_456", "status": "sent"}
            
            email_service = EmailService()
            
            # Act: Send email with all optional parameters
            result = email_service.send_email(
                to_email="test@example.com",
                subject="Test Subject",
                html_content="<h1>Test Content</h1>",
                cc=["cc@example.com"],
                bcc=["bcc@example.com"],
                reply_to="reply@example.com"
            )
            
            # Assert: All parameters should be included
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            
            assert call_args["cc"] == ["cc@example.com"]
            assert call_args["bcc"] == ["bcc@example.com"]
            assert call_args["reply_to"] == "reply@example.com"
            assert result["id"] == "email_id_456"

    def test_send_verification_email(self):
        """
        Test verification email sending with OTP.
        
        This test ensures that verification emails are generated
        with correct content and OTP codes.
        """
        # Arrange: Mock the send_email method
        with patch.object(EmailService, 'send_email') as mock_send_email:
            mock_send_email.return_value = {"id": "verification_email_123"}
            
            email_service = EmailService()
            
            # Act: Send verification email
            result = email_service.send_verification_email(
                to_email="newuser@example.com",
                otp="123456",
                username="testuser"
            )
            
            # Assert: Verification email should be sent correctly
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            
            # Check positional arguments: send_email(to_email, subject, html_content)
            assert call_args[0][0] == "newuser@example.com"  # to_email
            assert "Verify Your BiteWise Email Address" in call_args[0][1]  # subject
            assert "123456" in call_args[0][2]  # html_content
            assert "testuser" in call_args[0][2]  # username in content
            assert "Welcome to BiteWise!" in call_args[0][2]

    def test_send_login_otp(self):
        """
        Test login OTP email sending.
        
        This test ensures that login OTP emails contain
        the correct verification code and user information.
        """
        # Arrange: Mock the send_email method
        with patch.object(EmailService, 'send_email') as mock_send_email:
            mock_send_email.return_value = {"id": "login_otp_123"}
            
            email_service = EmailService()
            
            # Act: Send login OTP email
            result = email_service.send_login_otp(
                to_email="user@example.com",
                otp="654321",
                username="loginuser"
            )
            
            # Assert: Login OTP email should be sent correctly
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            
            # Check positional arguments: send_email(to_email, subject, html_content)
            assert call_args[0][0] == "user@example.com"  # to_email
            assert "Your BiteWise Login Code" in call_args[0][1]  # subject
            assert "654321" in call_args[0][2]  # html_content
            assert "loginuser" in call_args[0][2]  # username in content
            assert "login verification code" in call_args[0][2]

    def test_send_password_reset_email(self):
        """
        Test password reset email sending.
        
        This test ensures that password reset emails contain
        the correct reset code and appropriate security messaging.
        """
        # Arrange: Mock the send_email method
        with patch.object(EmailService, 'send_email') as mock_send_email:
            mock_send_email.return_value = {"id": "reset_email_123"}
            
            email_service = EmailService()
            
            # Act: Send password reset email
            result = email_service.send_password_reset_email(
                to_email="reset@example.com",
                otp="789012",
                username="resetuser"
            )
            
            # Assert: Password reset email should be sent correctly
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            
            # Check positional arguments: send_email(to_email, subject, html_content)
            assert call_args[0][0] == "reset@example.com"  # to_email
            assert "Reset Your BiteWise Password" in call_args[0][1]  # subject
            assert "789012" in call_args[0][2]  # html_content
            assert "resetuser" in call_args[0][2]  # username in content
            assert "password reset code" in call_args[0][2]
            assert "15 minutes" in call_args[0][2]  # Expiration time

    def test_send_account_activation_email(self):
        """
        Test account activation email for social login users.
        
        This test ensures that activation emails for OAuth users
        are sent with appropriate welcome messaging.
        """
        # Arrange: Mock the send_email method
        with patch.object(EmailService, 'send_email') as mock_send_email:
            mock_send_email.return_value = {"id": "activation_email_123"}
            
            email_service = EmailService()
            
            # Act: Send account activation email
            result = email_service.send_account_activation_email(
                to_email="oauth@example.com",
                username="oauthuser"
            )
            
            # Assert: Activation email should be sent correctly
            mock_send_email.assert_called_once()
            call_args = mock_send_email.call_args
            
            # Check positional arguments: send_email(to_email, subject, html_content)
            assert call_args[0][0] == "oauth@example.com"  # to_email
            assert "Activate Your BiteWise Account" in call_args[0][1]  # subject
            assert "oauthuser" in call_args[0][2]  # username in content
            assert "Google account" in call_args[0][2]
            assert "Welcome to BiteWise!" in call_args[0][2]

    def test_email_service_initialization(self):
        """
        Test EmailService initialization.
        
        This test ensures that the email service is properly
        initialized with configuration settings.
        """
        # Act: Initialize email service
        email_service = EmailService()
        
        # Assert: Service should be initialized with proper attributes
        assert hasattr(email_service, 'resend')
        assert hasattr(email_service, 'from_email')
        assert hasattr(email_service, 'from_name')

    def test_email_content_generation(self):
        """
        Test that email content is properly formatted.
        
        This test ensures that HTML email content contains
        expected styling and structure.
        """
        # Arrange: Mock the send_email method to capture content
        with patch.object(EmailService, 'send_email') as mock_send_email:
            mock_send_email.return_value = {"id": "content_test_123"}
            
            email_service = EmailService()
            
            # Act: Send verification email
            email_service.send_verification_email(
                to_email="test@example.com",
                otp="123456",
                username="testuser"
            )
            
            # Assert: Email content should be properly formatted
            call_args = mock_send_email.call_args
            html_content = call_args[0][2]  # html_content is the 3rd positional argument
            
            # Check for proper HTML structure
            assert "font-family: Arial, sans-serif" in html_content
            assert "max-width: 600px" in html_content
            assert "<strong>123456</strong>" in html_content
            assert "Hi testuser," in html_content 