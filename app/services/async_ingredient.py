from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select, and_
import math

from app.models.ingredient import Ingredient
from app.models.dish_ingredient import DishIngredient
from app.schemas.ingredient import IngredientResponse, IngredientListItem, IngredientListResponse, DishIngredientResponse


class AsyncIngredientService:
    """
    Async ingredient service providing ingredient management operations.
    """

    @staticmethod
    async def get_ingredient_by_id(db: AsyncSession, ingredient_id: int) -> Optional[IngredientResponse]:
        """Get an ingredient by its ID asynchronously."""
        stmt = select(Ingredient).where(Ingredient.id == ingredient_id)
        result = await db.execute(stmt)
        ingredient = result.scalar_one_or_none()
        
        if not ingredient:
            return None
        
        return IngredientResponse.model_validate(ingredient)

    @staticmethod
    async def get_ingredients(
        db: AsyncSession, 
        search: Optional[str] = None,
        page: int = 1, 
        page_size: int = 20
    ) -> IngredientListResponse:
        """Get ingredients with optional search and pagination."""
        stmt = select(Ingredient)
        
        # Filter out ingredients without images
        stmt = stmt.where(
            and_(
                Ingredient.image_url.is_not(None),
                Ingredient.image_url != ''
            )
        )
        
        # Apply search filter if provided
        if search and search.strip():
            search_term = f"%{search.strip().lower()}%"
            stmt = stmt.where(
                func.lower(Ingredient.name).like(search_term)
            )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        ingredients = result.scalars().all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        ingredient_items = [IngredientListItem.model_validate(ingredient) for ingredient in ingredients]
        
        return IngredientListResponse(
            ingredients=ingredient_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    async def search_ingredients_by_name(
        db: AsyncSession,
        search_term: str,
        page: int = 1,
        page_size: int = 20
    ) -> IngredientListResponse:
        """Search ingredients by name using substring matching."""
        return await AsyncIngredientService.get_ingredients(
            db=db,
            search=search_term,
            page=page,
            page_size=page_size
        )

    @staticmethod
    async def get_ingredients_by_dish_id(
        db: AsyncSession,
        dish_id: int
    ) -> List[DishIngredientResponse]:
        """Get all ingredients for a specific dish with quantities."""
        stmt = (
            select(DishIngredient, Ingredient)
            .join(Ingredient, DishIngredient.ingredient_id == Ingredient.id)
            .where(DishIngredient.dish_id == dish_id)
        )
        
        result = await db.execute(stmt)
        dish_ingredients = result.all()
        
        response_items = []
        for dish_ingredient, ingredient in dish_ingredients:
            ingredient_response = IngredientResponse.model_validate(ingredient)
            response_items.append(DishIngredientResponse(
                ingredient=ingredient_response,
                quantity=dish_ingredient.quantity
            ))
        
        return response_items

    @staticmethod
    async def get_dishes_by_ingredient_id(
        db: AsyncSession,
        ingredient_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """Get all dishes that contain a specific ingredient."""
        from app.models.dish import Dish
        
        # Get dishes that contain this ingredient
        stmt = (
            select(Dish)
            .join(DishIngredient, Dish.id == DishIngredient.dish_id)
            .where(DishIngredient.ingredient_id == ingredient_id)
        )
        
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
        
        # Convert to lightweight dish format
        from app.schemas.dish import DishListItem
        dish_items = [DishListItem.model_validate(dish) for dish in dishes]
        
        return {
            "dishes": dish_items,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        } 