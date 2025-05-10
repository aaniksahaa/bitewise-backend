from datetime import datetime
from typing import Dict, List, Optional

import resend

from app.core.config import settings


class EmailService:
    def __init__(self):
        self.resend = resend.api_key=settings.RESEND_API_KEY
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict:
        """Send an email using Resend."""
        params = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        if reply_to:
            params["reply_to"] = reply_to

        return resend.Emails.send(params)

    def send_verification_email(self, to_email: str, otp: str, username: str) -> Dict:
        """Send a verification email with OTP to a new user."""
        subject = "Verify Your BiteWise Email Address"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Welcome to BiteWise!</h2>
            <p>Hi {username},</p>
            <p>Thanks for signing up! Please verify your email address to activate your account.</p>
            <p>Your verification code is: <strong>{otp}</strong></p>
            <p>This code will expire in 5 minutes.</p>
            <p>If you didn't sign up for BiteWise, you can safely ignore this email.</p>
            <p>Best regards,<br>The BiteWise Team</p>
        </div>
        """
        return self.send_email(to_email, subject, html_content)

    def send_login_otp(self, to_email: str, otp: str, username: str) -> Dict:
        """Send a login OTP to a user."""
        subject = "Your BiteWise Login Code"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>BiteWise Login Verification</h2>
            <p>Hi {username},</p>
            <p>Your login verification code is: <strong>{otp}</strong></p>
            <p>This code will expire in 5 minutes.</p>
            <p>If you didn't attempt to log in to BiteWise, please secure your account immediately.</p>
            <p>Best regards,<br>The BiteWise Team</p>
        </div>
        """
        return self.send_email(to_email, subject, html_content)

    def send_password_reset_email(self, to_email: str, otp: str, username: str) -> Dict:
        """Send a password reset email with OTP."""
        subject = "Reset Your BiteWise Password"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>BiteWise Password Reset</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your password. Your password reset code is:</p>
            <p><strong>{otp}</strong></p>
            <p>This code will expire in 15 minutes.</p>
            <p>If you didn't request a password reset, you can safely ignore this email.</p>
            <p>Best regards,<br>The BiteWise Team</p>
        </div>
        """
        return self.send_email(to_email, subject, html_content)

    def send_account_activation_email(self, to_email: str, username: str) -> Dict:
        """Send an account activation email for social login users."""
        subject = "Activate Your BiteWise Account"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Welcome to BiteWise!</h2>
            <p>Hi {username},</p>
            <p>Thank you for signing up with BiteWise using your Google account. Your account has been successfully created.</p>
            <p>We're excited to have you on board!</p>
            <p>Best regards,<br>The BiteWise Team</p>
        </div>
        """
        return self.send_email(to_email, subject, html_content) 