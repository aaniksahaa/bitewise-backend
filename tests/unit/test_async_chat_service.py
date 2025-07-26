"""
Async unit tests for AsyncChatService.

This module tests the async chat service functionality including:
- Conversation creation and management
- Message creation and retrieval
- Conversation status handling
- Message status and cost calculations
- Async database operations

Tests use async patterns and fixtures for proper async testing.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from datetime import datetime

from app.services.async_chat import AsyncChatService
from app.schemas.chat import ConversationCreate, ConversationUpdate, MessageCreate, ConversationStatus, MessageStatus
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.llm_model import LLMModel
from tests.async_test_utils import AsyncDatabaseTestUtils, AsyncTestCase


class TestAsyncChatService(AsyncTestCase):
    """Test AsyncChatService functionality."""

    @pytest_asyncio.fixture
    async def mock_async_session(self):
        """Create a mock async session for testing."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.execute = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_conversation_success(self, mock_async_session):
        """
        Test successful async conversation creation.
        
        This test ensures that new conversations are created
        correctly with the current user as owner using async operations.
        """
        # Arrange: Conversation data
        conversation_data = ConversationCreate(
            title="Test Conversation",
            extra_data={"topic": "nutrition"}
        )
        user_id = 123
        
        # Mock the created conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.title = "Test Conversation"
        mock_conversation.user_id = user_id
        
        # Act: Create conversation
        result = await AsyncChatService.create_conversation(
            mock_async_session, conversation_data, user_id
        )
        
        # Assert: Should create conversation correctly
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_by_id_success(self, mock_async_session):
        """
        Test successful async conversation retrieval by ID.
        
        This test ensures that conversations can be retrieved
        by their ID for the correct user using async operations.
        """
        # Arrange: Mock conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        mock_conversation.title = "Test Conversation"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Get conversation by ID
        result = await AsyncChatService.get_conversation_by_id(
            mock_async_session, 1, 123
        )
        
        # Assert: Should return the conversation
        assert result == mock_conversation
        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_by_id_not_found(self, mock_async_session):
        """
        Test async conversation retrieval when conversation doesn't exist.
        
        This test ensures that non-existent conversations
        return None gracefully in async operations.
        """
        # Arrange: Mock database with no conversation found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to get non-existent conversation
        result = await AsyncChatService.get_conversation_by_id(
            mock_async_session, 999, 123
        )
        
        # Assert: Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_conversations(self, mock_async_session):
        """
        Test getting user conversations with pagination using async operations.
        
        This test ensures that user conversations are retrieved
        correctly with pagination support.
        """
        # Arrange: Mock conversations
        mock_conversations = [MagicMock() for _ in range(3)]
        
        # Mock count query
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 3
        
        # Mock conversations query
        mock_conversations_result = AsyncMock()
        mock_conversations_result.scalars.return_value.all.return_value = mock_conversations
        
        # Configure session to return different results for different queries
        mock_async_session.execute.side_effect = [mock_count_result, mock_conversations_result]
        
        # Act: Get user conversations
        result = await AsyncChatService.get_user_conversations(
            mock_async_session, 123, page=1, page_size=10
        )
        
        # Assert: Should return paginated conversations
        assert result.total_count == 3
        assert len(result.conversations) == 3
        assert result.page == 1
        assert result.page_size == 10

    @pytest.mark.asyncio
    async def test_update_conversation_success(self, mock_async_session):
        """
        Test successful async conversation update.
        
        This test ensures that conversations can be updated
        by their owners using async operations.
        """
        # Arrange: Mock existing conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        mock_conversation.title = "Original Title"
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        conversation_update = ConversationUpdate(title="Updated Title")
        
        # Act: Update conversation
        result = await AsyncChatService.update_conversation(
            mock_async_session, 1, conversation_update, 123
        )
        
        # Assert: Should update conversation
        assert mock_conversation.title == "Updated Title"
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_conversation_not_found(self, mock_async_session):
        """
        Test async conversation update when conversation doesn't exist.
        
        This test ensures that updating non-existent conversations
        returns None gracefully in async operations.
        """
        # Arrange: Mock database with no conversation found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        conversation_update = ConversationUpdate(title="Updated Title")
        
        # Act: Try to update non-existent conversation
        result = await AsyncChatService.update_conversation(
            mock_async_session, 999, conversation_update, 123
        )
        
        # Assert: Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_conversation_success(self, mock_async_session):
        """
        Test successful async conversation deletion.
        
        This test ensures that conversations can be deleted
        by their owners using async operations.
        """
        # Arrange: Mock existing conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Delete conversation
        result = await AsyncChatService.delete_conversation(
            mock_async_session, 1, 123
        )
        
        # Assert: Should delete conversation
        assert result is True
        mock_async_session.delete.assert_called_once_with(mock_conversation)
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(self, mock_async_session):
        """
        Test async conversation deletion when conversation doesn't exist.
        
        This test ensures that deleting non-existent conversations
        returns False gracefully in async operations.
        """
        # Arrange: Mock database with no conversation found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to delete non-existent conversation
        result = await AsyncChatService.delete_conversation(
            mock_async_session, 999, 123
        )
        
        # Assert: Should return False
        assert result is False

    @pytest.mark.asyncio
    async def test_create_message_success(self, mock_async_session):
        """
        Test successful async message creation.
        
        This test ensures that messages are created correctly
        within conversations using async operations.
        """
        # Arrange: Mock conversation and message data
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        message_data = MessageCreate(
            content="Hello, this is a test message",
            message_type="text"
        )
        
        # Act: Create message
        result = await AsyncChatService.create_message(
            mock_async_session, 1, message_data, 123,
            is_user_message=True, input_tokens=10, output_tokens=20
        )
        
        # Assert: Should create message
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_called_once()
        mock_async_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, mock_async_session):
        """
        Test getting messages from a conversation using async operations.
        
        This test ensures that conversation messages are retrieved
        correctly with pagination.
        """
        # Arrange: Mock messages
        mock_messages = [MagicMock() for _ in range(3)]
        
        # Mock count query
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 3
        
        # Mock messages query
        mock_messages_result = AsyncMock()
        mock_messages_result.scalars.return_value.all.return_value = mock_messages
        
        # Configure session to return different results for different queries
        mock_async_session.execute.side_effect = [mock_count_result, mock_messages_result]
        
        # Act: Get conversation messages
        result = await AsyncChatService.get_conversation_messages(
            mock_async_session, 1, 123, page=1, page_size=10
        )
        
        # Assert: Should return paginated messages
        assert result.total_count == 3
        assert len(result.messages) == 3

    @pytest.mark.asyncio
    async def test_mark_messages_as_read(self, mock_async_session):
        """
        Test marking messages as read using async operations.
        
        This test ensures that unread messages in a conversation
        are properly marked as read.
        """
        # Arrange: Mock conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Mark messages as read
        result = await AsyncChatService.mark_messages_as_read(
            mock_async_session, 1, 123
        )
        
        # Assert: Should mark messages as read
        assert result is True
        mock_async_session.commit.assert_called_once()

    def test_calculate_cost(self):
        """
        Test cost calculation for LLM usage.
        
        This test ensures that token costs are calculated
        correctly based on model pricing.
        """
        # Arrange: Mock LLM model
        mock_llm_model = MagicMock()
        mock_llm_model.cost_per_million_input_tokens = 30.0
        mock_llm_model.cost_per_million_output_tokens = 60.0
        
        # Act: Calculate cost
        cost = AsyncChatService.calculate_cost(100, 50, mock_llm_model)
        
        # Assert: Should calculate cost correctly
        expected_cost = (100 * 30.0 / 1_000_000) + (50 * 60.0 / 1_000_000)
        assert cost == expected_cost

    @pytest.mark.asyncio
    async def test_get_default_llm_model(self, mock_async_session):
        """
        Test getting default LLM model using async operations.
        
        This test ensures that the default LLM model
        is retrieved correctly from the database.
        """
        # Arrange: Mock default LLM model
        mock_model = MagicMock()
        mock_model.model_name = "gpt-4"
        mock_model.is_available = True
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_async_session.execute.return_value = mock_result
        
        # Act: Get default model
        result = await AsyncChatService.get_default_llm_model(mock_async_session)
        
        # Assert: Should return default model
        assert result == mock_model

    @pytest.mark.asyncio
    async def test_conversation_status_filtering(self, mock_async_session):
        """
        Test conversation filtering by status using async operations.
        
        This test ensures that conversations can be filtered
        by their status (active, archived, etc.).
        """
        # Arrange: Mock active conversations
        mock_conversations = [MagicMock() for _ in range(2)]
        for conv in mock_conversations:
            conv.status = ConversationStatus.ACTIVE
        
        # Mock count query
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 2
        
        # Mock conversations query
        mock_conversations_result = AsyncMock()
        mock_conversations_result.scalars.return_value.all.return_value = mock_conversations
        
        mock_async_session.execute.side_effect = [mock_count_result, mock_conversations_result]
        
        # Act: Get conversations with status filter
        result = await AsyncChatService.get_user_conversations(
            mock_async_session, 123, status=ConversationStatus.ACTIVE
        )
        
        # Assert: Should filter by status
        assert result.total_count == 2
        assert len(result.conversations) == 2

    @pytest.mark.asyncio
    async def test_get_llm_model_by_id(self, mock_async_session):
        """
        Test getting LLM model by ID using async operations.
        
        This test ensures that specific LLM models can be retrieved
        by their ID.
        """
        # Arrange: Mock LLM model
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.model_name = "gpt-4"
        
        mock_async_session.get.return_value = mock_model
        
        # Act: Get LLM model by ID
        result = await AsyncChatService.get_llm_model_by_id(mock_async_session, 1)
        
        # Assert: Should return the model
        assert result == mock_model
        mock_async_session.get.assert_called_once_with(LLMModel, 1)

    @pytest.mark.asyncio
    async def test_update_conversation_status(self, mock_async_session):
        """
        Test updating conversation status using async operations.
        
        This test ensures that conversation status can be changed
        (e.g., from active to archived).
        """
        # Arrange: Mock conversation
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 123
        mock_conversation.status = ConversationStatus.ACTIVE
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Update conversation status
        result = await AsyncChatService.update_conversation_status(
            mock_async_session, 1, ConversationStatus.ARCHIVED, 123
        )
        
        # Assert: Should update status
        assert mock_conversation.status == ConversationStatus.ARCHIVED
        mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_by_id(self, mock_async_session):
        """
        Test getting a specific message by ID using async operations.
        
        This test ensures that individual messages can be retrieved
        with proper authorization checks.
        """
        # Arrange: Mock message
        mock_message = MagicMock()
        mock_message.id = 1
        mock_message.user_id = 123
        mock_message.conversation_id = 1
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_message
        mock_async_session.execute.return_value = mock_result
        
        # Act: Get message by ID
        result = await AsyncChatService.get_message_by_id(
            mock_async_session, 1, 123
        )
        
        # Assert: Should return the message
        assert result == mock_message

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    @pytest.mark.asyncio
    async def test_get_conversation_unauthorized_access(self, mock_async_session):
        """
        Negative Test: Conversation access should fail for wrong user.
        
        This test ensures that users cannot access conversations
        that don't belong to them in async operations.
        """
        # Arrange: Mock conversation belonging to different user
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 456  # Different user
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to get conversation as wrong user
        result = await AsyncChatService.get_conversation_by_id(
            mock_async_session, 1, 123
        )
        
        # Assert: Should return None for unauthorized access
        assert result is None

    @pytest.mark.asyncio
    async def test_update_conversation_nonexistent(self, mock_async_session):
        """
        Negative Test: Conversation update should fail for non-existent conversation.
        
        This test ensures that updating non-existent conversations
        returns None appropriately in async operations.
        """
        # Arrange: Mock database with no conversation found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        conversation_update = ConversationUpdate(title="Non-existent")
        
        # Act: Try to update non-existent conversation
        result = await AsyncChatService.update_conversation(
            mock_async_session, 999999, conversation_update, 123
        )
        
        # Assert: Should return None for non-existent conversation
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthorized(self, mock_async_session):
        """
        Negative Test: Conversation deletion should fail for unauthorized user.
        
        This test ensures that users cannot delete conversations
        they don't own in async operations.
        """
        # Arrange: Mock conversation belonging to different user
        mock_conversation = MagicMock()
        mock_conversation.id = 1
        mock_conversation.user_id = 456  # Different user
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_conversation
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to delete conversation as unauthorized user
        result = await AsyncChatService.delete_conversation(
            mock_async_session, 1, 123
        )
        
        # Assert: Should return False for unauthorized deletion
        assert result is False

    @pytest.mark.asyncio
    async def test_create_message_invalid_conversation(self, mock_async_session):
        """
        Negative Test: Message creation should fail for invalid conversation.
        
        This test ensures that messages cannot be created in
        non-existent or unauthorized conversations.
        """
        # Arrange: Mock database with no conversation found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        message_data = MessageCreate(
            content="Test message",
            message_type="text"
        )
        
        # Act: Try to create message in invalid conversation
        result = await AsyncChatService.create_message(
            mock_async_session, 999, message_data, 123,
            is_user_message=True
        )
        
        # Assert: Should return None for invalid conversation
        assert result is None

    @pytest.mark.asyncio
    async def test_get_default_llm_model_not_found(self, mock_async_session):
        """
        Negative Test: Should handle case when no default LLM model exists.
        
        This test ensures that the system handles gracefully when
        no default LLM model is configured.
        """
        # Arrange: Mock database with no default model
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        
        # Act: Try to get default model when none exists
        result = await AsyncChatService.get_default_llm_model(mock_async_session)
        
        # Assert: Should return None when no default model exists
        assert result is None