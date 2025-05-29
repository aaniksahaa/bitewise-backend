from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import base64

from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.services.chat import ChatService
from app.services.agent import AgentService
from app.services.supabase_storage import SupabaseStorageService
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
    MessageType
)
from app.models.user import User

router = APIRouter()

# Conversation Management Endpoints
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
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[ConversationStatus] = Query(None, description="Filter by conversation status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all conversations for the current user with pagination."""
    return ChatService.get_user_conversations(
        db=db,
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
    # Create conversation if not provided
    conversation_id = chat_request.conversation_id
    if not conversation_id:
        from app.schemas.chat import ConversationCreate
        conversation = ChatService.create_conversation(
            db=db,
            conversation_data=ConversationCreate(),
            current_user_id=current_user.id
        )
        conversation_id = conversation.id
    
    # Create user message
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
    
    # Generate AI response
    ai_response, input_tokens, output_tokens, tool_attachments = AgentService.generate_response(
        user_message=chat_request.message,
        conversation_context=None,  # Could add conversation history here
        attachments=chat_request.attachments,
        db=db,
        current_user_id=current_user.id
    )
    
    # Get default model for cost calculation
    default_model = AgentService.get_default_model(db)
    
    # Create AI message
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