#!/usr/bin/env python3

"""
Integration test for async chat endpoints.
This test checks basic functionality and async database operations.
"""

import asyncio
import sys
import os
import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.async_session import get_async_db
from app.services.async_chat import AsyncChatService
from app.schemas.chat import ConversationCreate, MessageCreate, MessageType


@pytest.mark.asyncio
async def test_async_chat_service():
    """Test basic async chat service functionality."""
    
    # Get async database session
    async for db in get_async_db():
        # Test creating a conversation
        conversation_data = ConversationCreate(
            title="Test Async Conversation"
        )
        
        # Use a test user ID (assuming user 1 exists)
        test_user_id = 1
        
        conversation = await AsyncChatService.create_conversation(
            db=db,
            conversation_data=conversation_data,
            current_user_id=test_user_id
        )
        assert conversation.id is not None
        
        # Test creating a message
        message_data = MessageCreate(
            content="Test async message",
            message_type=MessageType.TEXT
        )
        
        message = await AsyncChatService.create_message(
            db=db,
            conversation_id=conversation.id,
            message_data=message_data,
            current_user_id=test_user_id,
            is_user_message=True
        )
        assert message.id is not None
        
        # Test getting conversation messages
        messages = await AsyncChatService.get_conversation_messages(
            db=db,
            conversation_id=conversation.id,
            current_user_id=test_user_id
        )
        assert messages.total_count >= 1
        
        # Test getting user conversations
        conversations = await AsyncChatService.get_user_conversations(
            db=db,
            current_user_id=test_user_id
        )
        assert conversations.total_count >= 1
        
        break  # Exit the async generator


if __name__ == "__main__":
    asyncio.run(test_async_chat_service())