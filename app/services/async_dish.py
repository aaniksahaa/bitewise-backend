from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, and_, select
from fastapi import HTTPException, status
import math

from app.models.dish import Dish
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListItem, DishListResponse
from app.utils.logger import dish_logger


class AsyncDishService:
    """
    Async dish service providing dish management operations using async database connections.
    
    This service handles all dish-related operations including creation, retrieval,
    updating, deletion, and search functionality with async/await patterns.
    """

    @staticmethod
    async def create_dish(db: AsyncSession, dish_data: DishCreate, current_user_id: int) -> DishResponse:
        """Create a new dish asynchronously."""
        # Create dish with user as creator
        db_dish = Dish(
            **dish_data.model_dump(),
            created_by_user_id=current_user_id
        )
        
        db.add(db_dish)
        await db.commit()
        await db.refresh(db_dish)
        
        return DishResponse.model_validate(db_dish)

    @staticmethod
    async def get_dish_by_id(db: AsyncSession, dish_id: int) -> Optional[DishResponse]:
        """Get a dish by its ID asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
        if not dish:
            return None
        
        return DishResponse.model_validate(dish)

    @staticmethod
    async def get_dishes(
        db: AsyncSession, 
        search: Optional[str] = None,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes with optional search and filtering asynchronously."""
        # If there's a search term, use the new fuzzy search
        if search and search.strip():
            return await AsyncDishService._fuzzy_search_dishes(
                db=db,
                search_term=search,
                cuisine=cuisine,
                created_by_user_id=created_by_user_id,
                page=page,
                page_size=page_size
            )
        
        # Otherwise, use the original filtering logic
        stmt = select(Dish)
        
        # Filter out dishes without images
        stmt = stmt.where(
            and_(
                Dish.image_urls.is_not(None),
                func.array_length(Dish.image_urls, 1) > 0
            )
        )
        
        # Apply cuisine filter
        if cuisine:
            stmt = stmt.where(Dish.cuisine.ilike(f"%{cuisine}%"))
            
        # Apply creator filter
        if created_by_user_id:
            stmt = stmt.where(Dish.created_by_user_id == created_by_user_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
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
    async def _fuzzy_search_dishes(
        db: AsyncSession,
        search_term: str,
        cuisine: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Internal method for fuzzy search with additional filters asynchronously."""
        # Get scored results from fuzzy search
        scored_dishes, total_before_filters = await AsyncDishService._async_search_dishes_with_scoring(
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
    async def _async_search_dishes_with_scoring(
        db: AsyncSession,
        search_term: str,
        page: int = 1,
        page_size: int = 20,
        min_score_threshold: float = 5.0
    ) -> Tuple[List[Tuple[Dish, float]], int]:
        """
        Async version of dish search with scoring.
        
        This is a simplified async implementation. For full fuzzy search functionality,
        the SearchUtils class would need to be updated to support async operations.
        For now, we'll implement basic text search with async patterns.
        """
        # Create search filters for name, description, and cuisine
        search_filter = or_(
            Dish.name.ilike(f"%{search_term}%"),
            Dish.description.ilike(f"%{search_term}%"),
            Dish.cuisine.ilike(f"%{search_term}%")
        )
        
        # Build query with image filter
        stmt = select(Dish).where(
            and_(
                search_filter,
                Dish.image_urls.is_not(None),
                func.array_length(Dish.image_urls, 1) > 0
            )
        )
        
        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
        # For now, assign a simple score based on exact matches
        # In a full implementation, this would use proper fuzzy matching algorithms
        scored_dishes = []
        for dish in dishes:
            score = 10.0  # Base score
            if search_term.lower() in dish.name.lower():
                score += 20.0
            if dish.description and search_term.lower() in dish.description.lower():
                score += 10.0
            if dish.cuisine and search_term.lower() in dish.cuisine.lower():
                score += 15.0
            
            if score >= min_score_threshold:
                scored_dishes.append((dish, score))
        
        # Sort by score descending
        scored_dishes.sort(key=lambda x: x[1], reverse=True)
        
        return scored_dishes, total_count

    @staticmethod
    async def search_dishes_by_name(
        db: AsyncSession,
        search_term: str,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """Search dishes by name with case-insensitive partial matching asynchronously."""
        
        dish_logger.debug(f"🔍 Async searching dishes: '{search_term}'", "SEARCH", 
                         page=page, page_size=page_size)
        
        # Create search filter
        search_filter = Dish.name.ilike(f"%{search_term}%")
        
        # Build query
        stmt = select(Dish).where(search_filter)
        
        # Get total count before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
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
                image_urls=dish.image_urls,
                prep_time_minutes=dish.prep_time_minutes,
                cook_time_minutes=dish.cook_time_minutes,
                servings=dish.servings,
                created_by_user_id=dish.created_by_user_id,
                carbs_g=dish.carbs_g,
                fats_g=dish.fats_g
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
    async def update_dish(
        db: AsyncSession, 
        dish_id: int, 
        dish_update: DishUpdate, 
        current_user_id: int
    ) -> Optional[DishResponse]:
        """Update an existing dish asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
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
        
        await db.commit()
        await db.refresh(dish)
        
        return DishResponse.model_validate(dish)

    @staticmethod
    async def delete_dish(db: AsyncSession, dish_id: int, current_user_id: int) -> bool:
        """Delete a dish asynchronously."""
        stmt = select(Dish).where(Dish.id == dish_id)
        result = await db.execute(stmt)
        dish = result.scalar_one_or_none()
        
        if not dish:
            return False
            
        # Check if user owns this dish
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this dish"
            )
        
        await db.delete(dish)
        await db.commit()
        
        return True

    @staticmethod
    async def get_user_dishes(
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get all dishes created by a specific user asynchronously."""
        return await AsyncDishService.get_dishes(
            db=db,
            created_by_user_id=user_id,
            page=page,
            page_size=page_size
        )

    @staticmethod
    async def get_dishes_by_cuisine(
        db: AsyncSession, 
        cuisine: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get dishes filtered by cuisine asynchronously."""
        return await AsyncDishService.get_dishes(
            db=db,
            cuisine=cuisine,
            page=page,
            page_size=page_size
        )

    @staticmethod
    async def get_dishes_with_ingredients(
        db: AsyncSession,
        dish_ids: List[int]
    ) -> List[Dish]:
        """
        Get dishes with their ingredient relationships loaded asynchronously.
        
        This method demonstrates async relationship handling for dish-ingredient relationships.
        """
        if not dish_ids:
            return []
        
        # Use selectinload or joinedload for async relationship loading
        # For now, we'll use a simple approach without explicit relationship loading
        stmt = select(Dish).where(Dish.id.in_(dish_ids))
        result = await db.execute(stmt)
        dishes = result.scalars().all()
        
        # If we had dish-ingredient relationships defined in the model,
        # we would use something like:
        # stmt = select(Dish).options(selectinload(Dish.ingredients)).where(Dish.id.in_(dish_ids))
        
        return dishes

    @staticmethod
    async def bulk_update_dishes(
        db: AsyncSession,
        dish_updates: List[Tuple[int, DishUpdate]],
        current_user_id: int
    ) -> List[DishResponse]:
        """
        Bulk update multiple dishes asynchronously.
        
        This method demonstrates async bulk operations for better performance
        when updating multiple dishes at once.
        """
        updated_dishes = []
        
        for dish_id, dish_update in dish_updates:
            try:
                updated_dish = await AsyncDishService.update_dish(
                    db=db,
                    dish_id=dish_id,
                    dish_update=dish_update,
                    current_user_id=current_user_id
                )
                if updated_dish:
                    updated_dishes.append(updated_dish)
            except HTTPException:
                # Skip dishes that can't be updated (permission issues, not found, etc.)
                continue
        
        return updated_dishes

    @staticmethod
    async def get_popular_dishes(
        db: AsyncSession,
        limit: int = 10
    ) -> List[DishListItem]:
        """
        Get popular dishes based on some criteria (placeholder implementation).
        
        This method demonstrates how to implement complex queries with async patterns.
        In a real implementation, this might consider factors like:
        - Number of times a dish has been logged in intakes
        - User ratings
        - Recent activity
        """
        # For now, just return the most recently created dishes
        stmt = select(Dish).order_by(Dish.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        dishes = result.scalars().all()
        
        return [DishListItem.model_validate(dish) for dish in dishes]

    @staticmethod
    async def search_dishes_by_nutrition(
        db: AsyncSession,
        min_protein: Optional[float] = None,
        max_calories: Optional[float] = None,
        min_fiber: Optional[float] = None,
        page: int = 1,
        page_size: int = 20
    ) -> DishListResponse:
        """
        Search dishes by nutritional criteria asynchronously.
        
        This method demonstrates complex filtering with async patterns.
        """
        stmt = select(Dish)
        
        # Apply nutritional filters
        if min_protein is not None:
            stmt = stmt.where(Dish.protein_g >= min_protein)
        
        if max_calories is not None:
            stmt = stmt.where(Dish.calories <= max_calories)
        
        if min_fiber is not None:
            stmt = stmt.where(Dish.fiber_g >= min_fiber)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        dishes = result.scalars().all()
        
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