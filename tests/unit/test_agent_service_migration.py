#!/usr/bin/env python3
"""
Unit tests for the BiteWise Agent Service.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.agent import AgentService


@pytest.fixture
def mock_openai_key():
    """Mock OpenAI API key for testing."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        yield


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not set")
def test_general_question():
    """Test the agent with a general nutrition question."""
    user_message = "What are the benefits of eating protein?"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert isinstance(input_tokens, int)
    assert isinstance(output_tokens, int)
    assert isinstance(attachments, list)


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not set")
def test_search_query():
    """Test the agent with a dish search query (without DB)."""
    user_message = "Can you help me find some chicken dishes?"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert isinstance(input_tokens, int)
    assert isinstance(output_tokens, int)
    assert isinstance(attachments, list)


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OpenAI API key not set")
def test_log_intake_query():
    """Test the agent with an intake logging query (without DB)."""
    user_message = "I just ate a grilled chicken breast"
    response, input_tokens, output_tokens, attachments = AgentService.generate_response(
        user_message=user_message
    )
    
    assert isinstance(response, str)
    assert len(response) > 0
    assert isinstance(input_tokens, int)
    assert isinstance(output_tokens, int)
    assert isinstance(attachments, list)


def test_agent_service_without_api_key():
    """Test that agent service handles missing API key gracefully."""
    with patch.dict(os.environ, {}, clear=True):
        # Remove OPENAI_API_KEY if it exists
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        with pytest.raises(Exception):
            AgentService.generate_response("test message")