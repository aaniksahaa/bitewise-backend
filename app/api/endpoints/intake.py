from datetime import date
from typing import Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.dish import Dish
from app.services.auth import get_current_active_user
from app.services.intake import IntakeService
from app.schemas.intake import (
    IntakeCreate,
    IntakeUpdate,
    IntakeResponse,
    IntakeListResponse,
    IntakeSummary
)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=IntakeResponse)
async def create_intake(
    intake_data: IntakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new food intake record for the authenticated user.
    
    - **dish_id**: ID of the dish being consumed
    - **intake_time**: When the dish was consumed
    - **portion_size**: Portion size relative to dish serving (default: 1.0)
    - **water_ml**: Water intake in milliliters (optional)
    """
    # Create the intake
    intake = IntakeService.create_intake(db, intake_data, current_user.id)
    
    # Get dish information for response
    dish = db.query(Dish).filter(Dish.id == intake.dish_id).first()
    
    return IntakeService.build_intake_response(intake, dish)


@router.get("/{intake_id}", response_model=IntakeResponse)
async def get_intake(
    intake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific intake record by ID for the authenticated user.
    """
    intake = IntakeService.get_intake_by_id(db, intake_id, current_user.id)
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        )
    
    # Get dish information for response
    dish = db.query(Dish).filter(Dish.id == intake.dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated dish not found"
        )
    
    return IntakeService.build_intake_response(intake, dish)


@router.get("/", response_model=IntakeListResponse)
async def get_intakes(
    start_date: Optional[date] = Query(None, description="Start date for filtering (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for filtering (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all intake records for the authenticated user with optional date filtering and pagination.
    
    - **start_date**: Optional start date for filtering (YYYY-MM-DD)
    - **end_date**: Optional end date for filtering (YYYY-MM-DD)  
    - **page**: Page number (default: 1)
    - **page_size**: Number of items per page (default: 50, max: 100)
    """
    # Get intakes and total count
    intakes, total_count = IntakeService.get_intakes(
        db, current_user.id, start_date, end_date, page, page_size
    )
    
    # Build response list with dish information
    intake_responses = []
    for intake in intakes:
        dish = db.query(Dish).filter(Dish.id == intake.dish_id).first()
        if dish:  # Only include if dish exists
            intake_responses.append(
                IntakeService.build_intake_response(intake, dish)
            )
    
    # Calculate pagination info
    total_pages = ceil(total_count / page_size) if total_count > 0 else 1
    
    return IntakeListResponse(
        intakes=intake_responses,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.put("/{intake_id}", response_model=IntakeResponse)
async def update_intake(
    intake_id: int,
    intake_data: IntakeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing intake record for the authenticated user.
    
    Only provide the fields you want to update:
    - **dish_id**: New dish ID (optional)
    - **intake_time**: New intake time (optional)
    - **portion_size**: New portion size (optional)
    - **water_ml**: New water intake amount (optional)
    """
    # Update the intake
    intake = IntakeService.update_intake(db, intake_id, intake_data, current_user.id)
    if not intake:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        )
    
    # Get dish information for response
    dish = db.query(Dish).filter(Dish.id == intake.dish_id).first()
    if not dish:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated dish not found"
        )
    
    return IntakeService.build_intake_response(intake, dish)


@router.delete("/{intake_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_intake(
    intake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an intake record for the authenticated user.
    """
    success = IntakeService.delete_intake(db, intake_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        )
    
    return None


@router.get("/summary/nutrition", response_model=IntakeSummary)
async def get_intake_summary(
    start_date: Optional[date] = Query(None, description="Start date for summary (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for summary (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get nutritional summary of intake records for the authenticated user within a date range.
    
    If no dates are provided, returns summary for all intake records.
    
    - **start_date**: Optional start date for summary (YYYY-MM-DD)
    - **end_date**: Optional end date for summary (YYYY-MM-DD)
    """
    return IntakeService.get_intake_summary(
        db, current_user.id, start_date, end_date
    ) 