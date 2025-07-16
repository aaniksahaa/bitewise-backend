from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid
import os
from pydantic import BaseModel
import base64

from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message as MessageModel
from app.models.dish import Dish
from app.services.chat import ChatService
from app.services.agent import AgentService
from app.services.supabase_storage import SupabaseStorageService
from app.services.intake import IntakeService
from app.schemas.chat import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
    ChatRequest,
    ChatResponse,
    ConversationSummaryRequest,
    ConversationSummaryResponse,
    ConversationStatus,
    ImageUploadResponse,
    ImageAttachment,
    MessageAttachments,
    MessageType,
    ControlMessage,
    DishSelectionWidget,
    WidgetStatus
)
from app.schemas.intake import IntakeCreateByName
from app.utils.logger import api_logger

router = APIRouter()


class DishConfirmationRequest(BaseModel):
    """Request model for confirming dish selection."""
    widget_id: str
    dish_id: int
    portion_size: float


# Conversation endpoints
@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new conversation."""
    return ChatService.create_conversation(
        db=db,
        conversation_data=conversation_data,
        current_user_id=current_user.id
    )

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    keyword: Optional[str] = Query(..., description="Search by keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[ConversationStatus] = Query(None, description="Filter by conversation status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all conversations for the current user with pagination."""
    return ChatService.get_user_conversations(
        db=db,
        keyword=keyword,
        current_user_id=current_user.id,
        page=page,
        page_size=page_size,
        status=status_filter
    )

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific conversation by ID."""
    conversation = ChatService.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation

@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a conversation."""
    conversation = ChatService.update_conversation(
        db=db,
        conversation_id=conversation_id,
        conversation_update=conversation_update,
        current_user_id=current_user.id
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete (archive) a conversation."""
    success = ChatService.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

# Message Management Endpoints
@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(
    conversation_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get messages for a conversation with pagination."""
    return ChatService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        page=page,
        page_size=page_size
    )

@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    conversation_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new message in a conversation (user message only)."""
    return ChatService.create_message(
        db=db,
        conversation_id=conversation_id,
        message_data=message_data,
        current_user_id=current_user.id,
        is_user_message=True
    )

@router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    message_update: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a message."""
    message = ChatService.update_message(
        db=db,
        message_id=message_id,
        message_update=message_update,
        current_user_id=current_user.id
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return message

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a message."""
    success = ChatService.delete_message(
        db=db,
        message_id=message_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

# AI Chat Interaction Endpoints
@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message and get AI response. Creates a new conversation if none specified."""
    
    # Start request processing with clear banner
    api_logger.newline()
    api_logger.section_start("Chat Request", "REQUEST")
    
    # Log the incoming chat request
    truncated_message = chat_request.message[:100] + "..." if len(chat_request.message) > 100 else chat_request.message
    api_logger.info(f"📨 Incoming message: '{truncated_message}'", "REQUEST",
                   user_id=current_user.id, conversation_id=chat_request.conversation_id,
                   has_attachments=bool(chat_request.attachments))
    
    try:
        # Create conversation if not provided
        conversation_id = chat_request.conversation_id
        if not conversation_id:
            api_logger.separator("┈", 40, "SETUP")
            api_logger.debug("Creating new conversation", "SETUP")
            from app.schemas.chat import ConversationCreate
            conversation = ChatService.create_conversation(
                db=db,
                conversation_data=ConversationCreate(),
                current_user_id=current_user.id
            )
            conversation_id = conversation.id
            api_logger.success(f"New conversation created: {conversation_id}", "SETUP")
        
        # Create user message
        api_logger.separator("┈", 40, "MESSAGE")
        api_logger.debug("Creating user message record", "MESSAGE", conversation_id=conversation_id)
        user_message_data = MessageCreate(
            content=chat_request.message,
            message_type=chat_request.message_type,
            attachments=chat_request.attachments,
            extra_data=chat_request.context
        )
        
        user_message = ChatService.create_message(
            db=db,
            conversation_id=conversation_id,
            message_data=user_message_data,
            current_user_id=current_user.id,
            is_user_message=True
        )
        
        api_logger.success(f"User message created: {user_message.id}", "MESSAGE")
        
        # Generate AI response
        api_logger.separator("┈", 40, "AI")
        api_logger.debug("Calling AgentService.generate_response", "AI")
        ai_response, input_tokens, output_tokens, tool_attachments = AgentService.generate_response(
            user_message=chat_request.message,
            conversation_context=None,  # Could add conversation history here
            attachments=chat_request.attachments,
            db=db,
            current_user_id=current_user.id
        )
        
        api_logger.success("AI response generated", "AI", 
                         response_length=len(ai_response), input_tokens=input_tokens, 
                         output_tokens=output_tokens, has_tool_attachments=bool(tool_attachments))
        
        # Log widget attachments specifically
        if tool_attachments and "widgets" in tool_attachments:
            widgets = tool_attachments["widgets"]
            api_logger.success(f"🎯 Found {len(widgets)} widgets in tool attachments", "AI",
                             widget_count=len(widgets))
            for widget in widgets:
                if isinstance(widget, dict):
                    widget_id = widget.get("widget_id", "unknown")
                    widget_type = widget.get("widget_type", "unknown")
                    dishes_count = len(widget.get("dishes", []))
                    api_logger.info(f"📋 Widget details: {widget_type} ({widget_id}) with {dishes_count} dishes", "AI",
                                   widget_id=widget_id, widget_type=widget_type, dishes_count=dishes_count)
        
        # Get default model for cost calculation
        default_model = AgentService.get_default_model(db)
        
        # Create AI message
        api_logger.separator("┈", 40, "STORAGE")
        api_logger.debug("Creating AI message record", "STORAGE")
        
        # Log what we're about to save
        if tool_attachments:
            api_logger.debug("Tool attachments to save", "STORAGE",
                           attachment_keys=list(tool_attachments.keys()),
                           has_widgets="widgets" in tool_attachments,
                           has_tool_calls="tool_calls" in tool_attachments)
        
        ai_message_data = MessageCreate(
            content=ai_response,
            message_type=chat_request.message_type,
            attachments=tool_attachments,  # Include tool call results in attachments
            extra_data={"generated": True}
        )
        
        ai_message = ChatService.create_message(
            db=db,
            conversation_id=conversation_id,
            message_data=ai_message_data,
            current_user_id=current_user.id,
            is_user_message=False,
            llm_model_id=default_model.id if default_model else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        api_logger.success(f"AI message saved: {ai_message.id}", "STORAGE")
        
        # Calculate cost
        cost_estimate = None
        if default_model:
            cost_estimate = AgentService.calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=default_model
            )
            api_logger.debug(f"Cost calculated: ${cost_estimate:.6f}", "STORAGE", cost=cost_estimate)
        
        # Auto-generate conversation title if it's the first exchange
        conversation = ChatService.get_conversation_by_id(
            db=db,
            conversation_id=conversation_id,
            current_user_id=current_user.id
        )
        
        if conversation and not conversation.title:
            api_logger.debug("Generating conversation title", "SETUP")
            title = ChatService.generate_conversation_title(db, conversation_id)
            if title:
                from app.schemas.chat import ConversationUpdate
                ChatService.update_conversation(
                    db=db,
                    conversation_id=conversation_id,
                    conversation_update=ConversationUpdate(title=title),
                    current_user_id=current_user.id
                )
                api_logger.success(f"Conversation title set: '{title}'", "SETUP")
        
        # Log tool attachments if present for debugging
        if tool_attachments and "tool_calls" in tool_attachments:
            api_logger.separator("┈", 40, "TOOLS")
            for tool_call in tool_attachments["tool_calls"]:
                tool_name = tool_call.get("tool_name", "unknown")
                tool_success = tool_call.get("tool_response", {}).get("success", False)
                api_logger.info(f"🔧 Tool executed: {tool_name} (success: {tool_success})", "TOOLS",
                               tool_name=tool_name, tool_success=tool_success)
                
                # Special logging for intake tool calls
                if tool_name == "log_intake":
                    tool_response = tool_call.get("tool_response", {})
                    if tool_success:
                        intake_id = tool_response.get("intake_id")
                        dish_name = tool_response.get("dish_name", "unknown")
                        api_logger.success(f"✅ Intake logged: '{dish_name}' (ID: {intake_id})", "TOOLS",
                                         intake_id=intake_id, dish_name=dish_name)
                    else:
                        error = tool_response.get("error", "unknown error")
                        api_logger.error(f"❌ Intake logging failed: {error}", "TOOLS", error=error)
        
        response = ChatResponse(
            conversation_id=conversation_id,
            user_message=user_message,
            ai_message=ai_message,
            total_tokens_used=input_tokens + output_tokens,
            cost_estimate=cost_estimate
        )
        
        # Successful completion
        api_logger.section_end("Chat Request", "REQUEST", success=True)
        
        return response
        
    except Exception as e:
        api_logger.error(f"Chat request failed: {str(e)}", "REQUEST",
                       user_id=current_user.id, error=str(e))
        api_logger.section_end("Chat Request", "REQUEST", success=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(e)}"
        )

# Utility Endpoints
@router.post("/conversations/{conversation_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_messages_as_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark all AI messages in a conversation as read."""
    success = ChatService.mark_messages_as_read(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

@router.get("/conversations/{conversation_id}/summary", response_model=ConversationSummaryResponse)
async def get_conversation_summary(
    conversation_id: int,
    summary_request: ConversationSummaryRequest = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a summary of a conversation."""
    summary = ChatService.get_conversation_summary(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id,
        max_length=summary_request.max_length
    )
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return summary

# Image Upload Endpoints
@router.post("/upload-image", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    image: UploadFile = File(..., description="Image file to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload an image to Supabase Storage."""
    try:
        # Upload image to Supabase
        download_url, metadata = SupabaseStorageService.upload_image(
            file=image,
            user_id=current_user.id,
            folder="chat_images"
        )
        
        return ImageUploadResponse(
            success=True,
            image_url=download_url,
            filename=image.filename,
            size=metadata.get("file_size", 0),
            metadata=metadata
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )

@router.post("/chat-with-images", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message_with_images(
    message: str = Form(..., description="Chat message"),
    conversation_id: Optional[int] = Form(None, description="Existing conversation ID"),
    images: List[UploadFile] = File(default=[], description="Images to upload with the message"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a chat message with image uploads."""
    # Handle the case where FastAPI passes invalid data for empty file uploads
    # This can happen when the client sends an empty form field
    valid_images = []
    
    if images:
        for image in images:
            # First check if it's actually an UploadFile object (not a string or other type)
            # This prevents the "Expected UploadFile, received: <class 'str'>" error
            if not hasattr(image, '__class__') or 'UploadFile' not in str(type(image)):
                continue
                
            # Check if it's a proper UploadFile object with valid content
            if (hasattr(image, 'filename') and 
                hasattr(image, 'file') and 
                hasattr(image, 'content_type') and
                image.filename and 
                image.filename.strip() != "" and
                image.filename != ""):
                valid_images.append(image)
    
    images = valid_images
    
    # Process images: Upload to Supabase AND prepare base64 for agent
    uploaded_images = []
    agent_image_data = []
    
    for image in images:
        try:
            # Read the image file content for base64 encoding
            image.file.seek(0)  # Reset file pointer
            image_content = image.file.read()
            
            # Encode to base64 for agent processing
            base64_encoded = base64.b64encode(image_content).decode('utf-8')
            
            # Reset file pointer for upload
            image.file.seek(0)
            
            # Upload to Supabase Storage for persistence
            download_url, metadata = SupabaseStorageService.upload_image(
                file=image,
                user_id=current_user.id,
                folder="chat_images"
            )
            
            # Create image attachment for database storage
            image_attachment = ImageAttachment(
                url=download_url,
                filename=image.filename,
                size=metadata.get("file_size", 0),
                content_type=image.content_type,
                storage_path=metadata.get("storage_path", ""),
                metadata=metadata
            )
            uploaded_images.append(image_attachment)
            
            # Prepare data for agent with base64
            agent_image_data.append({
                "url": download_url,  # Keep URL for backward compatibility
                "filename": image.filename,
                "size": metadata.get("file_size", 0),
                "content_type": image.content_type,
                "storage_path": metadata.get("storage_path", ""),
                "base64_data": base64_encoded,  # Add base64 data for agent
                "metadata": metadata
            })
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process image {image.filename}: {str(e)}"
            )
    
    # Create conversation if not provided
    if not conversation_id:
        from app.schemas.chat import ConversationCreate
        conversation = ChatService.create_conversation(
            db=db,
            conversation_data=ConversationCreate(),
            current_user_id=current_user.id
        )
        conversation_id = conversation.id
    
    # Prepare attachments for database storage (without base64 to save space)
    attachments_data = MessageAttachments(images=uploaded_images) if uploaded_images else None
    
    # Create user message
    user_message_data = MessageCreate(
        content=message,
        message_type=MessageType.IMAGE if uploaded_images else MessageType.TEXT,
        attachments=attachments_data.model_dump() if attachments_data else None,
        extra_data={"has_images": len(uploaded_images) > 0, "image_count": len(uploaded_images)}
    )
    
    user_message = ChatService.create_message(
        db=db,
        conversation_id=conversation_id,
        message_data=user_message_data,
        current_user_id=current_user.id,
        is_user_message=True
    )
    
    # Prepare attachments for agent processing (with base64 data)
    agent_attachments = None
    if agent_image_data:
        agent_attachments = {
            "images": agent_image_data
        }
    
    # Generate AI response
    ai_response, input_tokens, output_tokens, tool_attachments = AgentService.generate_response(
        user_message=message,
        conversation_context=None,
        attachments=agent_attachments,
        db=db,
        current_user_id=current_user.id
    )
    
    # Get default model for cost calculation
    default_model = AgentService.get_default_model(db)
    
    # Create AI message
    ai_message_data = MessageCreate(
        content=ai_response,
        message_type=MessageType.TEXT,
        attachments=tool_attachments,
        extra_data={"generated": True, "processed_images": len(uploaded_images) > 0}
    )
    
    ai_message = ChatService.create_message(
        db=db,
        conversation_id=conversation_id,
        message_data=ai_message_data,
        current_user_id=current_user.id,
        is_user_message=False,
        llm_model_id=default_model.id if default_model else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )
    
    # Calculate cost
    cost_estimate = None
    if default_model:
        cost_estimate = AgentService.calculate_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=default_model
        )
    
    # Auto-generate conversation title if it's the first exchange
    conversation = ChatService.get_conversation_by_id(
        db=db,
        conversation_id=conversation_id,
        current_user_id=current_user.id
    )
    
    if conversation and not conversation.title:
        title = ChatService.generate_conversation_title(db, conversation_id)
        if title:
            from app.schemas.chat import ConversationUpdate
            ChatService.update_conversation(
                db=db,
                conversation_id=conversation_id,
                conversation_update=ConversationUpdate(title=title),
                current_user_id=current_user.id
            )
    
    return ChatResponse(
        conversation_id=conversation_id,
        user_message=user_message,
        ai_message=ai_message,
        total_tokens_used=input_tokens + output_tokens,
        cost_estimate=cost_estimate
    ) 

@router.post("/confirm-dish-selection", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def confirm_dish_selection(
    request: DishConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Handle dish selection confirmation and log intake directly."""
    
    api_logger.newline()
    api_logger.section_start("Dish Selection Confirmation", "CONFIRM")
    
    api_logger.info(f"🎯 Processing dish selection confirmation", "CONFIRM",
                   user_id=current_user.id, widget_id=request.widget_id, 
                   dish_id=request.dish_id, portion_size=request.portion_size)
    
    try:
        # Get the dish
        dish = db.query(Dish).filter(Dish.id == request.dish_id).first()
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dish with ID {request.dish_id} not found"
            )
        
        # Find the conversation from the widget
        # We'll get the most recent conversation for this user
        conversation = db.query(Conversation).filter(
            Conversation.user_id == current_user.id
        ).order_by(Conversation.updated_at.desc()).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No conversation found"
            )
        
        # Find the original message with the widget that needs to be updated
        # Query messages directly since there's no relationship defined
        from app.models.message import Message
        conversation_messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.desc()).all()
        
        original_message = None
        for message in conversation_messages:
            if (message.attachments and 
                isinstance(message.attachments, dict) and 
                "widgets" in message.attachments):
                
                for widget in message.attachments["widgets"]:
                    if widget.get("widget_id") == request.widget_id:
                        original_message = message
                        break
                if original_message:
                    break
        
        # Update the widget status to "resolved" in the original message
        if original_message:
            api_logger.debug("Updating original widget status to resolved", "CONFIRM",
                           message_id=original_message.id, widget_id=request.widget_id)
            
            # Parse the current attachments
            current_attachments = original_message.attachments
            if current_attachments and "widgets" in current_attachments:
                # Update the specific widget
                for widget in current_attachments["widgets"]:
                    if widget.get("widget_id") == request.widget_id:
                        widget["status"] = "resolved"
                        widget["selected_dish_id"] = request.dish_id
                        widget["selected_portion"] = request.portion_size
                        widget["resolved_at"] = datetime.now().isoformat()
                        api_logger.success("Widget status updated to resolved", "CONFIRM",
                                         widget_id=request.widget_id, selected_dish_id=request.dish_id)
                        break
                
                # Update the message with the new attachments
                from app.services.chat import convert_decimals_to_floats
                updated_attachments = convert_decimals_to_floats(current_attachments)
                
                original_message.attachments = updated_attachments
                db.commit()
                api_logger.success("Original message updated with resolved widget", "CONFIRM",
                                 message_id=original_message.id)
        
        # Create user confirmation message
        user_message_content = f"I confirm eating {request.portion_size}x {dish.name}"
        
        user_message_data = MessageCreate(
            content=user_message_content,
            message_type=MessageType.TEXT,
            extra_data={"is_control_message": True, "widget_id": request.widget_id}
        )
        
        user_message = ChatService.create_message(
            db=db,
            conversation_id=conversation.id,
            message_data=user_message_data,
            current_user_id=current_user.id,
            is_user_message=True
        )
        
        api_logger.success(f"User confirmation message created: {user_message.id}", "CONFIRM")
        
        # Log the intake directly 
        api_logger.debug("Logging intake", "CONFIRM")
        
        intake_data = IntakeCreateByName(
            dish_name=dish.name,
            portion_size=Decimal(str(request.portion_size)),
            intake_time=datetime.now()
        )
        
        intake_result = IntakeService.create_intake_by_name(
            db=db,
            intake_data=intake_data,
            current_user_id=current_user.id
        )
        
        api_logger.success(f"✅ Intake logged successfully", "CONFIRM",
                         intake_id=intake_result.id, dish_name=intake_result.dish.name,
                         portion_size=float(intake_result.portion_size))
        
        # Generate AI confirmation response
        ai_response_content = f"Perfect! I've successfully logged your intake of {request.portion_size}x {dish.name}. "
        
        # Add nutritional info if available
        if dish.calories:
            total_calories = float(dish.calories) * request.portion_size
            ai_response_content += f"This adds approximately {total_calories:.0f} calories to your daily intake. "
        
        ai_response_content += "Keep up the great work tracking your nutrition! 🎉"
        
        # Create AI message
        ai_message_data = MessageCreate(
            content=ai_response_content,
            message_type=MessageType.TEXT,
            attachments={
                "intake_logged": {
                    "intake_id": intake_result.id,
                    "dish_id": dish.id,
                    "dish_name": dish.name,
                    "portion_size": request.portion_size,
                    "calories_logged": float(dish.calories * Decimal(str(request.portion_size))) if dish.calories else None,
                    "logged_at": intake_result.intake_time.isoformat()
                }
            },
            extra_data={"generated": True, "intake_confirmation": True}
        )
        
        ai_message = ChatService.create_message(
            db=db,
            conversation_id=conversation.id,
            message_data=ai_message_data,
            current_user_id=current_user.id,
            is_user_message=False,
            input_tokens=10,
            output_tokens=len(ai_response_content.split())
        )
        
        api_logger.success(f"AI confirmation message created: {ai_message.id}", "CONFIRM")
        
        response = ChatResponse(
            conversation_id=conversation.id,
            user_message=user_message,
            ai_message=ai_message,
            total_tokens_used=10 + len(ai_response_content.split()),
            cost_estimate=0.001
        )
        
        api_logger.section_end("Dish Selection Confirmation", "CONFIRM", success=True)
        
        return response
        
    except HTTPException as e:
        api_logger.error(f"Dish selection confirmation failed: {e.detail}", "CONFIRM",
                       user_id=current_user.id, error=str(e.detail))
        api_logger.section_end("Dish Selection Confirmation", "CONFIRM", success=False)
        raise e
    except Exception as e:
        api_logger.error(f"Dish selection confirmation failed: {str(e)}", "CONFIRM",
                       user_id=current_user.id, error=str(e))
        api_logger.section_end("Dish Selection Confirmation", "CONFIRM", success=False)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm dish selection: {str(e)}"
        ) 