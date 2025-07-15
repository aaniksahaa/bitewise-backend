"""User profile service.

This module contains the business logic for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class UserProfileService:
    """Service class for user profile operations.

    This class provides methods for managing user profiles, including creating,
    retrieving, updating, and deleting profiles. All operations require a valid
    user ID and appropriate permissions.
    """

    @staticmethod
    async def create_profile(
        db: AsyncSession, user_id: int, profile_data: UserProfileCreate
    ) -> UserProfile:
        """Create a new user profile."""
        # Check if profile already exists
        # existing_profile = (
        #     db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        # )
        # modified for asyncio
        existing_profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
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
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def get_profile(db: AsyncSession, user_id: int) -> UserProfile:
        """Get user profile by user ID."""
        # profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        # modified for asyncio
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        return profile

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: int, profile_data: UserProfileUpdate
    ) -> UserProfile:
        """Update user profile."""
        # profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        # modified for asyncio
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile fields
        for field, value in profile_data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def delete_profile(db: AsyncSession, user_id: int) -> None:
        """Delete user profile."""
        # profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        # modified for asyncio
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        await db.delete(profile)
        await db.commit()
