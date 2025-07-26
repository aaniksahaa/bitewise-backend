#!/usr/bin/env python3
"""
Integration tests for async database monitoring and error tracking.
"""

import pytest
import asyncio
import logging
import time
from datetime import datetime, timezone
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_monitoring_components_import():
    """Test that monitoring components can be imported."""
    from app.services.async_metrics import get_metrics_collector
    from app.services.async_error_tracking import get_error_tracker
    from app.db.monitored_session import get_monitored_async_db
    from app.db.async_session import get_async_db_manager
    
    # Initialize components
    metrics_collector = get_metrics_collector()
    error_tracker = get_error_tracker()
    db_manager = await get_async_db_manager()
    
    assert metrics_collector is not None
    assert error_tracker is not None
    assert db_manager is not None


@pytest.mark.asyncio
async def test_database_health_check():
    """Test database health check functionality."""
    from app.db.async_session import get_async_db_manager
    
    db_manager = await get_async_db_manager()
    health_status = await db_manager.perform_health_check_with_recovery()
    
    assert 'status' in health_status
    assert 'checks' in health_status
    assert health_status['checks'].get('basic_connection') is not None


@pytest.mark.asyncio
async def test_monitored_session_successful_queries():
    """Test monitored session with successful queries."""
    from app.db.monitored_session import get_monitored_async_db
    from sqlalchemy import text
    
    async with get_monitored_async_db() as session:
        result = await session.execute(text("SELECT 1 as test_value"))
        value = result.scalar()
        assert value == 1


@pytest.mark.asyncio
async def test_error_tracking():
    """Test error tracking functionality."""
    from app.services.async_error_tracking import get_error_tracker
    
    error_tracker = get_error_tracker()
    
    # Test error logging
    test_error = Exception("Test error for tracking")
    await error_tracker.log_error(
        error=test_error,
        context={"test": "error_tracking"},
        user_id=None
    )
    
    # This test mainly ensures no exceptions are raised during error logging
    assert True


@pytest.mark.asyncio
async def test_metrics_collection():
    """Test metrics collection functionality."""
    from app.services.async_metrics import get_metrics_collector
    
    metrics_collector = get_metrics_collector()
    
    # Test recording a metric
    await metrics_collector.record_query_time("test_query", 0.1)
    await metrics_collector.record_connection_event("connection_created")
    
    # This test mainly ensures no exceptions are raised during metrics collection
    assert True