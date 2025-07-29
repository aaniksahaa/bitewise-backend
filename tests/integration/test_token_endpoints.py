#!/usr/bin/env python3
"""
Integration tests for token and password reset endpoints.
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.async_session import get_async_db_manager
from app.services.async_auth import AsyncAuthService
from app.models.user import User
from app.models.auth import RefreshToken, PasswordResetRequest


@pytest.mark.asyncio
async def test_refresh_token_models():
    """Test that refresh token models can be imported."""
    assert RefreshToken is not None
    assert PasswordResetRequest is not None


@pytest.mark.asyncio
async def test_async_auth_service():
    """Test async auth service functionality."""
    assert AsyncAuthService is not None
    
    # Test that the service has the expected methods
    assert hasattr(AsyncAuthService, 'create_refresh_token')
    assert hasattr(AsyncAuthService, 'validate_refresh_token')
    assert hasattr(AsyncAuthService, 'create_password_reset_request')


@pytest.mark.asyncio
async def test_database_connection_for_auth():
    """Test database connection for auth operations."""
    manager = await get_async_db_manager()
    
    async for session in manager.get_async_session():
        assert session is not None
        break  # Exit after first iteration


@pytest.mark.asyncio
async def test_user_model():
    """Test User model can be instantiated."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User"
    )
    
    assert user.email == "test@example.com"
    assert user.username == "testuser"
    assert user.full_name == "Test User"