import os
import json
import math
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from fastapi import HTTPException, status

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.llm_model import LLMModel
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate, ConversationUpdate, ConversationResponse, ConversationListResponse,
    MessageCreate, MessageUpdate, MessageResponse, MessageListResponse,
    ConversationSummaryResponse, ConversationStatus, ConversationListItem, MessageStatus
)


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def convert_decimals_to_floats(obj: Any) -> Any:
    """Recursively convert Decimal objects to floats in nested data structures."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_floats(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_floats(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals_to_floats(item) for item in obj)
    else:
        return obj


class ChatService:
    """Service class for handling chat operations."""
    
    @staticmethod
    def create_conversation(
        db: Session, 
        conversation_data: ConversationCreate, 
        current_user_id: int
    ) -> ConversationResponse:
        """Create a new conversation."""
        db_conversation = Conversation(
            user_id=current_user_id,
            title=conversation_data.title,
            status=ConversationStatus.ACTIVE,
            extra_data=conversation_data.extra_data or {}
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        return ConversationResponse.model_validate(db_conversation)

    @staticmethod
    def get_conversation_by_id(
        db: Session, 
        conversation_id: int, 
        current_user_id: int
    ) -> Optional[ConversationResponse]:
        """Get a conversation by ID (only for the current user)."""
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            return None
        
        return ConversationResponse.model_validate(conversation)

    @staticmethod
    def get_user_conversations(
        db: Session,
        current_user_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[ConversationStatus] = None
    ) -> ConversationListResponse:
        """Get all conversations for the current user with pagination."""
        query = db.query(Conversation).filter(
            and_(
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        )
        
        # Apply status filter if provided
        if status:
            query = query.filter(Conversation.status == status)
        
        # Order by updated_at descending (most recent first)
        query = query.order_by(desc(Conversation.updated_at))
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        conversations = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format with additional data
        conversation_items = []
        for conv in conversations:
            # Get last message for preview
            last_message = db.query(Message).filter(
                Message.conversation_id == conv.id
            ).order_by(desc(Message.created_at)).first()
            
            # Get unread count (messages not read by user)
            unread_count = db.query(Message).filter(
                and_(
                    Message.conversation_id == conv.id,
                    Message.is_user_message == False,
                    Message.status != MessageStatus.READ
                )
            ).count()
            
            item = ConversationListItem(
                id=conv.id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                last_message_preview=last_message.content[:100] + "..." if last_message and len(last_message.content) > 100 else last_message.content if last_message else None,
                last_message_time=last_message.created_at if last_message else None,
                unread_count=unread_count
            )
            conversation_items.append(item)
        
        return ConversationListResponse(
            conversations=conversation_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: int,
        conversation_update: ConversationUpdate,
        current_user_id: int
    ) -> Optional[ConversationResponse]:
        """Update a conversation (only for the current user)."""
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            return None
        
        # Update only provided fields
        update_data = conversation_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(conversation, field, value)
        
        db.commit()
        db.refresh(conversation)
        
        return ConversationResponse.model_validate(conversation)

    @staticmethod
    def delete_conversation(
        db: Session, 
        conversation_id: int, 
        current_user_id: int
    ) -> bool:
        """Soft delete a conversation (only for the current user)."""
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            return False
        
        # Soft delete by updating status
        conversation.status = ConversationStatus.DELETED
        db.commit()
        
        return True

    @staticmethod
    def create_message(
        db: Session,
        conversation_id: int,
        message_data: MessageCreate,
        current_user_id: int,
        is_user_message: bool = True,
        llm_model_id: Optional[int] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> MessageResponse:
        """Create a new message in a conversation."""
        # Verify conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Create message
        # Convert any Decimal objects in attachments to floats for JSON serialization
        clean_attachments = convert_decimals_to_floats(message_data.attachments) if message_data.attachments else None
        clean_extra_data = convert_decimals_to_floats(message_data.extra_data) if message_data.extra_data else None
        
        db_message = Message(
            conversation_id=conversation_id,
            user_id=current_user_id,
            content=message_data.content,
            is_user_message=is_user_message,
            message_type=message_data.message_type,
            attachments=clean_attachments,
            extra_data=clean_extra_data,
            parent_message_id=message_data.parent_message_id,
            llm_model_id=llm_model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            status=MessageStatus.SENT
        )
        
        db.add(db_message)
        
        # Update conversation's updated_at timestamp
        conversation.updated_at = func.now()
        
        db.commit()
        db.refresh(db_message)
        
        return MessageResponse.model_validate(db_message)

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: int,
        current_user_id: int,
        page: int = 1,
        page_size: int = 50
    ) -> MessageListResponse:
        """Get messages for a conversation with pagination."""
        # Verify conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        query = db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.status != MessageStatus.DELETED
            )
        )
        
        # Order by created_at ascending (chronological order)
        query = query.order_by(Message.created_at.asc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        messages = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        message_items = [MessageResponse.model_validate(message) for message in messages]
        
        return MessageListResponse(
            messages=message_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_message(
        db: Session,
        message_id: int,
        message_update: MessageUpdate,
        current_user_id: int
    ) -> Optional[MessageResponse]:
        """Update a message (only for the current user)."""
        message = db.query(Message).filter(
            and_(
                Message.id == message_id,
                Message.user_id == current_user_id,
                Message.status != MessageStatus.DELETED
            )
        ).first()
        
        if not message:
            return None
        
        # Update only provided fields
        update_data = message_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(message, field, value)
        
        db.commit()
        db.refresh(message)
        
        return MessageResponse.model_validate(message)

    @staticmethod
    def delete_message(
        db: Session, 
        message_id: int, 
        current_user_id: int
    ) -> bool:
        """Soft delete a message (only for the current user)."""
        message = db.query(Message).filter(
            and_(
                Message.id == message_id,
                Message.user_id == current_user_id,
                Message.status != MessageStatus.DELETED
            )
        ).first()
        
        if not message:
            return False
        
        # Soft delete by updating status
        message.status = MessageStatus.DELETED
        db.commit()
        
        return True

    @staticmethod
    def mark_messages_as_read(
        db: Session,
        conversation_id: int,
        current_user_id: int
    ) -> bool:
        """Mark all AI messages in a conversation as read."""
        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            return False
        
        # Update all unread AI messages to read
        db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_user_message == False,
                Message.status != MessageStatus.READ,
                Message.status != MessageStatus.DELETED
            )
        ).update({Message.status: MessageStatus.READ})
        
        db.commit()
        return True

    @staticmethod
    def get_default_llm_model(db: Session) -> Optional[LLMModel]:
        """Get the default LLM model for AI responses."""
        return db.query(LLMModel).filter(
            LLMModel.is_available == True
        ).first()

    @staticmethod
    def calculate_cost(
        input_tokens: int, 
        output_tokens: int, 
        llm_model: LLMModel
    ) -> float:
        """Calculate the cost of an AI interaction."""
        input_cost = (input_tokens / 1_000_000) * float(llm_model.cost_per_million_input_tokens)
        output_cost = (output_tokens / 1_000_000) * float(llm_model.cost_per_million_output_tokens)
        return input_cost + output_cost

    @staticmethod
    def generate_conversation_title(db: Session, conversation_id: int) -> Optional[str]:
        """Generate a title for a conversation based on the first few messages."""
        messages = db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.is_user_message == True,
                Message.status != MessageStatus.DELETED
            )
        ).order_by(Message.created_at.asc()).limit(3).all()
        
        if not messages:
            return None
        
        # Simple title generation - use first user message (truncated)
        first_message = messages[0].content
        if len(first_message) > 50:
            return first_message[:47] + "..."
        return first_message

    @staticmethod
    def get_conversation_summary(
        db: Session,
        conversation_id: int,
        current_user_id: int,
        max_length: int = 200
    ) -> Optional[ConversationSummaryResponse]:
        """Get a summary of a conversation."""
        # Verify conversation exists and belongs to user
        conversation = db.query(Conversation).filter(
            and_(
                Conversation.id == conversation_id,
                Conversation.user_id == current_user_id,
                Conversation.status != ConversationStatus.DELETED
            )
        ).first()
        
        if not conversation:
            return None
        
        # Get all messages
        messages = db.query(Message).filter(
            and_(
                Message.conversation_id == conversation_id,
                Message.status != MessageStatus.DELETED
            )
        ).order_by(Message.created_at.asc()).all()
        
        if not messages:
            return ConversationSummaryResponse(
                conversation_id=conversation_id,
                summary="No messages in this conversation.",
                key_topics=[],
                message_count=0,
                date_range={}
            )
        
        # Simple summary generation (in a real app, you'd use AI for this)
        user_messages = [m for m in messages if m.is_user_message]
        ai_messages = [m for m in messages if not m.is_user_message]
        
        summary = f"Conversation with {len(user_messages)} user messages and {len(ai_messages)} AI responses."
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        # Extract key topics (simple keyword extraction)
        all_content = " ".join([m.content for m in user_messages])
        words = all_content.lower().split()
        # Simple frequency analysis for key topics
        word_freq = {}
        for word in words:
            if len(word) > 4:  # Only consider longer words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        key_topics = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[:5]
        
        return ConversationSummaryResponse(
            conversation_id=conversation_id,
            summary=summary,
            key_topics=key_topics,
            message_count=len(messages),
            date_range={
                "start": messages[0].created_at,
                "end": messages[-1].created_at
            }
        ) 