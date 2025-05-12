from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# Models
class ConversationCreate(BaseModel):
    pass

class MessageCreate(BaseModel):
    content: Optional[str] = None
    images_base64: Optional[List[str]] = None

class HealthMetricCreate(BaseModel):
    metric_type: str
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None

# Dummy responses
class ConversationResponse(BaseModel):
    conversation_id: int
    user_id: int
    started_at: datetime

class MessageResponse(BaseModel):
    message_id: int
    conversation_id: int
    user_id: int
    content: str
    is_user_message: bool
    llm_model_id: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    created_at: datetime
    intake_id: Optional[int] = None

class HealthMetricResponse(BaseModel):
    message_id: int
    conversation_id: int
    metric_type: str
    result: float
    widget_data: dict
    is_user_message: bool
    llm_model_id: int
    input_tokens: int
    output_tokens: int
    created_at: datetime

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation():
    """Create a new conversation."""
    return ConversationResponse(
        conversation_id=1,
        user_id=1,
        started_at=datetime.now()
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(limit: int = 20, offset: int = 0):
    """Get list of conversations."""
    return [
        ConversationResponse(
            conversation_id=1,
            user_id=1,
            started_at=datetime.now()
        )
    ]

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_history(conversation_id: int, limit: int = 50, offset: int = 0):
    """Get conversation history."""
    return [
        MessageResponse(
            message_id=1,
            conversation_id=conversation_id,
            user_id=1,
            content="Hello!",
            is_user_message=True,
            created_at=datetime.now()
        )
    ]

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_chat_message(conversation_id: int, message: MessageCreate):
    """Send a chat message."""
    return MessageResponse(
        message_id=1,
        conversation_id=conversation_id,
        user_id=1,
        content="This is a dummy response",
        is_user_message=False,
        llm_model_id=1,
        input_tokens=10,
        output_tokens=20,
        created_at=datetime.now()
    )

@router.post("/conversations/{conversation_id}/calculate", response_model=HealthMetricResponse)
async def calculate_health_metric(conversation_id: int, metric: HealthMetricCreate):
    """Calculate health metric."""
    return HealthMetricResponse(
        message_id=1,
        conversation_id=conversation_id,
        metric_type=metric.metric_type,
        result=22.5,
        widget_data={
            "description": "Your BMI is in the healthy range (18.5-24.9).",
            "input_fields": [
                {"name": "height_cm", "value": 175.5},
                {"name": "weight_kg", "value": 70.0}
            ],
            "result_label": "BMI: 22.5"
        },
        is_user_message=False,
        llm_model_id=1,
        input_tokens=30,
        output_tokens=50,
        created_at=datetime.now()
    ) 