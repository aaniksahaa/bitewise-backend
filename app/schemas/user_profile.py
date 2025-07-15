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
    """Schema for creating a new user profile.

    Inherits from UserProfileBase but requires certain fields that are mandatory
    for profile creation.
    """

    pass


class UserProfileUpdate(UserProfileBase):
    """Schema for updating an existing user profile.

    All fields are optional to support partial updates. Inherits from UserProfileBase.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[GenderType] = None
    height_cm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    date_of_birth: Optional[date] = None
    cooking_skill_level: Optional[CookingSkillLevelType] = None


class UserProfileResponse(UserProfileBase):
    """Schema for user profile API responses.

    Includes all profile fields plus system-generated fields like timestamps and user_id.
    """

    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileListResponse(BaseModel):
    """Schema for paginated user profile list responses."""
    
    users: List[UserProfileResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


class UserWithProfileResponse(BaseModel):
    """Schema for combined user account + profile data for admin management."""
    # User account fields
    id: int  # This is the user_id, but renamed to 'id' for frontend compatibility
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    oauth_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    # Profile fields
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    height_cm: Optional[str] = None
    weight_kg: Optional[str] = None
    date_of_birth: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    dietary_restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    fitness_goals: Optional[List[str]] = None
    taste_preferences: Optional[List[str]] = None
    cuisine_interests: Optional[List[str]] = None
    cooking_skill_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithProfileListResponse(BaseModel):
    """Schema for paginated combined user + profile list responses."""
    
    users: List[UserWithProfileResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
