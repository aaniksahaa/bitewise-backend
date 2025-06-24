from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status
import math

from app.models.dish import Dish
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListItem, DishListResponse
from app.utils.search import SearchUtils


class DishService:
    @staticmethod
    def create_dish(db: Session, dish_data: DishCreate, current_user_id: int) -> DishResponse:
        """Create a new dish."""
        # Create dish with user as creator
        db_dish = Dish(
            **dish_data.model_dump(),
            created_by_user_id=current_user_id
        )
        
        db.add(db_dish)
        db.commit()
        db.refresh(db_dish)
        
        return DishResponse.model_validate(db_dish)

    @staticmethod
    def get_dish_by_id(db: Session, dish_id: int) -> Optional[DishResponse]:
        """Get a dish by its ID."""
        dish = db.query(Dish).filter(Dish.id == dish_id).first()
        if not dish:
            return None
        
        return DishResponse.model_validate(dish)

    @staticmethod
    def get_dishes(
        db: Session, 
        search: Optional[str] = None,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes with optional search and filtering."""
        # If there's a search term, use the new fuzzy search
        if search and search.strip():
            return DishService._fuzzy_search_dishes(
                db=db,
                search_term=search,
                cuisine=cuisine,
                created_by_user_id=created_by_user_id,
                page=page,
                page_size=page_size
            )
        
        # Otherwise, use the original filtering logic
        query = db.query(Dish)
        
        # Apply cuisine filter
        if cuisine:
            query = query.filter(Dish.cuisine.ilike(f"%{cuisine}%"))
            
        # Apply creator filter
        if created_by_user_id:
            query = query.filter(Dish.created_by_user_id == created_by_user_id)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        dishes = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        dish_items = [DishListItem.model_validate(dish) for dish in dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def _fuzzy_search_dishes(
        db: Session,
        search_term: str,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Internal method for fuzzy search with additional filters."""
        # Get scored results from fuzzy search
        scored_dishes, total_before_filters = SearchUtils.search_dishes_with_scoring(
            db=db,
            search_term=search_term,
            page=1,  # Get all results first for filtering
            page_size=1000,  # Large number to get all results
            min_score_threshold=5.0  # Lower threshold for more inclusive results
        )
        
        # Apply additional filters if specified
        if cuisine or created_by_user_id:
            filtered_dishes = []
            for dish, score in scored_dishes:
                # Apply cuisine filter
                if cuisine and not (dish.cuisine and cuisine.lower() in dish.cuisine.lower()):
                    continue
                
                # Apply creator filter
                if created_by_user_id and dish.created_by_user_id != created_by_user_id:
                    continue
                
                filtered_dishes.append((dish, score))
            
            scored_dishes = filtered_dishes
        
        # Apply pagination to filtered results
        total_count = len(scored_dishes)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_dishes = scored_dishes[start_idx:end_idx]
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format (ignoring scores in final response)
        dish_items = [DishListItem.model_validate(dish) for dish, score in paginated_dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def search_dishes_by_name(
        db: Session, 
        search_term: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Search dishes by name using intelligent fuzzy matching and scoring."""
        # Use the new fuzzy search utility
        scored_dishes, total_count = SearchUtils.search_dishes_with_scoring(
            db=db,
            search_term=search_term,
            page=page,
            page_size=page_size,
            min_score_threshold=10.0  # Reasonable threshold for name search
        )
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format (ignoring scores in final response)
        dish_items = [DishListItem.model_validate(dish) for dish, score in scored_dishes]
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_dish(
        db: Session, 
        dish_id: int, 
        dish_update: DishUpdate, 
        current_user_id: int
    ) -> Optional[DishResponse]:
        """Update an existing dish."""
        dish = db.query(Dish).filter(Dish.id == dish_id).first()
        
        if not dish:
            return None
            
        # Check if user owns this dish or is admin (for now just check ownership)
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this dish"
            )
        
        # Update only provided fields
        update_data = dish_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dish, field, value)
        
        db.commit()
        db.refresh(dish)
        
        return DishResponse.model_validate(dish)

    @staticmethod
    def delete_dish(db: Session, dish_id: int, current_user_id: int) -> bool:
        """Delete a dish."""
        dish = db.query(Dish).filter(Dish.id == dish_id).first()
        
        if not dish:
            return False
            
        # Check if user owns this dish
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this dish"
            )
        
        db.delete(dish)
        db.commit()
        
        return True

    @staticmethod
    def get_user_dishes(
        db: Session, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get all dishes created by a specific user."""
        return DishService.get_dishes(
            db=db,
            created_by_user_id=user_id,
            page=page,
            page_size=page_size
        )

    @staticmethod
    def get_dishes_by_cuisine(
        db: Session, 
        cuisine: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes filtered by cuisine."""
        return DishService.get_dishes(
            db=db,
            cuisine=cuisine,
            page=page,
            page_size=page_size
        ) 