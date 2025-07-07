import pytest
from unittest.mock import patch, MagicMock
from app.services.agent import AgentService

class DummyLLMResponse:
    def __init__(self, content):
        self.content = content

@pytest.fixture
def mock_llm(monkeypatch):
    # Patch the ChatOpenAI instance and its invoke method
    monkeypatch.setattr(AgentService, "llm", MagicMock())
    monkeypatch.setattr(AgentService, "vision_llm", MagicMock())
    return AgentService.llm, AgentService.vision_llm


def test_generate_response_basic(monkeypatch):
    # Patch the LLM's invoke method to return a canned response
    with patch.object(AgentService, "llm", create=True) as mock_llm:
        mock_llm_instance = MagicMock()
        # Simulate the first LLM call (tool selection)
        mock_llm_instance.invoke.side_effect = [
            DummyLLMResponse('{"use_tool": false, "response": "Protein is essential for muscle growth."}'),
        ]
        mock_llm.return_value = mock_llm_instance
        response, input_tokens, output_tokens, attachments = AgentService.generate_response(
            user_message="What are the benefits of eating protein?"
        )
        assert isinstance(response, str)
        assert "protein" in response.lower()
        assert isinstance(input_tokens, int)
        assert isinstance(output_tokens, int)
        assert attachments is None or isinstance(attachments, dict)


def test_generate_response_with_attachments(monkeypatch):
    # Patch both llm and vision_llm for image analysis
    with patch.object(AgentService, "llm", create=True) as mock_llm, \
         patch.object(AgentService, "vision_llm", create=True) as mock_vision_llm, \
         patch.object(AgentService, "_process_image_attachments", return_value="Image: healthy food"):
        mock_llm_instance = MagicMock()
        # Simulate the first LLM call (tool selection)
        mock_llm_instance.invoke.side_effect = [
            DummyLLMResponse('{"use_tool": false, "response": "Here is an image of healthy food."}')
        ]
        mock_llm.return_value = mock_llm_instance
        mock_vision_llm_instance = MagicMock()
        mock_vision_llm_instance.invoke.return_value = DummyLLMResponse("A healthy food image.")
        mock_vision_llm.return_value = mock_vision_llm_instance
        response, input_tokens, output_tokens, attachments = AgentService.generate_response(
            user_message="Show me a picture of healthy food.",
            attachments={"images": [{"base64_data": "fakebase64", "content_type": "image/png"}]}
        )
        assert "image" in response.lower()
        assert attachments is None or isinstance(attachments, dict)

# ===== NEGATIVE TESTS =====
# These tests verify that the system properly handles error conditions

def test_generate_response_with_none_message():
    """
    Negative Test: Response generation should handle empty message.
    
    This test ensures that empty user messages
    return appropriate default behavior.
    """
    # Patch LLM to return a simple response
    with patch.object(AgentService, "llm", create=True) as mock_llm:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = DummyLLMResponse('{"use_tool": false, "response": "Please provide a message."}')
        mock_llm.return_value = mock_llm_instance
        
        # Act: Generate response with empty message
        response, input_tokens, output_tokens, attachments = AgentService.generate_response(
            user_message=""  # Empty string instead of None
        )
        
        # Assert: Should handle empty message gracefully
        assert isinstance(response, str)
        assert isinstance(input_tokens, int)
        assert isinstance(output_tokens, int)

def test_generate_response_with_very_long_message():
    """
    Negative Test: Response generation should handle very long messages.
    
    This test ensures that extremely long user messages
    are processed appropriately.
    """
    # Patch LLM to return a response
    with patch.object(AgentService, "llm", create=True) as mock_llm:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = DummyLLMResponse('{"use_tool": false, "response": "Message too long."}')
        mock_llm.return_value = mock_llm_instance
        
        # Act: Generate response with very long message
        very_long_message = "What is protein? " * 1000  # Very long message
        response, input_tokens, output_tokens, attachments = AgentService.generate_response(
            user_message=very_long_message
        )
        
        # Assert: Should handle long message without crashing
        assert isinstance(response, str)
        assert len(response) > 0

# You may add more granular unit tests for tool invocation, error handling, etc.
