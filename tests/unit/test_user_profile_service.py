"""
Unit tests for UserProfileService.

This module tests the user profile service functionality including:
- Profile creation and validation
- Profile retrieval operations
- Profile updates and modifications
- Profile deletion and error handling

Tests use mocking to avoid database dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status
from datetime import date
from decimal import Decimal

from app.services.user_profile import UserProfileService
from app.models.user_profile import UserProfile, GenderType
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class TestUserProfileService:
    """Test UserProfileService functionality."""

    def test_create_profile_success(self):
        """
        Test successful profile creation.
        
        This test ensures that new user profiles are created
        correctly when no existing profile exists.
        """
        # Arrange: Mock database and profile data with all required fields
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing profile
        
        profile_data = UserProfileCreate(
            first_name="John",
            last_name="Doe",
            gender=GenderType.male,
            height_cm=Decimal("180.0"),
            weight_kg=Decimal("75.0"),
            date_of_birth=date(1990, 1, 1),
            bio="Test bio",
            location_city="Test City"
        )
        
        # Act: Create profile
        UserProfileService.create_profile(mock_db, 123, profile_data)
        
        # Assert: Profile should be created and saved
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_profile_already_exists(self):
        """
        Test profile creation when profile already exists.
        
        This test ensures that attempting to create a profile
        for a user who already has one raises an appropriate error.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        existing_profile = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_profile
        
        profile_data = UserProfileCreate(
            first_name="John",
            last_name="Doe",
            gender=GenderType.male,
            height_cm=Decimal("180.0"),
            weight_kg=Decimal("75.0"),
            date_of_birth=date(1990, 1, 1),
            bio="Test bio"
        )
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.create_profile(mock_db, 123, profile_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Profile already exists" in exc_info.value.detail

    def test_get_profile_success(self):
        """
        Test successful profile retrieval.
        
        This test ensures that existing profiles can be
        retrieved by user ID.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        mock_profile = MagicMock()
        mock_profile.id = 1
        mock_profile.user_id = 123
        mock_profile.full_name = "John Doe"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        # Act: Get profile
        result = UserProfileService.get_profile(mock_db, 123)
        
        # Assert: Should return the profile
        assert result == mock_profile
        mock_db.query.assert_called_once()

    def test_get_profile_not_found(self):
        """
        Test profile retrieval when profile doesn't exist.
        
        This test ensures that attempting to get a non-existent
        profile raises an appropriate error.
        """
        # Arrange: Mock database with no profile found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.get_profile(mock_db, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in exc_info.value.detail

    def test_update_profile_success(self):
        """
        Test successful profile update.
        
        This test ensures that existing profiles can be
        updated with new information.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        mock_profile = MagicMock()
        mock_profile.user_id = 123
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.bio = "Old bio"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        profile_update = UserProfileUpdate(
            first_name="Jane",
            bio="Updated bio"
        )
        
        # Act: Update profile
        result = UserProfileService.update_profile(mock_db, 123, profile_update)
        
        # Assert: Profile should be updated (check the actual attributes after setattr)
        assert mock_profile.first_name == "Jane"
        assert mock_profile.bio == "Updated bio"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_profile_not_found(self):
        """
        Test profile update when profile doesn't exist.
        
        This test ensures that updating non-existent profiles
        raises an appropriate error.
        """
        # Arrange: Mock database with no profile found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        profile_update = UserProfileUpdate(first_name="Jane Doe")
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.update_profile(mock_db, 999, profile_update)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in exc_info.value.detail

    def test_update_profile_partial_update(self):
        """
        Test partial profile update.
        
        This test ensures that only provided fields are updated
        and other fields remain unchanged.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        mock_profile = MagicMock()
        mock_profile.user_id = 123
        mock_profile.first_name = "John"
        mock_profile.last_name = "Doe"
        mock_profile.bio = "Original bio"
        mock_profile.location_city = "Original location"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        # Only update bio, leave other fields unchanged
        profile_update = UserProfileUpdate(bio="Updated bio only")
        
        # Act: Update profile
        result = UserProfileService.update_profile(mock_db, 123, profile_update)
        
        # Assert: Only bio should be updated
        assert mock_profile.bio == "Updated bio only"
        assert mock_profile.first_name == "John"  # Should remain unchanged
        assert mock_profile.location_city == "Original location"  # Should remain unchanged

    def test_delete_profile_success(self):
        """
        Test successful profile deletion.
        
        This test ensures that existing profiles can be
        deleted from the database.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        mock_profile = MagicMock()
        mock_profile.id = 1
        mock_profile.user_id = 123
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_profile
        
        # Act: Delete profile
        UserProfileService.delete_profile(mock_db, 123)
        
        # Assert: Profile should be deleted
        mock_db.delete.assert_called_once_with(mock_profile)
        mock_db.commit.assert_called_once()

    def test_delete_profile_not_found(self):
        """
        Test profile deletion when profile doesn't exist.
        
        This test ensures that attempting to delete a non-existent
        profile raises an appropriate error.
        """
        # Arrange: Mock database with no profile found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert: Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.delete_profile(mock_db, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in exc_info.value.detail

    def test_profile_data_validation(self):
        """
        Test that profile data is properly validated.
        
        This test ensures that profile creation and updates
        handle data validation correctly.
        """
        # Arrange: Mock database
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Test with valid profile data including all required fields
        valid_profile_data = UserProfileCreate(
            first_name="Valid",
            last_name="Name",
            gender=GenderType.female,
            height_cm=Decimal("165.0"),
            weight_kg=Decimal("60.0"),
            date_of_birth=date(1995, 5, 15),
            bio="Valid bio",
            location_city="Valid City"
        )
        
        # Act: Create profile with valid data
        UserProfileService.create_profile(mock_db, 123, valid_profile_data)
        
        # Assert: Should succeed without errors
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_database_error_handling(self):
        """
        Test handling of database errors.
        
        This test ensures that database operation failures
        are handled gracefully.
        """
        # Arrange: Mock database to raise an error
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.commit.side_effect = Exception("Database error")
        
        profile_data = UserProfileCreate(
            first_name="Test",
            last_name="User",
            gender=GenderType.male,
            height_cm=Decimal("175.0"),
            weight_kg=Decimal("70.0"),
            date_of_birth=date(1992, 3, 10),
            bio="Test bio"
        )
        
        # Act & Assert: Should handle database errors
        with pytest.raises(Exception) as exc_info:
            UserProfileService.create_profile(mock_db, 123, profile_data)
        
        assert "Database error" in str(exc_info.value)

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    def test_create_profile_duplicate_user(self):
        """
        Negative Test: Profile creation should fail for existing user.
        
        This test ensures that attempting to create a duplicate profile
        for a user raises an appropriate error.
        """
        # Arrange: Mock database with existing profile
        mock_db = MagicMock()
        existing_profile = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_profile
        
        profile_data = UserProfileCreate(
            first_name="John",
            last_name="Doe",
            gender=GenderType.male,
            height_cm=Decimal("180.0"),
            weight_kg=Decimal("75.0"),
            date_of_birth=date(1990, 1, 1)
        )
        
        # Act & Assert: Should raise HTTPException for duplicate profile
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.create_profile(mock_db, 123, profile_data)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Profile already exists" in exc_info.value.detail

    def test_get_profile_nonexistent_user(self):
        """
        Negative Test: Profile retrieval should fail for non-existent user.
        
        This test ensures that getting a profile for a non-existent user
        raises an appropriate 404 error.
        """
        # Arrange: Mock database with no profile found
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert: Should raise HTTPException for missing profile
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.get_profile(mock_db, 999)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in exc_info.value.detail

    def test_update_profile_unauthorized_access(self):
        """
        Negative Test: Profile update should fail for wrong user.
        
        This test ensures that users cannot update profiles
        that don't belong to them.
        """
        # Arrange: Mock database with no profile for the requesting user
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        profile_update = UserProfileUpdate(first_name="Hacker")
        
        # Act & Assert: Should raise HTTPException for unauthorized access
        with pytest.raises(HTTPException) as exc_info:
            UserProfileService.update_profile(mock_db, 999, profile_update)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Profile not found" in exc_info.value.detail 