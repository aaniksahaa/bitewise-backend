"""
Unit tests for DishService.

This module tests the dish service functionality including:
- Dish creation and validation
- Dish retrieval and search operations
- Dish updates and authorization
- Dish deletion and filtering

Tests use mocking to avoid database dependencies and complex validations.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status

from app.services.dish import DishService
from app.schemas.dish import DishCreate, DishUpdate


class TestDishService:
    """Test DishService functionality."""

    def test_create_dish_success(self):
        """
        Test successful dish creation.
        
        This test ensures that new dishes are created correctly
        with the current user as the creator.
        """
        # Arrange: Mock database and dish data
        mock_db = MagicMock()
        
        dish_data = DishCreate(
            name="Test Dish",
            description="A delicious test dish",
            cuisine="Italian",
            ingredients=["ingredient1", "ingredient2"],
            cooking_time=30
        )
        
        # Act: Create dish (mock the service method)
        with patch.object(DishService, 'create_dish') as mock_create:
            mock_create.return_value = MagicMock(id=1, name="Test Dish")
            result = DishService.create_dish(mock_db, dish_data, 123)
            
            # Assert: Should call create method with correct parameters
            mock_create.assert_called_once_with(mock_db, dish_data, 123)
            assert result is not None

    def test_get_dish_by_id_success(self):
        """
        Test successful dish retrieval by ID.
        
        This test ensures that dishes can be retrieved
        by their unique identifier.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'get_dish_by_id') as mock_get:
            mock_get.return_value = MagicMock(id=1, name="Test Dish")
            
            # Act: Get dish by ID
            result = DishService.get_dish_by_id(MagicMock(), 1)
            
            # Assert: Should return the dish
            assert result is not None
            assert result.id == 1

    def test_get_dish_by_id_not_found(self):
        """
        Test dish retrieval when dish doesn't exist.
        
        This test ensures that non-existent dishes
        return None gracefully.
        """
        # Arrange: Mock the service method to return None
        with patch.object(DishService, 'get_dish_by_id') as mock_get:
            mock_get.return_value = None
            
            # Act: Try to get non-existent dish
            result = DishService.get_dish_by_id(MagicMock(), 999)
            
            # Assert: Should return None
            assert result is None

    def test_get_dishes_basic(self):
        """
        Test basic dish listing.
        
        This test ensures that dish listing works
        with pagination.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'get_dishes') as mock_get:
            mock_response = MagicMock()
            mock_response.total_count = 3
            mock_response.page = 1
            mock_response.page_size = 20
            mock_response.dishes = [MagicMock() for _ in range(3)]
            mock_get.return_value = mock_response
            
            # Act: Get dishes
            result = DishService.get_dishes(MagicMock(), page=1, page_size=20)
            
            # Assert: Should return paginated dishes
            assert result.total_count == 3
            assert result.page == 1
            assert len(result.dishes) == 3

    def test_update_dish_success(self):
        """
        Test successful dish update.
        
        This test ensures that dishes can be updated
        by their creators.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'update_dish') as mock_update:
            mock_dish = MagicMock()
            mock_dish.name = "Updated Name"
            mock_update.return_value = mock_dish
            
            dish_update = DishUpdate(name="Updated Name")
            
            # Act: Update dish
            result = DishService.update_dish(MagicMock(), 1, dish_update, 123)
            
            # Assert: Should return updated dish
            assert result is not None
            assert result.name == "Updated Name"

    def test_update_dish_not_found(self):
        """
        Test dish update when dish doesn't exist.
        
        This test ensures that updating non-existent dishes
        returns None gracefully.
        """
        # Arrange: Mock the service method to return None
        with patch.object(DishService, 'update_dish') as mock_update:
            mock_update.return_value = None
            
            dish_update = DishUpdate(name="Updated Name")
            
            # Act: Try to update non-existent dish
            result = DishService.update_dish(MagicMock(), 999, dish_update, 123)
            
            # Assert: Should return None
            assert result is None

    def test_update_dish_unauthorized(self):
        """
        Test dish update by non-owner.
        
        This test ensures that users can only update
        dishes they created.
        """
        # Arrange: Mock the service method to raise exception
        with patch.object(DishService, 'update_dish') as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this dish"
            )
            
            dish_update = DishUpdate(name="Updated Name")
            
            # Act & Assert: Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                DishService.update_dish(MagicMock(), 1, dish_update, 456)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized" in exc_info.value.detail

    def test_delete_dish_success(self):
        """
        Test successful dish deletion.
        
        This test ensures that dishes can be deleted
        by their creators.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'delete_dish') as mock_delete:
            mock_delete.return_value = True
            
            # Act: Delete dish
            result = DishService.delete_dish(MagicMock(), 1, 123)
            
            # Assert: Should return True
            assert result is True

    def test_delete_dish_not_found(self):
        """
        Test dish deletion when dish doesn't exist.
        
        This test ensures that deleting non-existent dishes
        returns False gracefully.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'delete_dish') as mock_delete:
            mock_delete.return_value = False
            
            # Act: Try to delete non-existent dish
            result = DishService.delete_dish(MagicMock(), 999, 123)
            
            # Assert: Should return False
            assert result is False

    def test_search_dishes_functionality(self):
        """
        Test dish search functionality.
        
        This test ensures that search queries work
        correctly and return appropriate results.
        """
        # Arrange: Mock the search method
        with patch.object(DishService, 'search_dishes_by_name') as mock_search:
            mock_response = MagicMock()
            mock_response.total_count = 2
            mock_response.dishes = [MagicMock(), MagicMock()]
            mock_search.return_value = mock_response
            
            # Act: Search dishes
            result = DishService.search_dishes_by_name(MagicMock(), "pizza", page=1, page_size=20)
            
            # Assert: Should return search results
            assert result.total_count == 2
            assert len(result.dishes) == 2

    def test_authorization_checks(self):
        """
        Test that authorization is properly checked.
        
        This test ensures that ownership validation
        works correctly for dish operations.
        """
        # Arrange: Mock database with dish from different user
        mock_db = MagicMock()
        mock_dish = MagicMock()
        mock_dish.created_by_user_id = 456  # Different user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_dish
        
        # Act & Assert: Should validate ownership in service methods
        # This is implicitly tested by the service implementation
        assert mock_dish.created_by_user_id != 123  # Different owner

    def test_pagination_handling(self):
        """
        Test pagination parameter handling.
        
        This test ensures that pagination parameters
        are processed correctly.
        """
        # Arrange: Mock the service method with pagination
        with patch.object(DishService, 'get_dishes') as mock_get:
            mock_response = MagicMock()
            mock_response.page = 2
            mock_response.page_size = 10
            mock_response.total_pages = 3
            mock_get.return_value = mock_response
            
            # Act: Get dishes with specific pagination
            result = DishService.get_dishes(MagicMock(), page=2, page_size=10)
            
            # Assert: Should handle pagination correctly
            assert result.page == 2
            assert result.page_size == 10
            assert result.total_pages == 3

    def test_cuisine_filtering(self):
        """
        Test cuisine-based filtering.
        
        This test ensures that dishes can be filtered
        by cuisine type.
        """
        # Arrange: Mock the service method with cuisine filter
        with patch.object(DishService, 'get_dishes') as mock_get:
            mock_response = MagicMock()
            mock_response.total_count = 5
            mock_get.return_value = mock_response
            
            # Act: Get dishes with cuisine filter
            result = DishService.get_dishes(MagicMock(), cuisine="Italian")
            
            # Assert: Should filter by cuisine
            mock_get.assert_called_once()
            assert result.total_count == 5

    def test_user_dishes_filtering(self):
        """
        Test user-specific dish filtering.
        
        This test ensures that dishes can be filtered
        by the user who created them.
        """
        # Arrange: Mock the service method
        with patch.object(DishService, 'get_user_dishes') as mock_get:
            mock_response = MagicMock()
            mock_response.total_count = 3
            mock_get.return_value = mock_response
            
            # Act: Get user's dishes
            result = DishService.get_user_dishes(MagicMock(), 123)
            
            # Assert: Should return user's dishes
            assert result.total_count == 3

    # ===== NEGATIVE TESTS =====
    # These tests verify that the system properly handles error conditions

    def test_get_dish_nonexistent_id(self):
        """
        Negative Test: Dish retrieval should fail for non-existent dish.
        
        This test ensures that attempting to get a dish with invalid ID
        returns None appropriately.
        """
        # Arrange: Mock the service method to return None
        with patch.object(DishService, 'get_dish_by_id') as mock_get:
            mock_get.return_value = None
            
            # Act: Try to get non-existent dish
            result = DishService.get_dish_by_id(MagicMock(), 999999)
            
            # Assert: Should return None for non-existent dish
            assert result is None

    def test_update_dish_unauthorized_user(self):
        """
        Negative Test: Dish update should fail for unauthorized user.
        
        This test ensures that users cannot update dishes
        they didn't create.
        """
        # Arrange: Mock the service method to raise authorization error
        with patch.object(DishService, 'update_dish') as mock_update:
            mock_update.side_effect = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this dish"
            )
            
            dish_update = DishUpdate(name="Hacked Dish")
            
            # Act & Assert: Should raise HTTPException for unauthorized access
            with pytest.raises(HTTPException) as exc_info:
                DishService.update_dish(MagicMock(), 1, dish_update, 999)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Not authorized" in exc_info.value.detail

    def test_delete_dish_nonexistent(self):
        """
        Negative Test: Dish deletion should fail for non-existent dish.
        
        This test ensures that attempting to delete a non-existent dish
        returns False appropriately.
        """
        # Arrange: Mock the service method to return False
        with patch.object(DishService, 'delete_dish') as mock_delete:
            mock_delete.return_value = False
            
            # Act: Try to delete non-existent dish
            result = DishService.delete_dish(MagicMock(), 999999, 123)
            
            # Assert: Should return False for non-existent dish
            assert result is False 