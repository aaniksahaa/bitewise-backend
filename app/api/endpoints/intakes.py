from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.services.intake import IntakeService
from app.schemas.intake import (
    IntakeCreate, 
    IntakeCreateByName,
    IntakeUpdate, 
    IntakeResponse, 
    IntakeListResponse
)
from app.models.user import User

router = APIRouter()


@router.post("/", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def create_intake(
    intake_data: IntakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new intake record."""
    return IntakeService.create_intake(
        db=db, 
        intake_data=intake_data, 
        current_user_id=current_user.id
    )


@router.post("/by-name", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def create_intake_by_name(
    intake_data: IntakeCreateByName,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new intake record using dish name instead of dish ID."""
    return IntakeService.create_intake_by_name(
        db=db, 
        intake_data=intake_data, 
        current_user_id=current_user.id
    )


@router.get("/", response_model=IntakeListResponse)
async def get_my_intakes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes for the current user with pagination."""
    return IntakeService.get_user_intakes(
        db=db,
        current_user_id=current_user.id,
        page=page,
        page_size=page_size
    )


@router.get("/period", response_model=IntakeListResponse)
async def get_intakes_by_period(
    start_time: datetime = Query(..., description="Start of the time period (ISO format)"),
    end_time: datetime = Query(..., description="End of the time period (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get intakes for the current user between specific date/time periods."""
    return IntakeService.get_intakes_by_period(
        db=db,
        current_user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )


@router.get("/today", response_model=IntakeListResponse)
async def get_today_intakes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes from the last 24 hours for the current user."""
    return IntakeService.get_today_intakes(
        db=db,
        current_user_id=current_user.id
    )


@router.get("/calendar-day", response_model=IntakeListResponse)
async def get_calendar_day_intakes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes for the current calendar day (00:00 to 23:59 today) for the current user."""
    return IntakeService.get_calendar_day_intakes(
        db=db,
        current_user_id=current_user.id
    )


@router.get("/filter", response_model=IntakeListResponse)
async def get_filtered_intakes(
    # Intake-specific filters
    min_intake_time: Optional[datetime] = Query(None, description="Minimum intake time (ISO format)"),
    max_intake_time: Optional[datetime] = Query(None, description="Maximum intake time (ISO format)"),
    min_portion_size: Optional[float] = Query(None, ge=0, description="Minimum portion size"),
    max_portion_size: Optional[float] = Query(None, ge=0, description="Maximum portion size"),
    min_water_ml: Optional[int] = Query(None, ge=0, description="Minimum water intake in ml"),
    max_water_ml: Optional[int] = Query(None, ge=0, description="Maximum water intake in ml"),
    # Dish-based filters
    dish_search: Optional[str] = Query(None, description="Search term for dish name, description, or cuisine"),
    cuisine: Optional[str] = Query(None, description="Filter by dish cuisine type"),
    has_image: Optional[bool] = Query(None, description="Filter by dish image availability"),
    min_prep_time: Optional[int] = Query(None, ge=0, description="Minimum dish preparation time in minutes"),
    max_prep_time: Optional[int] = Query(None, ge=0, description="Maximum dish preparation time in minutes"),
    min_cook_time: Optional[int] = Query(None, ge=0, description="Minimum dish cooking time in minutes"),
    max_cook_time: Optional[int] = Query(None, ge=0, description="Maximum dish cooking time in minutes"),
    min_servings: Optional[int] = Query(None, ge=1, description="Minimum dish number of servings"),
    max_servings: Optional[int] = Query(None, ge=1, description="Maximum dish number of servings"),
    min_calories: Optional[float] = Query(None, ge=0, description="Minimum dish calories per serving"),
    max_calories: Optional[float] = Query(None, ge=0, description="Maximum dish calories per serving"),
    min_protein: Optional[float] = Query(None, ge=0, description="Minimum dish protein in grams"),
    max_protein: Optional[float] = Query(None, ge=0, description="Maximum dish protein in grams"),
    min_carbs: Optional[float] = Query(None, ge=0, description="Minimum dish carbohydrates in grams"),
    max_carbs: Optional[float] = Query(None, ge=0, description="Maximum dish carbohydrates in grams"),
    min_fats: Optional[float] = Query(None, ge=0, description="Minimum dish fats in grams"),
    max_fats: Optional[float] = Query(None, ge=0, description="Maximum dish fats in grams"),
    min_sugar: Optional[float] = Query(None, ge=0, description="Minimum dish sugar in grams"),
    max_sugar: Optional[float] = Query(None, ge=0, description="Maximum dish sugar in grams"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get intakes with comprehensive filtering support including dish-based filters."""
    return IntakeService.get_filtered_intakes(
        db=db,
        current_user_id=current_user.id,
        min_intake_time=min_intake_time,
        max_intake_time=max_intake_time,
        min_portion_size=min_portion_size,
        max_portion_size=max_portion_size,
        min_water_ml=min_water_ml,
        max_water_ml=max_water_ml,
        dish_search=dish_search,
        cuisine=cuisine,
        has_image=has_image,
        min_prep_time=min_prep_time,
        max_prep_time=max_prep_time,
        min_cook_time=min_cook_time,
        max_cook_time=max_cook_time,
        min_servings=min_servings,
        max_servings=max_servings,
        min_calories=min_calories,
        max_calories=max_calories,
        min_protein=min_protein,
        max_protein=max_protein,
        min_carbs=min_carbs,
        max_carbs=max_carbs,
        min_fats=min_fats,
        max_fats=max_fats,
        min_sugar=min_sugar,
        max_sugar=max_sugar,
        page=page,
        page_size=page_size
    )


@router.get("/{intake_id}", response_model=IntakeResponse)
async def get_intake(
    intake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific intake by ID (only for the current user)."""
    intake = IntakeService.get_intake_by_id(
        db=db, 
        intake_id=intake_id, 
        current_user_id=current_user.id
    )
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        )
    return intake


@router.put("/{intake_id}", response_model=IntakeResponse)
async def update_intake(
    intake_id: int,
    intake_update: IntakeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an intake (only for the current user)."""
    intake = IntakeService.update_intake(
        db=db,
        intake_id=intake_id,
        intake_update=intake_update,
        current_user_id=current_user.id
    )
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        )
    return intake


@router.delete("/{intake_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intake(
    intake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an intake (only for the current user)."""
    success = IntakeService.delete_intake(
        db=db,
        intake_id=intake_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        ) 