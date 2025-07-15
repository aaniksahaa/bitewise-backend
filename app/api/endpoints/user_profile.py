"""User profile API endpoints.

This module contains the API endpoints for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import APIRouter, Depends, status, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import get_db
from app.models.user import User
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse, UserProfileUpdate, UserProfileListResponse, UserWithProfileListResponse
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


@router.get("/message-count")
async def get_message_count(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get the message count for the current user."""
    count = UserProfileService.get_message_count(db=db, user_id=current_user.id)
    return count


@router.get("/delete-messages")
async def delete_messages(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Delete all messages for the current user."""
    count = UserProfileService.delete_messages(db=db, user_id=current_user.id)
    return count


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


# Admin endpoints for managing all user profiles
@router.get("/all", response_model=UserWithProfileListResponse)
async def get_all_profiles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of profiles per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all user profiles (admin only)."""
    # Note: Add admin check here when admin roles are implemented
    combined_users, total_count = UserProfileService.get_all_users_with_profiles(
        db=db, page=page, page_size=page_size
    )
    
    total_pages = (total_count + page_size - 1) // page_size
    
    return UserWithProfileListResponse(
        users=combined_users,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/filter", response_model=UserWithProfileListResponse)
async def filter_profiles(
    # Search filters
    search: Optional[str] = Query(None, description="Search in email, username, full_name, first_name, last_name, bio"),
    first_name: Optional[str] = Query(None, description="Filter by first name"),
    last_name: Optional[str] = Query(None, description="Filter by last name"),
    
    # User account filters
    is_active: Optional[bool] = Query(None, description="Filter by account status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    is_superuser: Optional[bool] = Query(None, description="Filter by admin status"),
    oauth_provider: Optional[str] = Query(None, description="Filter by OAuth provider"),
    
    # Demographic filters
    gender: Optional[str] = Query(None, description="Filter by gender"),
    min_age: Optional[int] = Query(None, ge=0, le=150, description="Minimum age"),
    max_age: Optional[int] = Query(None, ge=0, le=150, description="Maximum age"),
    
    # Location filters
    location_city: Optional[str] = Query(None, description="Filter by city"),
    location_country: Optional[str] = Query(None, description="Filter by country"),
    
    # Physical attributes
    min_height: Optional[float] = Query(None, ge=0, description="Minimum height in cm"),
    max_height: Optional[float] = Query(None, ge=0, description="Maximum height in cm"),
    min_weight: Optional[float] = Query(None, ge=0, description="Minimum weight in kg"),
    max_weight: Optional[float] = Query(None, ge=0, description="Maximum weight in kg"),
    
    # Health and preferences
    dietary_restrictions: Optional[str] = Query(None, description="Filter by dietary restrictions"),
    allergies: Optional[str] = Query(None, description="Filter by allergies"),
    medical_conditions: Optional[str] = Query(None, description="Filter by medical conditions"),
    fitness_goals: Optional[str] = Query(None, description="Filter by fitness goals"),
    taste_preferences: Optional[str] = Query(None, description="Filter by taste preferences"),
    cuisine_interests: Optional[str] = Query(None, description="Filter by cuisine interests"),
    cooking_skill_level: Optional[str] = Query(None, description="Filter by cooking skill level"),
    
    # Date filters
    min_created_at: Optional[str] = Query(None, description="Created after date (ISO format)"),
    max_created_at: Optional[str] = Query(None, description="Created before date (ISO format)"),
    min_last_login: Optional[str] = Query(None, description="Last login after date (ISO format)"),
    max_last_login: Optional[str] = Query(None, description="Last login before date (ISO format)"),
    created_after: Optional[str] = Query(None, description="Created after date (YYYY-MM-DD)"),
    created_before: Optional[str] = Query(None, description="Created before date (YYYY-MM-DD)"),
    
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Number of profiles per page"),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    
    # Note: Add admin check here when admin roles are implemented
    
    filters = {
        "search": search,
        "first_name": first_name,
        "last_name": last_name,
        "is_active": is_active,
        "is_verified": is_verified,
        "is_superuser": is_superuser,
        "oauth_provider": oauth_provider,
        "gender": gender,
        "min_age": min_age,
        "max_age": max_age,
        "location_city": location_city,
        "location_country": location_country,
        "min_height": min_height,
        "max_height": max_height,
        "min_weight": min_weight,
        "max_weight": max_weight,
        "dietary_restrictions": dietary_restrictions,
        "allergies": allergies,
        "medical_conditions": medical_conditions,
        "fitness_goals": fitness_goals,
        "taste_preferences": taste_preferences,
        "cuisine_interests": cuisine_interests,
        "cooking_skill_level": cooking_skill_level,
        "min_created_at": min_created_at,
        "max_created_at": max_created_at,
        "min_last_login": min_last_login,
        "max_last_login": max_last_login,
        "created_after": created_after,
        "created_before": created_before,
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    combined_users, total_count = UserProfileService.filter_users_with_profiles(
        db=db, filters=filters, page=page, page_size=page_size
    )
    
    total_pages = (total_count + page_size - 1) // page_size
    
    return UserWithProfileListResponse(
        users=combined_users,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{user_id}")
async def get_profile_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific user's profile by ID (admin only)."""
    # Note: Add admin check here when admin roles are implemented
    return UserProfileService.get_user_with_profile_by_id(db=db, user_id=user_id)


@router.put("/{user_id}")
async def update_profile_by_id(
    user_id: int,
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a specific user's profile by ID (admin only)."""
    # Note: Add admin check here when admin roles are implemented
    return UserProfileService.update_user_with_profile(
        db=db, user_id=user_id, profile_data=profile_data.model_dump(exclude_unset=True)
    )


@router.delete("/{user_id}")
async def delete_profile_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a specific user and their profile by ID (admin only)."""
    # Note: Add admin check here when admin roles are implemented
    UserProfileService.delete_user_with_profile(db=db, user_id=user_id)
    return {"detail": "User and profile deleted successfully"}
