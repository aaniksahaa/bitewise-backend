"""User profile API endpoints.

This module contains the API endpoints for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles using async operations.
"""

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import get_async_db
from app.models.user import User
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse, UserProfileUpdate
from app.services.async_auth import get_current_active_user_async, get_current_user_validated_token
from app.services.async_user_profile import AsyncUserProfileService
from app.services.supabase_storage import SupabaseStorageService

router = APIRouter()


@router.post(
    "/", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED
)
async def create_profile(
    profile_data: UserProfileCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async),
):
    """Create a new user profile."""
    # Validate profile data before creation
    await AsyncUserProfileService.validate_profile_data(profile_data)
    
    return await AsyncUserProfileService.create_profile(
        db=db, user_id=current_user.id, profile_data=profile_data
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user_validated_token),
    db: AsyncSession = Depends(get_async_db)
):
    """Get the current user's profile."""
    return await AsyncUserProfileService.get_profile(db=db, user_id=current_user.id)


@router.put("/me", response_model=UserProfileResponse)
async def update_my_profile(
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async),
):
    """Update the current user's profile."""
    # Validate profile update data before updating
    await AsyncUserProfileService.validate_profile_update_data(profile_data)
    
    return await AsyncUserProfileService.update_profile(
        db=db, user_id=current_user.id, profile_data=profile_data
    )


@router.post("/me/profile-picture")
async def upload_profile_picture(
    image: UploadFile = File(..., description="Profile picture to upload"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Upload a profile picture and update the user's profile."""
    try:
        # Upload image to Supabase Storage
        download_url, metadata = SupabaseStorageService.upload_image(
            file=image,
            user_id=current_user.id,
            folder="profile_pictures"
        )
        
        # Update the profile with the new image URL using async service
        updated_profile = await AsyncUserProfileService.update_profile_image(
            db=db, user_id=current_user.id, image_url=download_url
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
    db: AsyncSession = Depends(get_async_db), 
    current_user: User = Depends(get_current_active_user_async)
):
    """Delete the current user's profile."""
    await AsyncUserProfileService.delete_profile(db=db, user_id=current_user.id)
