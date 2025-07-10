"""User profile API endpoints.

This module contains the API endpoints for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse, UserProfileUpdate
from app.services.auth import get_current_active_user
from app.services.user_profile import UserProfileService
from app.services.supabase_storage import SupabaseStorageService

router = APIRouter()


@router.post(
    "/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_profile(
    profile_data: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new user profile."""
    return UserProfileService.create_profile(
        db=db, user_id=current_user.id, profile_data=profile_data
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get the current user's profile."""
    return UserProfileService.get_profile(db=db, user_id=current_user.id)

@router.get("/message-count", response_model=int)
async def get_message_count(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get the current user's message count."""
    return UserProfileService.get_message_count(db=db, user_id=current_user.id)

@router.get("/delete-messages", response_model=int)
async def delete_messages(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get the current user's message count."""
    return UserProfileService.delete_messages(db=db, user_id=current_user.id)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update the current user's profile."""
    return UserProfileService.update_profile(
        db=db, user_id=current_user.id, profile_data=profile_data
    )


@router.post("/me/profile-picture")
async def upload_profile_picture(
    image: UploadFile = File(..., description="Profile picture to upload"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a profile picture and update the user's profile."""
    try:
        # Upload image to Supabase Storage
        download_url, metadata = SupabaseStorageService.upload_image(
            file=image,
            user_id=current_user.id,
            folder="profile_pictures"
        )
        
        # Update the profile with the new image URL
        profile_update = UserProfileUpdate(profile_image_url=download_url)
        updated_profile = UserProfileService.update_profile(
            db=db, user_id=current_user.id, profile_data=profile_update
        )
        
        return {
            "success": True,
            "profile_image_url": download_url,
            "filename": image.filename,
            "size": metadata.get("file_size", 0),
            "metadata": metadata,
            "message": "Profile picture updated successfully"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload profile picture: {str(e)}"
        )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Delete the current user's profile."""
    UserProfileService.delete_profile(db=db, user_id=current_user.id)
