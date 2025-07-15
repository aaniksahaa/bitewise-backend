from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from fastapi import HTTPException, status
import math

from app.models.dish import Dish
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListItem, DishListResponse
from app.utils.search import SearchUtils
from app.utils.logger import dish_logger


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
        """Search dishes by name with case-insensitive partial matching."""
        
        dish_logger.debug(f"🔍 Searching dishes: '{search_term}'", "SEARCH", 
                         page=page, page_size=page_size)
        
        # Create search filter
        search_filter = Dish.name.ilike(f"%{search_term}%")
        
        # Build query
        query = db.query(Dish).filter(search_filter)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        dishes = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to list items
        dish_items = [
            DishListItem(
                id=dish.id,
                name=dish.name,
                description=dish.description,
                cuisine=dish.cuisine,
                calories=dish.calories,
                protein_g=dish.protein_g,
                created_at=dish.created_at,
                image_urls=dish.image_urls
            )
            for dish in dishes
        ]
        
        dish_logger.success(f"Found {total_count} dishes", "SEARCH",
                          search_term=search_term, returned_count=len(dishes), total_count=total_count)
        
        if dishes and len(dishes) <= 3:
            # Log the names of found dishes for debugging
            dish_names = [dish.name for dish in dishes]
            dish_logger.debug(f"Results: {', '.join(dish_names)}", "SEARCH")
        
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
            
        # # Check if user owns this dish or is admin (for now just check ownership)
        # if dish.created_by_user_id != current_user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to update this dish"
        #     )
        
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
            
        # # Check if user owns this dish
        # if dish.created_by_user_id != current_user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Not authorized to delete this dish"
        #     )
        
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

    @staticmethod
    def get_dishes_by_prep_time(
        db: Session,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes sorted by preparation time (ascending)."""
        # Build query to get dishes sorted by prep_time_minutes
        query = db.query(Dish).filter(Dish.prep_time_minutes.isnot(None)).order_by(Dish.prep_time_minutes.asc())
        
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
    def get_avg_prep_time(
        db: Session,
        search_term: str
    ) -> float:
        """Get avg prep time for dishes matching search term"""

        search_filter = Dish.name.ilike(f"%{search_term}%")

        # Build query to get dishes sorted by prep_time_minutes
        query = db.query(func.avg(Dish.prep_time_minutes)).filter(search_filter)

        avg_prep_time = query.scalar()

        return avg_prep_time or 0.0

    # @staticmethod
    # def get_avg_ingredient_count(
    #     db: Session,
    #     search_term: str
    # ) -> float:
    #     """Get average count of ingredients per dish for dishes matching search term"""
    #     from app.models.dish_ingredient import DishIngredient
        
    #     # First get the matching dishes and their ingredient counts
    #     search_filter = Dish.name.ilike(f"%{search_term}%")
        
    #     # JOIN dishes with dish_ingredients and count ingredients per dish
    #     subquery = (
    #         db.query(
    #             Dish.id,
    #             func.count(DishIngredient.ingredient_id).label('ingredient_count')
    #         )
    #         .join(DishIngredient, Dish.id == DishIngredient.dish_id)
    #         .filter(search_filter)
    #         .group_by(Dish.id)
    #         .subquery()
    #     )
        
    #     # Calculate average of ingredient counts
    #     avg_count = db.query(func.avg(subquery.c.ingredient_count)).scalar()
        
    #     return float(avg_count) if avg_count else 0.0

    @staticmethod
    def get_avg_ingredient_count(
        db: Session,
        search_term: str
    ) -> float:
        from app.models.dish_ingredient import DishIngredient

        search_filter = Dish.name.ilike(f"%{search_term}%")
        
        subquery =(
            db.query(
                Dish.id, 
                func.count(DishIngredient.ingredient_id).label('ingred_count')
            ).join(DishIngredient, Dish.id == DishIngredient.dish_id)
            .filter(search_filter)
            .group_by(Dish.id)
            .subquery()
        )

        avg_count = db.query(func.avg(subquery.c.ingred_count)).scalar()

        return avg_count or 0.0

    @staticmethod
    def get_filtered_dishes(
        db: Session,
        search: Optional[str] = None,
        cuisine: Optional[str] = None,
        has_image: Optional[bool] = None,
        min_prep_time: Optional[int] = None,
        max_prep_time: Optional[int] = None,
        min_cook_time: Optional[int] = None,
        max_cook_time: Optional[int] = None,
        min_servings: Optional[int] = None,
        max_servings: Optional[int] = None,
        min_calories: Optional[float] = None,
        max_calories: Optional[float] = None,
        min_protein: Optional[float] = None,
        max_protein: Optional[float] = None,
        min_carbs: Optional[float] = None,
        max_carbs: Optional[float] = None,
        min_fats: Optional[float] = None,
        max_fats: Optional[float] = None,
        min_sugar: Optional[float] = None,
        max_sugar: Optional[float] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes with comprehensive filtering support."""
        
        dish_logger.debug(f"🔍 Filtering dishes with comprehensive criteria", "FILTER",
                         search=search, cuisine=cuisine, has_image=has_image,
                         min_prep_time=min_prep_time, max_prep_time=max_prep_time,
                         min_cook_time=min_cook_time, max_cook_time=max_cook_time,
                         min_servings=min_servings, max_servings=max_servings,
                         min_calories=min_calories, max_calories=max_calories,
                         min_protein=min_protein, max_protein=max_protein,
                         min_carbs=min_carbs, max_carbs=max_carbs,
                         min_fats=min_fats, max_fats=max_fats,
                         min_sugar=min_sugar, max_sugar=max_sugar,
                         page=page, page_size=page_size)
        
        query = db.query(Dish)
        
        # Text search (case insensitive in name, description, or cuisine)
        if search and search.strip():
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Dish.name.ilike(search_term),
                    Dish.description.ilike(search_term),
                    Dish.cuisine.ilike(search_term)
                )
            )
        
        # Cuisine filter
        if cuisine:
            query = query.filter(Dish.cuisine.ilike(f"%{cuisine}%"))
        
        # Image availability filter
        if has_image is not None:
            if has_image:
                query = query.filter(
                    and_(
                        Dish.image_urls.isnot(None),
                        func.array_length(Dish.image_urls, 1) > 0
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Dish.image_urls.is_(None),
                        func.array_length(Dish.image_urls, 1) == 0
                    )
                )
        
        # Prep time filters
        if min_prep_time is not None:
            query = query.filter(Dish.prep_time_minutes >= min_prep_time)
        if max_prep_time is not None:
            query = query.filter(Dish.prep_time_minutes <= max_prep_time)
        
        # Cook time filters
        if min_cook_time is not None:
            query = query.filter(Dish.cook_time_minutes >= min_cook_time)
        if max_cook_time is not None:
            query = query.filter(Dish.cook_time_minutes <= max_cook_time)
        
        # Servings filters
        if min_servings is not None:
            query = query.filter(Dish.servings >= min_servings)
        if max_servings is not None:
            query = query.filter(Dish.servings <= max_servings)
        
        # Nutritional filters
        if min_calories is not None:
            query = query.filter(Dish.calories >= min_calories)
        if max_calories is not None:
            query = query.filter(Dish.calories <= max_calories)
        
        if min_protein is not None:
            query = query.filter(Dish.protein_g >= min_protein)
        if max_protein is not None:
            query = query.filter(Dish.protein_g <= max_protein)
        
        if min_carbs is not None:
            query = query.filter(Dish.carbs_g >= min_carbs)
        if max_carbs is not None:
            query = query.filter(Dish.carbs_g <= max_carbs)
        
        if min_fats is not None:
            query = query.filter(Dish.fats_g >= min_fats)
        if max_fats is not None:
            query = query.filter(Dish.fats_g <= max_fats)
        
        if min_sugar is not None:
            query = query.filter(Dish.sugar_g >= min_sugar)
        if max_sugar is not None:
            query = query.filter(Dish.sugar_g <= max_sugar)
        
        # Creator filter
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
        
        dish_logger.success(f"Found {total_count} dishes with filters", "FILTER",
                          returned_count=len(dishes), total_count=total_count)
        
        return DishListResponse(
            dishes=dish_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )