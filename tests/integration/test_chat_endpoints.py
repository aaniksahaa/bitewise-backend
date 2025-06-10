import pytest

def test_create_conversation(client):
    payload = {"title": "Test Conversation"}
    response = client.post("/api/v1/chat/conversations", json=payload)
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Conversation"


def test_send_message(client):
    # First, create a conversation
    conv_payload = {"title": "Integration Test Conversation"}
    conv_resp = client.post("/api/v1/chat/conversations", json=conv_payload)
    conv_id = conv_resp.json()["id"]

    # Now, send a message
    msg_payload = {"conversation_id": conv_id, "content": "Hello, this is a test message."}
    msg_resp = client.post("/api/v1/chat/messages", json=msg_payload)
    assert msg_resp.status_code in (200, 201)
    msg_data = msg_resp.json()
    assert msg_data["content"] == "Hello, this is a test message."
    assert msg_data["conversation_id"] == conv_id


def test_get_conversation_messages(client):
    # Create a conversation and send a message
    conv_payload = {"title": "Msg Fetch Test"}
    conv_resp = client.post("/api/v1/chat/conversations", json=conv_payload)
    conv_id = conv_resp.json()["id"]
    msg_payload = {"conversation_id": conv_id, "content": "Fetch this message."}
    client.post("/api/v1/chat/messages", json=msg_payload)

    # Fetch messages
    resp = client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(msg["content"] == "Fetch this message." for msg in data)
