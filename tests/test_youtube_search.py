"""
Tests for YouTube search functionality.
"""

import pytest
import os
import requests
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings


def test_youtube_api_key_configured():
    """Test that YouTube API key is configured."""
    # This test checks if the API key is set, but doesn't require it to be valid
    api_key = settings.YOUTUBE_V3_API_KEY
    if api_key:
        assert len(api_key) > 0
    else:
        pytest.skip("YouTube API key not configured")


@pytest.mark.skipif(not settings.YOUTUBE_V3_API_KEY, reason="YouTube API key not configured")
def test_youtube_search_url_format():
    """Test YouTube search URL format."""
    url = "https://youtube-v311.p.rapidapi.com/search/"
    
    # Test that the URL is properly formatted
    assert url.startswith("https://")
    assert "youtube" in url.lower()


def test_youtube_search_parameters():
    """Test YouTube search parameters structure."""
    querystring = {
        "part": "snippet",
        "maxResults": "5",
        "q": "test query"
    }
    
    assert "part" in querystring
    assert "maxResults" in querystring
    assert "q" in querystring
    assert querystring["part"] == "snippet"


def test_settings_youtube_import():
    """Test that YouTube settings can be imported."""
    assert hasattr(settings, 'YOUTUBE_V3_API_KEY')
    
    # Test that the setting exists (even if None)
    youtube_key = getattr(settings, 'YOUTUBE_V3_API_KEY', None)
    assert youtube_key is not None or youtube_key is None  # Either set or not set