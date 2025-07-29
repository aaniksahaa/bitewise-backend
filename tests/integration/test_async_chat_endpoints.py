"""
Async integration tests for chat endpoints.

This module tests the chat API endpoints using async patterns,
ensuring that the full request-response cycle works correctly
with async database operations.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.async_test_utils import AsyncAPITestUtils, AsyncTestScenarios


class TestAsyncChatEndpoints:
    """Test async chat endpoints integration."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation creation endpoint.
        
        This test ensures that conversations can be created
        through the API using async operations.
        """
        # Arrange: Conversation payload
        payload = {"title": "Test Async Conversation"}
        
        # Act: Create conversation
        response = await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Assert: Should create conversation successfully
        assert response.status_code in (200, 201)
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Async Conversation"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_user_conversations(self, async_client: AsyncClient, async_auth_header):
        """
        Test async user conversations retrieval endpoint.
        
        This test ensures that user conversations can be retrieved
        with pagination through async operations.
        """
        # Arrange: Create a conversation first
        payload = {"title": "Test Conversation for Retrieval"}
        await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Act: Get user conversations
        response = await async_client.get(
            "/api/v1/chat/conversations", 
            headers=async_auth_header
        )
        
        # Assert: Should return conversations
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert "total_count" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["conversations"], list)
        assert data["total_count"] >= 1

    @pytest.mark.asyncio
    async def test_get_conversation_by_id(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation retrieval by ID endpoint.
        
        This test ensures that specific conversations can be retrieved
        by their ID using async operations.
        """
        # Arrange: Create a conversation first
        payload = {"title": "Test Conversation by ID"}
        create_response = await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        conv_id = create_response.json()["id"]
        
        # Act: Get conversation by ID
        response = await async_client.get(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=async_auth_header
        )
        
        # Assert: Should return the conversation
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert data["title"] == "Test Conversation by ID"

    @pytest.mark.asyncio
    async def test_update_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation update endpoint.
        
        This test ensures that conversations can be updated
        through the API using async operations.
        """
        # Arrange: Create a conversation first
        payload = {"title": "Original Title"}
        create_response = await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        conv_id = create_response.json()["id"]
        
        # Act: Update conversation
        update_payload = {"title": "Updated Title"}
        response = await async_client.put(
            f"/api/v1/chat/conversations/{conv_id}", 
            json=update_payload, 
            headers=async_auth_header
        )
        
        # Assert: Should update conversation
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["id"] == conv_id

    @pytest.mark.asyncio
    async def test_delete_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation deletion endpoint.
        
        This test ensures that conversations can be deleted
        through the API using async operations.
        """
        # Arrange: Create a conversation first
        payload = {"title": "Conversation to Delete"}
        create_response = await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        conv_id = create_response.json()["id"]
        
        # Act: Delete conversation
        response = await async_client.delete(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=async_auth_header
        )
        
        # Assert: Should delete conversation
        assert response.status_code in (200, 204)
        
        # Verify conversation is deleted
        get_response = await async_client.get(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=async_auth_header
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message(self, async_client: AsyncClient, async_auth_header):
        """
        Test async message sending endpoint.
        
        This test ensures that messages can be sent to conversations
        through the API using async operations.
        """
        # Arrange: Create a conversation first
        conv_payload = {"title": "Integration Test Conversation"}
        conv_resp = await async_client.post(
            "/api/v1/chat/conversations", 
            json=conv_payload, 
            headers=async_auth_header
        )
        conv_id = conv_resp.json()["id"]

        # Act: Send a message
        msg_payload = {"content": "Hello, this is an async test message."}
        msg_resp = await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            json=msg_payload, 
            headers=async_auth_header
        )
        
        # Assert: Should send message successfully
        assert msg_resp.status_code in (200, 201)
        msg_data = msg_resp.json()
        assert msg_data["content"] == "Hello, this is an async test message."
        assert msg_data["conversation_id"] == conv_id
        assert msg_data["is_user_message"] is True
        assert msg_data["message_type"] == "text"

    @pytest.mark.asyncio
    async def test_get_conversation_messages(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation messages retrieval endpoint.
        
        This test ensures that conversation messages can be retrieved
        with pagination through async operations.
        """
        # Arrange: Create a conversation and send a message
        conv_payload = {"title": "Msg Fetch Test"}
        conv_resp = await async_client.post(
            "/api/v1/chat/conversations", 
            json=conv_payload, 
            headers=async_auth_header
        )
        conv_id = conv_resp.json()["id"]
        
        msg_payload = {"content": "Fetch this async message."}
        await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            json=msg_payload, 
            headers=async_auth_header
        )

        # Act: Fetch messages
        resp = await async_client.get(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            headers=async_auth_header
        )
        
        # Assert: Should return messages
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert "total_count" in data
        assert "page" in data
        assert isinstance(data["messages"], list)
        assert any(msg["content"] == "Fetch this async message." for msg in data["messages"])

    @pytest.mark.asyncio
    async def test_mark_messages_as_read(self, async_client: AsyncClient, async_auth_header):
        """
        Test async mark messages as read endpoint.
        
        This test ensures that messages can be marked as read
        through the API using async operations.
        """
        # Arrange: Create conversation and message
        conv_payload = {"title": "Read Status Test"}
        conv_resp = await async_client.post(
            "/api/v1/chat/conversations", 
            json=conv_payload, 
            headers=async_auth_header
        )
        conv_id = conv_resp.json()["id"]
        
        msg_payload = {"content": "Mark me as read."}
        await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            json=msg_payload, 
            headers=async_auth_header
        )

        # Act: Mark messages as read
        resp = await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages/read", 
            headers=async_auth_header
        )
        
        # Assert: Should mark messages as read
        assert resp.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_conversation_pagination(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation pagination.
        
        This test ensures that conversation pagination works correctly
        with async operations.
        """
        # Arrange: Create multiple conversations
        for i in range(5):
            payload = {"title": f"Pagination Test Conversation {i}"}
            await async_client.post(
                "/api/v1/chat/conversations", 
                json=payload, 
                headers=async_auth_header
            )

        # Act: Get conversations with pagination
        response = await async_client.get(
            "/api/v1/chat/conversations?page=1&page_size=3", 
            headers=async_auth_header
        )
        
        # Assert: Should return paginated results
        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) <= 3
        assert data["page"] == 1
        assert data["page_size"] == 3
        assert data["total_count"] >= 5

    @pytest.mark.asyncio
    async def test_conversation_status_filter(self, async_client: AsyncClient, async_auth_header):
        """
        Test async conversation filtering by status.
        
        This test ensures that conversations can be filtered
        by status through async operations.
        """
        # Arrange: Create conversations with different statuses
        active_payload = {"title": "Active Conversation"}
        await async_client.post(
            "/api/v1/chat/conversations", 
            json=active_payload, 
            headers=async_auth_header
        )

        # Act: Get active conversations
        response = await async_client.get(
            "/api/v1/chat/conversations?status=active", 
            headers=async_auth_header
        )
        
        # Assert: Should return filtered conversations
        assert response.status_code == 200
        data = response.json()
        assert all(conv["status"] == "active" for conv in data["conversations"])

    @pytest.mark.asyncio
    async def test_message_with_attachments(self, async_client: AsyncClient, async_auth_header):
        """
        Test async message sending with attachments.
        
        This test ensures that messages with attachments can be sent
        through async operations.
        """
        # Arrange: Create conversation
        conv_payload = {"title": "Attachment Test"}
        conv_resp = await async_client.post(
            "/api/v1/chat/conversations", 
            json=conv_payload, 
            headers=async_auth_header
        )
        conv_id = conv_resp.json()["id"]

        # Act: Send message with attachments
        msg_payload = {
            "content": "Message with attachment",
            "attachments": [{"type": "image", "url": "https://example.com/image.jpg"}]
        }
        response = await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            json=msg_payload, 
            headers=async_auth_header
        )
        
        # Assert: Should handle attachments
        assert response.status_code in (200, 201)
        data = response.json()
        assert data["content"] == "Message with attachment"
        if "attachments" in data:
            assert isinstance(data["attachments"], list)

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    @pytest.mark.asyncio
    async def test_get_nonexistent_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Negative Test: Should return 404 for non-existent conversation.
        
        This test ensures that requesting non-existent conversations
        returns appropriate error responses in async operations.
        """
        # Act: Try to get non-existent conversation
        response = await async_client.get(
            "/api/v1/chat/conversations/999999", 
            headers=async_auth_header
        )
        
        # Assert: Should return 404
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Negative Test: Should return 404 when updating non-existent conversation.
        
        This test ensures that updating non-existent conversations
        returns appropriate error responses in async operations.
        """
        # Act: Try to update non-existent conversation
        payload = {"title": "Updated Title"}
        response = await async_client.put(
            "/api/v1/chat/conversations/999999", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Assert: Should return 404
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_conversation(self, async_client: AsyncClient, async_auth_header):
        """
        Negative Test: Should return 404 when sending message to non-existent conversation.
        
        This test ensures that sending messages to non-existent conversations
        returns appropriate error responses in async operations.
        """
        # Act: Try to send message to non-existent conversation
        payload = {"content": "This should fail"}
        response = await async_client.post(
            "/api/v1/chat/conversations/999999/messages", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Assert: Should return 404
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthorized_conversation_access(self, async_client: AsyncClient):
        """
        Negative Test: Should return 401 for unauthorized access.
        
        This test ensures that accessing conversations without authentication
        returns appropriate error responses in async operations.
        """
        # Act: Try to access conversations without auth header
        response = await async_client.get("/api/v1/chat/conversations")
        
        # Assert: Should return 401
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_conversation_data(self, async_client: AsyncClient, async_auth_header):
        """
        Negative Test: Should return 422 for invalid conversation data.
        
        This test ensures that invalid conversation data
        returns appropriate validation errors in async operations.
        """
        # Act: Try to create conversation with invalid data
        payload = {"title": ""}  # Empty title should be invalid
        response = await async_client.post(
            "/api/v1/chat/conversations", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Assert: Should return validation error
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_invalid_message_data(self, async_client: AsyncClient, async_auth_header):
        """
        Negative Test: Should return 422 for invalid message data.
        
        This test ensures that invalid message data
        returns appropriate validation errors in async operations.
        """
        # Arrange: Create conversation first
        conv_payload = {"title": "Test Conversation"}
        conv_resp = await async_client.post(
            "/api/v1/chat/conversations", 
            json=conv_payload, 
            headers=async_auth_header
        )
        conv_id = conv_resp.json()["id"]

        # Act: Try to send message with invalid data
        payload = {"content": ""}  # Empty content should be invalid
        response = await async_client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            json=payload, 
            headers=async_auth_header
        )
        
        # Assert: Should return validation error
        assert response.status_code in (400, 422)


class TestAsyncChatEndpointsWithScenarios:
    """Test async chat endpoints using test scenarios."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, async_client: AsyncClient, async_auth_header):
        """
        Test complete conversation flow using async operations.
        
        This test covers the full lifecycle of a conversation:
        create -> send messages -> retrieve messages -> update -> delete
        """
        api_utils = AsyncAPITestUtils(async_client)
        
        # Step 1: Create conversation
        conv_payload = {"title": "Full Flow Test"}
        conv_response = await api_utils.post_json(
            "/api/v1/chat/conversations", 
            conv_payload, 
            async_auth_header
        )
        await api_utils.assert_status_code(conv_response, 201)
        conv_data = await api_utils.assert_json_response(conv_response, ["id", "title"])
        conv_id = conv_data["id"]

        # Step 2: Send multiple messages
        messages = ["Hello!", "How are you?", "This is a test conversation."]
        for content in messages:
            msg_payload = {"content": content}
            msg_response = await api_utils.post_json(
                f"/api/v1/chat/conversations/{conv_id}/messages", 
                msg_payload, 
                async_auth_header
            )
            await api_utils.assert_status_code(msg_response, 201)

        # Step 3: Retrieve messages
        messages_response = await api_utils.get(
            f"/api/v1/chat/conversations/{conv_id}/messages", 
            headers=async_auth_header
        )
        await api_utils.assert_status_code(messages_response, 200)
        messages_data = await api_utils.assert_json_response(
            messages_response, ["messages", "total_count"]
        )
        assert messages_data["total_count"] >= len(messages)

        # Step 4: Update conversation
        update_payload = {"title": "Updated Full Flow Test"}
        update_response = await api_utils.put_json(
            f"/api/v1/chat/conversations/{conv_id}", 
            update_payload, 
            async_auth_header
        )
        await api_utils.assert_status_code(update_response, 200)

        # Step 5: Delete conversation
        delete_response = await api_utils.delete(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=async_auth_header
        )
        await api_utils.assert_status_code(delete_response, 204)

        # Step 6: Verify deletion
        get_response = await api_utils.get(
            f"/api/v1/chat/conversations/{conv_id}", 
            headers=async_auth_header
        )
        await api_utils.assert_status_code(get_response, 404)