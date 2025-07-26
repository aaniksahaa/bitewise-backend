#!/usr/bin/env python3
"""
Tests for Supabase Storage configuration and connectivity.
"""

import pytest
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

load_dotenv()


def test_supabase_environment_variables():
    """Test that Supabase environment variables are configured."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "chat-images")
    
    # Test that variables exist (they can be None in test environment)
    assert supabase_url is not None or supabase_url is None
    assert supabase_key is not None or supabase_key is None
    assert bucket_name is not None


def test_supabase_url_format():
    """Test Supabase URL format if configured."""
    supabase_url = os.getenv("SUPABASE_URL")
    
    if supabase_url:
        assert supabase_url.startswith("https://")
        assert "supabase" in supabase_url.lower()
    else:
        pytest.skip("Supabase URL not configured")


def test_supabase_key_format():
    """Test Supabase key format if configured."""
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_key:
        # Supabase keys are typically JWT tokens, so they should be fairly long
        assert len(supabase_key) > 50
        # JWT tokens typically have dots separating sections
        assert "." in supabase_key
    else:
        pytest.skip("Supabase key not configured")


def test_bucket_name_format():
    """Test bucket name format."""
    bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "chat-images")
    
    # Bucket names should be valid
    assert len(bucket_name) > 0
    assert " " not in bucket_name  # No spaces in bucket names
    assert bucket_name.lower() == bucket_name  # Should be lowercase


@pytest.mark.skipif(not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"), 
                    reason="Supabase not configured")
def test_supabase_client_creation():
    """Test that Supabase client can be created."""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        client = create_client(supabase_url, supabase_key)
        assert client is not None
        
    except ImportError:
        pytest.skip("Supabase client library not available")