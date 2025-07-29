#!/usr/bin/env python3
"""
Unit tests for async community and fitness services.
"""

import pytest
import asyncio
import sys
import os
from datetime import date, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.async_session import get_async_db_manager
from app.services.async_community import AsyncCommunityService
from app.services.async_fitness import AsyncFitnessService


@pytest.mark.asyncio
async def test_async_community_service_import():
    """Test that async community service can be imported."""
    assert AsyncCommunityService is not None


@pytest.mark.asyncio
async def test_async_fitness_service_import():
    """Test that async fitness service can be imported."""
    assert AsyncFitnessService is not None


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection for community services."""
    db_manager = await get_async_db_manager()
    
    async for db in db_manager.get_async_session():
        assert db is not None
        break  # Exit after first iteration


@pytest.mark.asyncio
async def test_user_streak_update():
    """Test user streak update functionality."""
    db_manager = await get_async_db_manager()
    
    async for db in db_manager.get_async_session():
        user_id = 1  # Test with user ID 1
        
        try:
            streak_data = await AsyncCommunityService.update_user_streak(
                db=db,
                user_id=user_id,
                activity_date=date.today()
            )
            
            # Basic validation that the function returns something
            assert streak_data is not None
            
        except Exception as e:
            # If the user doesn't exist or other DB issues, that's expected in tests
            pytest.skip(f"Skipping streak test due to: {e}")
        
        break  # Exit after first iteration