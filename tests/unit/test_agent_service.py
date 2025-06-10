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
        assert isinstance(attachments, dict)


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
        assert isinstance(attachments, dict)

# You may add more granular unit tests for tool invocation, error handling, etc.
