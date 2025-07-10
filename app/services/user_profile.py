"""User profile service.

This module contains the business logic for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class UserProfileService:
    """Service class for user profile operations.

    This class provides methods for managing user profiles, including creating,
    retrieving, updating, and deleting profiles. All operations require a valid
    user ID and appropriate permissions.
    """

    @staticmethod
    def create_profile(
        db: Session, user_id: int, profile_data: UserProfileCreate
    ) -> UserProfile:
        """Create a new user profile."""
        # Check if profile already exists
        existing_profile = (
            db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        )
        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists for this user",
            )

        # Create new profile
        profile = UserProfile(
            user_id=user_id, **profile_data.model_dump(exclude_unset=True)
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_profile(db: Session, user_id: int) -> UserProfile:
        """Get user profile by user ID."""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        return profile
    
    @staticmethod
    def get_message_count(db: Session, user_id: int) -> int:
        """Get message count by user ID."""
        from app.models.message import Message 

        cnt = db.query(Message).filter(Message.user_id == user_id).count()

        return cnt
    
    @staticmethod
    def delete_messages(db: Session, user_id: int) -> int:
        from app.models.message import Message 

        cnt = db.query(Message).filter(Message.user_id == user_id).delete()
        db.commit()

        return cnt

    @staticmethod
    def update_profile(
        db: Session, user_id: int, profile_data: UserProfileUpdate
    ) -> UserProfile:
        """Update user profile."""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile fields
        for field, value in profile_data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete_profile(db: Session, user_id: int) -> None:
        """Delete user profile."""
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        db.delete(profile)
        db.commit()
