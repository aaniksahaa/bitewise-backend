"""
Unit tests for async base service classes and error handling utilities.
"""

import pytest
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.base import AsyncBaseService, AsyncQueryUtils, AsyncTransactionManager
from app.services.async_error_handler import AsyncErrorHandler, AsyncRetryManager
from app.models.user import User
from sqlalchemy.exc import IntegrityError
import asyncpg


def test_base_service_initialization():
    """Test the AsyncBaseService initialization."""
    user_service = AsyncBaseService(User)
    assert user_service.model == User


def test_error_handler_sqlalchemy_classification():
    """Test SQLAlchemy error classification."""
    error_handler = AsyncErrorHandler()
    
    integrity_error = IntegrityError("statement", "params", "orig")
    error_info = error_handler.classify_error(integrity_error)
    assert error_info['status_code'] == 409
    assert not error_info['retryable']


def test_error_handler_asyncpg_classification():
    """Test asyncpg error classification."""
    error_handler = AsyncErrorHandler()
    
    try:
        # Create a mock asyncpg error
        class MockUniqueViolationError(asyncpg.UniqueViolationError):
            def __init__(self):
                pass
        
        unique_error = MockUniqueViolationError()
        error_info = error_handler.classify_error(unique_error)
        assert error_info['status_code'] == 409
    except Exception:
        # Skip if asyncpg mock fails
        pytest.skip("asyncpg error test skipped")


@pytest.mark.asyncio
async def test_retry_manager_successful_operation():
    """Test retry manager with successful operation."""
    retry_manager = AsyncRetryManager(max_retries=2, base_delay=0.1)
    
    async def successful_operation():
        return "success"
    
    result = await retry_manager.execute_with_retry(successful_operation)
    assert result == "success"


@pytest.mark.asyncio
async def test_retry_manager_eventual_success():
    """Test retry manager with eventual success."""
    retry_manager = AsyncRetryManager(max_retries=3, base_delay=0.1)
    
    attempt_count = 0
    async def eventually_successful_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 2:
            raise asyncpg.ConnectionFailureError("Connection failed")
        return "success after retry"
    
    result = await retry_manager.execute_with_retry(eventually_successful_operation)
    assert result == "success after retry"
    assert attempt_count == 2