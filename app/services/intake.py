from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status
import math

from app.models.intake import Intake
from app.models.dish import Dish
from app.schemas.intake import (
    IntakeCreate, 
    IntakeUpdate, 
    IntakeResponse, 
    IntakeListItem, 
    IntakeListResponse
)


class IntakeService:
    @staticmethod
    def create_intake(db: Session, intake_data: IntakeCreate, current_user_id: int) -> IntakeResponse:
        """Create a new intake record."""
        # Verify that the dish exists
        dish = db.query(Dish).filter(Dish.id == intake_data.dish_id).first()
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dish not found"
            )
        
        # Create intake with user as owner
        db_intake = Intake(
            user_id=current_user_id,
            **intake_data.model_dump()
        )
        
        db.add(db_intake)
        db.commit()
        db.refresh(db_intake)
        
        return IntakeResponse.model_validate(db_intake)

    @staticmethod
    def get_intake_by_id(db: Session, intake_id: int, current_user_id: int) -> Optional[IntakeResponse]:
        """Get an intake by its ID (only for the current user)."""
        intake = db.query(Intake).filter(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        ).first()
        
        if not intake:
            return None
        
        return IntakeResponse.model_validate(intake)

    @staticmethod
    def get_user_intakes(
        db: Session, 
        current_user_id: int,
        page: int = 1, 
        page_size: int = 20
    ) -> IntakeListResponse:
        """Get all intakes for the current user with pagination."""
        query = db.query(Intake).filter(Intake.user_id == current_user_id)
        
        # Order by intake_time descending (most recent first)
        query = query.order_by(Intake.intake_time.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        intakes = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        intake_items = [IntakeListItem.model_validate(intake) for intake in intakes]
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def get_intakes_by_period(
        db: Session,
        current_user_id: int,
        start_time: datetime,
        end_time: datetime,
        page: int = 1,
        page_size: int = 20
    ) -> IntakeListResponse:
        """Get intakes for the current user between specific date/time periods."""
        # Validate time period
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )
        
        query = db.query(Intake).filter(
            and_(
                Intake.user_id == current_user_id,
                Intake.intake_time >= start_time,
                Intake.intake_time <= end_time
            )
        )
        
        # Order by intake_time ascending for period queries
        query = query.order_by(Intake.intake_time.asc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        intakes = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format
        intake_items = [IntakeListItem.model_validate(intake) for intake in intakes]
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_intake(
        db: Session, 
        intake_id: int, 
        intake_update: IntakeUpdate, 
        current_user_id: int
    ) -> Optional[IntakeResponse]:
        """Update an existing intake (only for the current user)."""
        intake = db.query(Intake).filter(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        ).first()
        
        if not intake:
            return None
        
        # If updating dish_id, verify the new dish exists
        update_data = intake_update.model_dump(exclude_unset=True)
        if "dish_id" in update_data:
            dish = db.query(Dish).filter(Dish.id == update_data["dish_id"]).first()
            if not dish:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dish not found"
                )
        
        # Update only provided fields
        for field, value in update_data.items():
            setattr(intake, field, value)
        
        db.commit()
        db.refresh(intake)
        
        return IntakeResponse.model_validate(intake)

    @staticmethod
    def delete_intake(db: Session, intake_id: int, current_user_id: int) -> bool:
        """Delete an intake (only for the current user)."""
        intake = db.query(Intake).filter(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        ).first()
        
        if not intake:
            return False
        
        db.delete(intake)
        db.commit()
        
        return True

    @staticmethod
    def get_today_intakes(db: Session, current_user_id: int) -> IntakeListResponse:
        """Get all intakes for today for the current user."""
        from datetime import date, time, datetime, timezone
        
        # Get today's start and end
        today = date.today()
        start_of_day = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)
        
        return IntakeService.get_intakes_by_period(
            db=db,
            current_user_id=current_user_id,
            start_time=start_of_day,
            end_time=end_of_day,
            page=1,
            page_size=100  # Get all today's intakes without pagination
        ) 