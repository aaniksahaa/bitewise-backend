"""Async User profile service.

This module contains the async business logic for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles using async database operations.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Optional

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class AsyncUserProfileService:
    """Async service class for user profile operations.

    This class provides async methods for managing user profiles, including creating,
    retrieving, updating, and deleting profiles. All operations require a valid
    user ID and appropriate permissions.
    """

    @staticmethod
    async def create_profile(
        db: AsyncSession, user_id: int, profile_data: UserProfileCreate
    ) -> UserProfile:
        """Create a new user profile asynchronously."""
        # Check if profile already exists
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        existing_profile = result.scalar_one_or_none()
        
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
        """Get user profile by user ID asynchronously."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )
        return profile

    @staticmethod
    async def get_profile_optional(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID asynchronously, returning None if not found."""
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_profile(
        db: AsyncSession, user_id: int, profile_data: UserProfileUpdate
    ) -> UserProfile:
        """Update user profile asynchronously."""
        # First check if profile exists
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile fields
        update_data = profile_data.model_dump(exclude_unset=True)
        if update_data:
            # Use SQLAlchemy update statement for better performance
            update_stmt = (
                update(UserProfile)
                .where(UserProfile.user_id == user_id)
                .values(**update_data)
                .returning(UserProfile)
            )
            result = await db.execute(update_stmt)
            await db.commit()
            updated_profile = result.scalar_one()
            return updated_profile
        
        # If no updates, return the existing profile
        return profile

    @staticmethod
    async def delete_profile(db: AsyncSession, user_id: int) -> None:
        """Delete user profile asynchronously."""
        # Check if profile exists first
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Delete the profile
        delete_stmt = delete(UserProfile).where(UserProfile.user_id == user_id)
        await db.execute(delete_stmt)
        await db.commit()

    @staticmethod
    async def profile_exists(db: AsyncSession, user_id: int) -> bool:
        """Check if a user profile exists asynchronously."""
        stmt = select(UserProfile.user_id).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def validate_profile_data(profile_data: UserProfileCreate) -> None:
        """Validate user profile data asynchronously.
        
        This method performs async validation logic for user profile data.
        Currently implements basic validation, can be extended for more complex
        async validation like checking external services.
        """
        # Basic validation - can be extended for async operations
        if profile_data.height_cm and (profile_data.height_cm < 50 or profile_data.height_cm > 300):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Height must be between 50 and 300 cm"
            )
        
        if profile_data.weight_kg and (profile_data.weight_kg < 20 or profile_data.weight_kg > 500):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Weight must be between 20 and 500 kg"
            )
        
        # Additional async validation can be added here
        # For example: checking if location exists, validating image URLs, etc.

    @staticmethod
    async def validate_profile_update_data(profile_data: UserProfileUpdate) -> None:
        """Validate user profile update data asynchronously.
        
        This method performs async validation logic for user profile update data.
        """
        # Basic validation for update data
        if profile_data.height_cm is not None and (profile_data.height_cm < 50 or profile_data.height_cm > 300):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Height must be between 50 and 300 cm"
            )
        
        if profile_data.weight_kg is not None and (profile_data.weight_kg < 20 or profile_data.weight_kg > 500):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Weight must be between 20 and 500 kg"
            )
        
        # Additional async validation can be added here

    @staticmethod
    async def get_profiles_by_location(
        db: AsyncSession, 
        city: Optional[str] = None, 
        country: Optional[str] = None,
        limit: int = 100
    ) -> list[UserProfile]:
        """Get user profiles by location asynchronously.
        
        This method demonstrates additional async functionality that could be useful
        for location-based features.
        """
        stmt = select(UserProfile)
        
        if city:
            stmt = stmt.where(UserProfile.location_city.ilike(f"%{city}%"))
        
        if country:
            stmt = stmt.where(UserProfile.location_country.ilike(f"%{country}%"))
        
        stmt = stmt.limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_profile_image(
        db: AsyncSession, user_id: int, image_url: str
    ) -> UserProfile:
        """Update user profile image URL asynchronously."""
        # Check if profile exists
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile image
        update_stmt = (
            update(UserProfile)
            .where(UserProfile.user_id == user_id)
            .values(profile_image_url=image_url)
            .returning(UserProfile)
        )
        result = await db.execute(update_stmt)
        await db.commit()
        updated_profile = result.scalar_one()
        return updated_profile