from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from decimal import Decimal


class MessageType(str, Enum):
    """Message types supported by the chat system."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class MessageStatus(str, Enum):
    """Message status options."""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    EDITED = "edited"
    DELETED = "deleted"


class ConversationStatus(str, Enum):
    """Conversation status options."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class WidgetType(str, Enum):
    """Widget types supported by the chat system."""
    DISH_SELECTION = "dish_selection"
    CONFIRMATION = "confirmation"
    INFO_CARD = "info_card"


class WidgetStatus(str, Enum):
    """Widget status options."""
    PENDING = "pending"
    RESOLVED = "resolved"
    EXPIRED = "expired"


# Image and File Attachment Schemas
class ImageAttachment(BaseModel):
    """Schema for image attachments."""
    url: str = Field(..., description="Public URL of the uploaded image")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the image")
    storage_path: str = Field(..., description="Path in Firebase storage")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Image metadata (dimensions, format, etc.)")


class FileAttachment(BaseModel):
    """Schema for general file attachments."""
    url: str = Field(..., description="Public URL of the uploaded file")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME type of the file")
    storage_path: str = Field(..., description="Path in storage")


class DishCard(BaseModel):
    """Simplified dish representation for widgets and UI cards."""
    id: int = Field(..., description="Dish ID")
    name: str = Field(..., description="Dish name")
    description: Optional[str] = Field(default=None, description="Dish description (truncated)")
    cuisine: Optional[str] = Field(default=None, description="Cuisine type")
    image_url: Optional[str] = Field(default=None, description="Primary image URL")
    calories: Optional[Decimal] = Field(default=None, description="Calories per serving")
    protein_g: Optional[Decimal] = Field(default=None, description="Protein in grams")
    carbs_g: Optional[Decimal] = Field(default=None, description="Carbohydrates in grams")
    fats_g: Optional[Decimal] = Field(default=None, description="Fats in grams")
    servings: Optional[int] = Field(default=None, description="Number of servings")


class DishSelectionWidget(BaseModel):
    """Widget for dish selection during intake logging."""
    widget_id: str = Field(..., description="Unique widget identifier")
    widget_type: WidgetType = Field(default=WidgetType.DISH_SELECTION, description="Widget type")
    status: WidgetStatus = Field(default=WidgetStatus.PENDING, description="Widget status")
    title: str = Field(..., description="Widget title")
    description: str = Field(..., description="Widget description")
    search_term: str = Field(..., description="Original search term used")
    extracted_portion: Optional[Decimal] = Field(default=None, description="Extracted portion size from user message")
    dishes: List[DishCard] = Field(..., description="Available dish options")
    selected_dish_id: Optional[int] = Field(default=None, description="Selected dish ID (when resolved)")
    selected_portion: Optional[Decimal] = Field(default=None, description="Selected portion size (when resolved)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional widget metadata")
    created_at: Optional[str] = Field(default=None, description="Widget creation timestamp")
    resolved_at: Optional[str] = Field(default=None, description="Widget resolution timestamp")


class ControlMessage(BaseModel):
    """Schema for control messages that trigger specific actions."""
    action: str = Field(..., description="Action type (e.g., 'confirm_dish_selection')")
    widget_id: str = Field(..., description="Target widget ID")
    data: Dict[str, Any] = Field(..., description="Action-specific data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "confirm_dish_selection",
                "widget_id": "dish_sel_123456",
                "data": {
                    "dish_id": 42,
                    "portion_size": 1.5
                }
            }
        }


class MessageAttachments(BaseModel):
    """Schema for message attachments."""
    images: List[ImageAttachment] = Field(default_factory=list, description="Image attachments")
    files: List[FileAttachment] = Field(default_factory=list, description="File attachments")
    widgets: Optional[List[DishSelectionWidget]] = Field(default=None, description="Interactive widgets")
    tool_results: Optional[Dict[str, Any]] = Field(default=None, description="Results from tool calls")
    control_message: Optional[ControlMessage] = Field(default=None, description="Control message for triggering actions")


# Conversation Schemas
class ConversationBase(BaseModel):
    """Base schema for conversation operations."""
    title: Optional[str] = Field(default=None, max_length=255, description="Conversation title")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional conversation metadata")


class ConversationCreate(ConversationBase):
    """Schema for creating a new conversation."""
    pass


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(default=None, max_length=255, description="Conversation title")
    status: Optional[ConversationStatus] = Field(default=None, description="Conversation status")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional conversation metadata")


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime


class ConversationListItem(BaseModel):
    """Schema for conversation list item with last message preview."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: Optional[str]
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = Field(default=None, description="Preview of the last message")
    last_message_time: Optional[datetime] = Field(default=None, description="Time of the last message")
    unread_count: int = Field(default=0, description="Number of unread messages")


class ConversationListResponse(BaseModel):
    """Schema for paginated conversation list response."""
    conversations: List[ConversationListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# Message Schemas
class MessageBase(BaseModel):
    """Base schema for message operations."""
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    attachments: Optional[Union[Dict[str, Any], MessageAttachments]] = Field(default=None, description="Message attachments (files, images, widgets, etc.)")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")


class MessageCreate(MessageBase):
    """Schema for creating a new message (user message)."""
    parent_message_id: Optional[int] = Field(default=None, description="ID of parent message for threading")


class MessageUpdate(BaseModel):
    """Schema for updating a message."""
    content: Optional[str] = Field(default=None, description="Message content")
    status: Optional[MessageStatus] = Field(default=None, description="Message status")
    reactions: Optional[Dict[str, Any]] = Field(default=None, description="Message reactions")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")


class MessageResponse(MessageBase):
    """Schema for message response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    conversation_id: int
    user_id: int
    is_user_message: bool
    llm_model_id: Optional[int]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    parent_message_id: Optional[int]
    reactions: Optional[Dict[str, Any]]
    status: MessageStatus
    created_at: datetime
    updated_at: datetime


class MessageListResponse(BaseModel):
    """Schema for paginated message list response."""
    messages: List[MessageResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


# AI Chat Specific Schemas
class ChatRequest(BaseModel):
    """Schema for sending a chat message and getting AI response."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    conversation_id: Optional[int] = Field(default=None, description="Existing conversation ID, if any")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for AI")
    attachments: Optional[Union[Dict[str, Any], MessageAttachments]] = Field(default=None, description="Message attachments (files, images, widgets, etc.)")


class ChatWithImageRequest(BaseModel):
    """Schema for sending a chat message with image uploads."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message content")
    conversation_id: Optional[int] = Field(default=None, description="Existing conversation ID, if any")
    message_type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for AI")
    # Note: Images will be handled as UploadFile in the endpoint, not in this schema


class ChatResponse(BaseModel):
    """Schema for chat response including both user and AI messages."""
    conversation_id: int
    user_message: MessageResponse
    ai_message: MessageResponse
    total_tokens_used: int = Field(description="Total tokens used for this interaction")
    cost_estimate: Optional[float] = Field(default=None, description="Estimated cost for this interaction")


class StreamingChatResponse(BaseModel):
    """Schema for streaming chat response."""
    conversation_id: int
    user_message_id: int
    ai_message_id: int
    chunk: str = Field(description="Partial AI response chunk")
    is_complete: bool = Field(default=False, description="Whether this is the final chunk")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens (only in final chunk)")


# Conversation Management Schemas
class ConversationSummaryRequest(BaseModel):
    """Schema for requesting conversation summary."""
    max_length: int = Field(default=200, ge=50, le=500, description="Maximum summary length")


class ConversationSummaryResponse(BaseModel):
    """Schema for conversation summary response."""
    conversation_id: int
    summary: str
    key_topics: List[str]
    message_count: int
    date_range: Dict[str, datetime]


# Image Upload Response Schemas
class ImageUploadResponse(BaseModel):
    """Schema for image upload response."""
    success: bool
    image_url: str
    filename: str
    size: int
    metadata: Dict[str, Any]
    message: str = "Image uploaded successfully" 