"""User profile API endpoints.

This module contains the API endpoints for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user_profile import UserProfileCreate, UserProfileResponse, UserProfileUpdate
from app.services.auth import get_current_active_user
from app.services.user_profile import UserProfileService

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


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Delete the current user's profile."""
    UserProfileService.delete_profile(db=db, user_id=current_user.id)
