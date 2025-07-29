from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.async_session import get_async_db
from app.services.async_ingredient import AsyncIngredientService
from app.schemas.ingredient import IngredientResponse, IngredientListResponse, DishIngredientResponse

router = APIRouter()


@router.get("/", response_model=IngredientListResponse)
@router.get("", response_model=IngredientListResponse)  # Handle requests without trailing slash
async def get_ingredients(
    search: Optional[str] = Query(None, description="Search term for ingredient name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get ingredients with optional search and pagination."""
    return await AsyncIngredientService.get_ingredients(
        db=db,
        search=search,
        page=page,
        page_size=page_size
    )


@router.get("/search", response_model=IngredientListResponse)
async def search_ingredients_by_name(
    q: str = Query(..., description="Search term for ingredient name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Search ingredients by name using substring matching."""
    return await AsyncIngredientService.search_ingredients_by_name(
        db=db,
        search_term=q,
        page=page,
        page_size=page_size
    )


@router.get("/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific ingredient by ID."""
    ingredient = await AsyncIngredientService.get_ingredient_by_id(db=db, ingredient_id=ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    return ingredient


@router.get("/{ingredient_id}/dishes")
async def get_dishes_by_ingredient(
    ingredient_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get dishes that contain a specific ingredient."""
    # First check if ingredient exists
    ingredient = await AsyncIngredientService.get_ingredient_by_id(db=db, ingredient_id=ingredient_id)
    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingredient not found"
        )
    
    return await AsyncIngredientService.get_dishes_by_ingredient_id(
        db=db,
        ingredient_id=ingredient_id,
        page=page,
        page_size=page_size
    ) 