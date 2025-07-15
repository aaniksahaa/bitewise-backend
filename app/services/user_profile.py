"""User profile service.

This module contains the business logic for managing user profiles, including
creation, retrieval, updating, and deletion of user profiles.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from typing import List, Dict, Any, Optional
from datetime import datetime, date

from app.models.user_profile import UserProfile
from app.models.user import User
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

    @staticmethod
    def get_all_profiles(db: Session, page: int = 1, page_size: int = 20) -> tuple[List[UserProfile], int]:
        """Get all user profiles with pagination."""
        # Get total count
        total_count = db.query(UserProfile).count()
        
        # Get paginated results
        offset = (page - 1) * page_size
        profiles = (
            db.query(UserProfile)
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        return profiles, total_count

    @staticmethod
    def filter_profiles(
        db: Session, 
        filters: Dict[str, Any], 
        page: int = 1, 
        page_size: int = 20
    ) -> tuple[List[UserProfile], int]:
        """Filter user profiles based on various criteria."""
        query = db.query(UserProfile)
        
        # Search in first_name, last_name, bio
        if "search" in filters and filters["search"]:
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    UserProfile.first_name.ilike(search_term),
                    UserProfile.last_name.ilike(search_term),
                    UserProfile.bio.ilike(search_term)
                )
            )
        
        # Name filters
        if "first_name" in filters and filters["first_name"]:
            query = query.filter(UserProfile.first_name.ilike(f"%{filters['first_name']}%"))
        
        if "last_name" in filters and filters["last_name"]:
            query = query.filter(UserProfile.last_name.ilike(f"%{filters['last_name']}%"))
        
        # Demographic filters
        if "gender" in filters and filters["gender"]:
            query = query.filter(UserProfile.gender == filters["gender"])
        
        # Age filters (calculated from date_of_birth)
        if "min_age" in filters and filters["min_age"] is not None:
            max_birth_date = date.today().replace(year=date.today().year - filters["min_age"])
            query = query.filter(UserProfile.date_of_birth <= max_birth_date)
        
        if "max_age" in filters and filters["max_age"] is not None:
            min_birth_date = date.today().replace(year=date.today().year - filters["max_age"])
            query = query.filter(UserProfile.date_of_birth >= min_birth_date)
        
        # Location filters
        if "location_city" in filters and filters["location_city"]:
            query = query.filter(UserProfile.location_city.ilike(f"%{filters['location_city']}%"))
        
        if "location_country" in filters and filters["location_country"]:
            query = query.filter(UserProfile.location_country.ilike(f"%{filters['location_country']}%"))
        
        # Physical attribute filters
        if "min_height" in filters and filters["min_height"] is not None:
            query = query.filter(UserProfile.height_cm >= filters["min_height"])
        
        if "max_height" in filters and filters["max_height"] is not None:
            query = query.filter(UserProfile.height_cm <= filters["max_height"])
        
        if "min_weight" in filters and filters["min_weight"] is not None:
            query = query.filter(UserProfile.weight_kg >= filters["min_weight"])
        
        if "max_weight" in filters and filters["max_weight"] is not None:
            query = query.filter(UserProfile.weight_kg <= filters["max_weight"])
        
        # Array field filters (check if any element contains the search term)
        array_fields = [
            "dietary_restrictions", "allergies", "medical_conditions",
            "fitness_goals", "taste_preferences", "cuisine_interests"
        ]
        
        for field in array_fields:
            if field in filters and filters[field]:
                field_attr = getattr(UserProfile, field)
                # Use PostgreSQL array contains operator
                query = query.filter(field_attr.any(filters[field]))
        
        # Cooking skill level filter
        if "cooking_skill_level" in filters and filters["cooking_skill_level"]:
            query = query.filter(UserProfile.cooking_skill_level == filters["cooking_skill_level"])
        
        # Date filters
        if "created_after" in filters and filters["created_after"]:
            try:
                created_after = datetime.strptime(filters["created_after"], "%Y-%m-%d")
                query = query.filter(UserProfile.created_at >= created_after)
            except ValueError:
                pass  # Invalid date format, skip filter
        
        if "created_before" in filters and filters["created_before"]:
            try:
                created_before = datetime.strptime(filters["created_before"], "%Y-%m-%d")
                # Add one day to include the entire day
                created_before = created_before.replace(hour=23, minute=59, second=59)
                query = query.filter(UserProfile.created_at <= created_before)
            except ValueError:
                pass  # Invalid date format, skip filter
        
        # Get total count before applying pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        profiles = query.offset(offset).limit(page_size).all()
        
        return profiles, total_count

    @staticmethod
    def get_all_users_with_profiles(db: Session, page: int = 1, page_size: int = 20) -> tuple[List[Dict], int]:
        """Get all users with their profile data joined."""
        # Get total count
        total_count = db.query(User).filter(User.profile.has()).count()
        
        # Get paginated results with joined profile data
        offset = (page - 1) * page_size
        results = (
            db.query(User, UserProfile)
            .join(UserProfile, User.id == UserProfile.user_id)
            .offset(offset)
            .limit(page_size)
            .all()
        )
        
        # Combine user and profile data
        combined_users = []
        for user, profile in results:
            user_data = {
                # User fields (rename user.id to id for frontend compatibility)
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'is_superuser': user.is_superuser,
                'oauth_provider': user.oauth_provider,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'last_login_at': user.last_login_at,
                # Profile fields
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'gender': profile.gender.value if profile.gender else None,
                'height_cm': str(profile.height_cm) if profile.height_cm else None,
                'weight_kg': str(profile.weight_kg) if profile.weight_kg else None,
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'location_city': profile.location_city,
                'location_country': profile.location_country,
                'dietary_restrictions': profile.dietary_restrictions,
                'allergies': profile.allergies,
                'medical_conditions': profile.medical_conditions,
                'fitness_goals': profile.fitness_goals,
                'taste_preferences': profile.taste_preferences,
                'cuisine_interests': profile.cuisine_interests,
                'cooking_skill_level': profile.cooking_skill_level.value if profile.cooking_skill_level else None,
            }
            combined_users.append(user_data)
        
        return combined_users, total_count

    @staticmethod
    def filter_users_with_profiles(
        db: Session, 
        filters: Dict[str, Any], 
        page: int = 1, 
        page_size: int = 20
    ) -> tuple[List[Dict], int]:
        """Filter users with profile data based on various criteria."""
        query = db.query(User, UserProfile).join(UserProfile, User.id == UserProfile.user_id)
        
        # Search in user fields and profile fields
        if "search" in filters and filters["search"]:
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.username.ilike(search_term),
                    User.full_name.ilike(search_term),
                    UserProfile.first_name.ilike(search_term),
                    UserProfile.last_name.ilike(search_term),
                    UserProfile.bio.ilike(search_term)
                )
            )
        
        # User account filters
        if "is_active" in filters and filters["is_active"] is not None:
            query = query.filter(User.is_active == filters["is_active"])
        
        if "is_verified" in filters and filters["is_verified"] is not None:
            query = query.filter(User.is_verified == filters["is_verified"])
        
        if "is_superuser" in filters and filters["is_superuser"] is not None:
            query = query.filter(User.is_superuser == filters["is_superuser"])
        
        if "oauth_provider" in filters and filters["oauth_provider"]:
            query = query.filter(User.oauth_provider == filters["oauth_provider"])
        
        # User date filters
        if "min_created_at" in filters and filters["min_created_at"]:
            try:
                min_created = datetime.fromisoformat(filters["min_created_at"].replace('Z', '+00:00'))
                query = query.filter(User.created_at >= min_created)
            except ValueError:
                pass
        
        if "max_created_at" in filters and filters["max_created_at"]:
            try:
                max_created = datetime.fromisoformat(filters["max_created_at"].replace('Z', '+00:00'))
                query = query.filter(User.created_at <= max_created)
            except ValueError:
                pass
        
        if "min_last_login" in filters and filters["min_last_login"]:
            try:
                min_login = datetime.fromisoformat(filters["min_last_login"].replace('Z', '+00:00'))
                query = query.filter(User.last_login_at >= min_login)
            except ValueError:
                pass
        
        if "max_last_login" in filters and filters["max_last_login"]:
            try:
                max_login = datetime.fromisoformat(filters["max_last_login"].replace('Z', '+00:00'))
                query = query.filter(User.last_login_at <= max_login)
            except ValueError:
                pass
        
        # Profile filters (same as existing filter_profiles method)
        if "gender" in filters and filters["gender"]:
            query = query.filter(UserProfile.gender == filters["gender"])
        
        if "location_city" in filters and filters["location_city"]:
            query = query.filter(UserProfile.location_city.ilike(f"%{filters['location_city']}%"))
        
        if "location_country" in filters and filters["location_country"]:
            query = query.filter(UserProfile.location_country.ilike(f"%{filters['location_country']}%"))
        
        if "cooking_skill_level" in filters and filters["cooking_skill_level"]:
            query = query.filter(UserProfile.cooking_skill_level == filters["cooking_skill_level"])
        
        # Physical attribute filters
        if "min_height" in filters and filters["min_height"] is not None:
            query = query.filter(UserProfile.height_cm >= filters["min_height"])
        
        if "max_height" in filters and filters["max_height"] is not None:
            query = query.filter(UserProfile.height_cm <= filters["max_height"])
        
        if "min_weight" in filters and filters["min_weight"] is not None:
            query = query.filter(UserProfile.weight_kg >= filters["min_weight"])
        
        if "max_weight" in filters and filters["max_weight"] is not None:
            query = query.filter(UserProfile.weight_kg <= filters["max_weight"])
        
        # Get total count before applying pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        results = query.offset(offset).limit(page_size).all()
        
        # Combine user and profile data
        combined_users = []
        for user, profile in results:
            user_data = {
                # User fields (rename user.id to id for frontend compatibility)
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'full_name': user.full_name,
                'is_active': user.is_active,
                'is_verified': user.is_verified,
                'is_superuser': user.is_superuser,
                'oauth_provider': user.oauth_provider,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'last_login_at': user.last_login_at,
                # Profile fields
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'gender': profile.gender.value if profile.gender else None,
                'height_cm': str(profile.height_cm) if profile.height_cm else None,
                'weight_kg': str(profile.weight_kg) if profile.weight_kg else None,
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'location_city': profile.location_city,
                'location_country': profile.location_country,
                'dietary_restrictions': profile.dietary_restrictions,
                'allergies': profile.allergies,
                'medical_conditions': profile.medical_conditions,
                'fitness_goals': profile.fitness_goals,
                'taste_preferences': profile.taste_preferences,
                'cuisine_interests': profile.cuisine_interests,
                'cooking_skill_level': profile.cooking_skill_level.value if profile.cooking_skill_level else None,
            }
            combined_users.append(user_data)
        
        return combined_users, total_count

    @staticmethod
    def get_user_with_profile_by_id(db: Session, user_id: int) -> Dict:
        """Get a specific user with profile data by user ID."""
        result = (
            db.query(User, UserProfile)
            .join(UserProfile, User.id == UserProfile.user_id)
            .filter(User.id == user_id)
            .first()
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User or profile not found"
            )
        
        user, profile = result
        
        return {
            # User fields (rename user.id to id for frontend compatibility)
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'is_superuser': user.is_superuser,
            'oauth_provider': user.oauth_provider,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'last_login_at': user.last_login_at,
            # Profile fields
            'first_name': profile.first_name,
            'last_name': profile.last_name,
            'gender': profile.gender.value if profile.gender else None,
            'height_cm': str(profile.height_cm) if profile.height_cm else None,
            'weight_kg': str(profile.weight_kg) if profile.weight_kg else None,
            'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            'location_city': profile.location_city,
            'location_country': profile.location_country,
            'dietary_restrictions': profile.dietary_restrictions,
            'allergies': profile.allergies,
            'medical_conditions': profile.medical_conditions,
            'fitness_goals': profile.fitness_goals,
            'taste_preferences': profile.taste_preferences,
            'cuisine_interests': profile.cuisine_interests,
            'cooking_skill_level': profile.cooking_skill_level.value if profile.cooking_skill_level else None,
        }

    @staticmethod
    def update_user_with_profile(db: Session, user_id: int, profile_data: Dict) -> Dict:
        """Update user profile and return combined user + profile data."""
        # Update the profile
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
            )

        # Update profile fields
        for field, value in profile_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        
        # Return combined user + profile data
        return UserProfileService.get_user_with_profile_by_id(db, user_id)

    @staticmethod 
    def delete_user_with_profile(db: Session, user_id: int) -> None:
        """Delete user and their profile."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # The profile will be automatically deleted due to CASCADE foreign key
        db.delete(user)
        db.commit()
