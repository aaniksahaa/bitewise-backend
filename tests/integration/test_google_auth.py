#!/usr/bin/env python3
"""
Integration tests for Google OAuth authentication endpoints.
"""

import pytest
import sys
import os
import requests
from urllib.parse import urlparse, parse_qs

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.config import settings


def test_google_oauth_config():
    """Test Google OAuth configuration."""
    # Check if required environment variables are set
    assert settings.GOOGLE_CLIENT_ID is not None, "GOOGLE_CLIENT_ID is not set"
    assert settings.GOOGLE_CLIENT_SECRET is not None, "GOOGLE_CLIENT_SECRET is not set"
    assert settings.GOOGLE_CALLBACK_URL is not None, "GOOGLE_CALLBACK_URL is not set"


def test_google_oauth_url_format():
    """Test that Google OAuth callback URL is properly formatted."""
    if settings.GOOGLE_CALLBACK_URL:
        parsed_url = urlparse(settings.GOOGLE_CALLBACK_URL)
        assert parsed_url.scheme in ['http', 'https']
        assert parsed_url.netloc != ''
        assert '/auth/google/callback' in parsed_url.path


@pytest.mark.skipif(not settings.GOOGLE_CLIENT_ID, reason="Google OAuth not configured")
def test_google_oauth_client_id_format():
    """Test that Google Client ID has the expected format."""
    client_id = settings.GOOGLE_CLIENT_ID
    # Google Client IDs typically end with .apps.googleusercontent.com
    assert client_id.endswith('.apps.googleusercontent.com') or len(client_id) > 20


def test_settings_import():
    """Test that settings can be imported successfully."""
    assert settings is not None
    assert hasattr(settings, 'GOOGLE_CLIENT_ID')
    assert hasattr(settings, 'GOOGLE_CLIENT_SECRET')
    assert hasattr(settings, 'GOOGLE_CALLBACK_URL')