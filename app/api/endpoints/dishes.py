from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.services.dish import DishService
from app.schemas.dish import DishCreate, DishUpdate, DishResponse, DishListResponse
from app.models.user import User

router = APIRouter()


# Create a function to optionally get current user
async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = None
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    if not token:
        return None
    try:
        from app.services.auth import AuthService
        return await AuthService.get_current_user(db=db, token=token)
    except:
        return None


@router.post("/", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
async def create_dish(
    dish_data: DishCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new dish."""
    return await DishService.create_dish(
        db=db, 
        dish_data=dish_data, 
        current_user_id=current_user.id
    )


@router.get("/search", response_model=DishListResponse)
async def search_dishes_by_name(
    q: str = Query(..., description="Search term for dish name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Search dishes by name using substring matching."""
    return await DishService.search_dishes_by_name(
        db=db,
        search_term=q,
        page=page,
        page_size=page_size
    )


@router.get("/", response_model=DishListResponse)
async def get_dishes(
    search: Optional[str] = Query(None, description="Search term for name, description, or cuisine"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine"),
    my_dishes: bool = Query(False, description="Get only dishes created by current user"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get dishes with optional search and filtering."""
    created_by_user_id = None
    if my_dishes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view your dishes. Use /dishes/my endpoint instead."
        )
    
    return await DishService.get_dishes(
        db=db,
        search=search,
        cuisine=cuisine,
        created_by_user_id=created_by_user_id,
        page=page,
        page_size=page_size
    )


@router.get("/cuisine/{cuisine}", response_model=DishListResponse)
async def get_dishes_by_cuisine(
    cuisine: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """Get dishes filtered by cuisine."""
    return await DishService.get_dishes_by_cuisine(
        db=db,
        cuisine=cuisine,
        page=page,
        page_size=page_size
    )


@router.get("/my", response_model=DishListResponse)
async def get_my_dishes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get dishes created by the current user."""
    return await DishService.get_user_dishes(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )


@router.get("/{dish_id}", response_model=DishResponse)
async def get_dish(
    dish_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific dish by ID."""
    dish = await DishService.get_dish_by_id(db=db, dish_id=dish_id)
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    return dish


@router.put("/{dish_id}", response_model=DishResponse)
async def update_dish(
    dish_id: int,
    dish_update: DishUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a dish."""
    dish = await DishService.update_dish(
        db=db,
        dish_id=dish_id,
        dish_update=dish_update,
        current_user_id=current_user.id
    )
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        )
    return dish


@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dish(
    dish_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a dish."""
    success = await DishService.delete_dish(
        db=db,
        dish_id=dish_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dish not found"
        ) 