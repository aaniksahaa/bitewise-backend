"""User profile schemas.

This module contains Pydantic models for user profile data validation and serialization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.user_profile import CookingSkillLevelType, GenderType


class UserProfileBase(BaseModel):
    """Base schema for user profile operations.

    Contains all the common fields that can be used for both creating and updating
    user profiles. All fields are optional to allow partial updates.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: GenderType
    height_cm: Decimal
    weight_kg: Decimal
    date_of_birth: date
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    fitness_goals: Optional[List[str]] = None
    taste_preferences: Optional[List[str]] = None
    cuisine_interests: Optional[List[str]] = None
    cooking_skill_level: Optional[CookingSkillLevelType] = None
    email_notifications_enabled: Optional[bool] = True
    push_notifications_enabled: Optional[bool] = True


class UserProfileCreate(UserProfileBase):
    """Schema for creating a new user profile."""

    pass


class UserProfileUpdate(UserProfileBase):
    """Schema for updating an existing user profile."""

    pass


class UserProfileResponse(UserProfileBase):
    """Schema for user profile response."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    created_at: datetime
    updated_at: datetime
