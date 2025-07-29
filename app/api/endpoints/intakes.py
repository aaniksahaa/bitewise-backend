from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new intake record."""
    return await IntakeService.create_intake(
        db=db, 
        intake_data=intake_data, 
        current_user_id=current_user.id
    )


@router.post("/by-name", response_model=IntakeResponse, status_code=status.HTTP_201_CREATED)
async def create_intake_by_name(
    intake_data: IntakeCreateByName,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new intake record using dish name instead of dish ID."""
    return await IntakeService.create_intake_by_name(
        db=db, 
        intake_data=intake_data, 
        current_user_id=current_user.id
    )


@router.get("/", response_model=IntakeListResponse)
async def get_my_intakes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes for the current user with pagination."""
    return await IntakeService.get_user_intakes(
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get intakes for the current user between specific date/time periods."""
    return await IntakeService.get_intakes_by_period(
        db=db,
        current_user_id=current_user.id,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )


@router.get("/today", response_model=IntakeListResponse)
async def get_today_intakes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes from the last 24 hours for the current user."""
    return await IntakeService.get_today_intakes(
        db=db,
        current_user_id=current_user.id
    )


@router.get("/calendar-day", response_model=IntakeListResponse)
async def get_calendar_day_intakes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all intakes for the current calendar day (00:00 to 23:59 today) for the current user."""
    return await IntakeService.get_calendar_day_intakes(
        db=db,
        current_user_id=current_user.id
    )


@router.get("/{intake_id}", response_model=IntakeResponse)
async def get_intake(
    intake_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific intake by ID (only for the current user)."""
    intake = await IntakeService.get_intake_by_id(
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an intake (only for the current user)."""
    intake = await IntakeService.update_intake(
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


@router.delete("/{intake_id}", status_code=status.HTTP_200_OK)
async def delete_intake(
    intake_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an intake (only for the current user)."""
    success = await IntakeService.delete_intake(
        db=db,
        intake_id=intake_id,
        current_user_id=current_user.id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intake not found"
        ) 
    return {"message": f"Intake {intake_id} deleted successfully"}