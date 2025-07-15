from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, and_, select, update, func
from fastapi import HTTPException, status
import math

from app.models.dish import Dish
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListItem, DishListResponse
from app.utils.search import SearchUtils
from app.utils.logger import dish_logger


class DishService:
    @staticmethod
    async def create_dish(db: AsyncSession, dish_data: DishCreate, current_user_id: int) -> DishResponse:
        """Create a new dish."""
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
        """Get a dish by its ID."""
        # dish = db.query(Dish).filter(Dish.id == dish_id).first()
        # modified for asyncio
        dish = (await db.execute(select(Dish).where(Dish.id == dish_id))).scalars().first()
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
        """Get dishes with optional search and filtering."""
        # If there's a search term, use the new fuzzy search
        if search and search.strip():
            return await DishService._fuzzy_search_dishes(
                db=db,
                search_term=search,
                cuisine=cuisine,
                created_by_user_id=created_by_user_id,
                page=page,
                page_size=page_size
            )
        
        # Otherwise, use the original filtering logic
        # query = db.query(Dish)
        # modified for asyncio
        query = select(Dish)
        
        # Apply cuisine filter
        if cuisine:
            # query = query.filter(Dish.cuisine.ilike(f"%{cuisine}%"))
            query = query.where(Dish.cuisine.ilike(f"%{cuisine}%"))
            
        # Apply creator filter
        if created_by_user_id:
            # query = query.filter(Dish.created_by_user_id == created_by_user_id)
            query = query.where(Dish.created_by_user_id == created_by_user_id)
        
        # Get total count
        # total_count = query.count()
        # modified for asyncio
        total_count = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        # dishes = query.offset(offset).limit(page_size).all()
        # modified for asyncio
        dishes = (await db.execute(query.offset(offset).limit(page_size))).scalars().all()
        
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
        """Internal method for fuzzy search with additional filters."""
        # Get scored results from fuzzy search
        scored_dishes, total_before_filters = await SearchUtils.search_dishes_with_scoring(
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
    async def search_dishes_by_name(
        db: AsyncSession,
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
        # query = db.query(Dish).filter(search_filter)
        # modified for asyncio
        query = select(Dish).where(search_filter)
        
        # Get total count before pagination
        # total_count = query.count()
        # modified for asyncio
        total_count = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        
        # Apply pagination
        offset = (page - 1) * page_size
        # dishes = query.offset(offset).limit(page_size).all()
        # modified for asyncio
        dishes = (await db.execute(query.offset(offset).limit(page_size))).scalars().all()
        
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
    async def update_dish(
        db: AsyncSession, 
        dish_id: int, 
        dish_update: DishUpdate, 
        current_user_id: int
    ) -> Optional[DishResponse]:
        """Update an existing dish."""
        # dish = db.query(Dish).filter(Dish.id == dish_id).first()
        # modified for asyncio
        dish = (await db.execute(select(Dish).where(Dish.id == dish_id))).scalars().first()
        
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
        """Delete a dish."""
        # dish = db.query(Dish).filter(Dish.id == dish_id).first()
        # modified for asyncio
        dish = (await db.execute(select(Dish).where(Dish.id == dish_id))).scalars().first()
        
        if not dish:
            return False
            
        # Check if user owns this dish
        if dish.created_by_user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this dish"
            )
        
        db.delete(dish)
        await db.commit()
        
        return True

    @staticmethod
    async def get_user_dishes(
        db: AsyncSession, 
        user_id: int, 
        page: int = 1, 
        page_size: int = 20
    ) -> DishListResponse:
        """Get all dishes created by a specific user."""
        return await DishService.get_dishes(
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
        """Get dishes filtered by cuisine."""
        return await DishService.get_dishes(
            db=db,
            cuisine=cuisine,
            page=page,
            page_size=page_size
        ) 