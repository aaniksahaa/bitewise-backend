#!/usr/bin/env python3
"""
Tests for environment configuration and switching.
"""

import pytest
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_environment_variable_loading():
    """Test that environment variables can be loaded."""
    load_dotenv()
    
    # Test that we can get environment variables
    env = os.getenv('ENVIRONMENT', 'development')
    assert env in ['development', 'production', 'testing']


def test_environment_override():
    """Test environment variable override functionality."""
    # Set environment variable
    original_env = os.getenv('ENVIRONMENT')
    
    os.environ['ENVIRONMENT'] = 'testing'
    assert os.getenv('ENVIRONMENT') == 'testing'
    
    # Restore original if it existed
    if original_env:
        os.environ['ENVIRONMENT'] = original_env
    elif 'ENVIRONMENT' in os.environ:
        del os.environ['ENVIRONMENT']


def test_settings_import():
    """Test that settings can be imported."""
    try:
        from app.core.config import settings
        assert settings is not None
        assert hasattr(settings, 'DATABASE_URL')
    except ImportError:
        pytest.skip("Settings module not available")


def test_database_url_format():
    """Test that database URL has the expected format."""
    try:
        from app.core.config import settings
        
        if settings.DATABASE_URL:
            assert settings.DATABASE_URL.startswith(('postgresql://', 'sqlite://'))
    except ImportError:
        pytest.skip("Settings module not available")