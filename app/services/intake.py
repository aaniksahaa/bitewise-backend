from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from fastapi import HTTPException, status
import math
from decimal import Decimal

from app.models.intake import Intake
from app.models.dish import Dish
from app.schemas.intake import (
    IntakeCreate, 
    IntakeCreateByName,
    IntakeUpdate, 
    IntakeResponse, 
    IntakeListItem, 
    IntakeListResponse,
    DishDetail,
    NutritionalSummary
)
from app.utils.search import SearchUtils


class IntakeService:
    @staticmethod
    def _create_intake_response(intake: Intake) -> IntakeResponse:
        """Helper method to create IntakeResponse with dish details."""
        dish_detail = DishDetail.model_validate(intake.dish)
        
        # Create the response manually to include dish details
        return IntakeResponse(
            id=intake.id,
            user_id=intake.user_id,
            dish_id=intake.dish_id,
            intake_time=intake.intake_time,
            portion_size=intake.portion_size,
            water_ml=intake.water_ml,
            created_at=intake.created_at,
            dish=dish_detail
        )
    
    @staticmethod
    def _create_intake_list_item(intake: Intake) -> IntakeListItem:
        """Helper method to create IntakeListItem with dish details."""
        dish_detail = DishDetail.model_validate(intake.dish)
        
        return IntakeListItem(
            id=intake.id,
            dish_id=intake.dish_id,
            intake_time=intake.intake_time,
            portion_size=intake.portion_size,
            water_ml=intake.water_ml,
            created_at=intake.created_at,
            dish=dish_detail
        )

    @staticmethod
    def _calculate_nutritional_summary(intakes: List[Intake]) -> NutritionalSummary:
        """Calculate nutritional totals from a list of intakes."""
        total_calories = Decimal("0")
        total_protein_g = Decimal("0")
        total_carbs_g = Decimal("0")
        total_fats_g = Decimal("0")
        total_fiber_g = Decimal("0")
        total_sugar_g = Decimal("0")
        total_water_ml = 0
        
        for intake in intakes:
            portion_multiplier = intake.portion_size or Decimal("1.0")
            
            # Add water
            if intake.water_ml:
                total_water_ml += intake.water_ml
            
            # Add nutritional values multiplied by portion size
            if intake.dish:
                if intake.dish.calories:
                    total_calories += intake.dish.calories * portion_multiplier
                if intake.dish.protein_g:
                    total_protein_g += intake.dish.protein_g * portion_multiplier
                if intake.dish.carbs_g:
                    total_carbs_g += intake.dish.carbs_g * portion_multiplier
                if intake.dish.fats_g:
                    total_fats_g += intake.dish.fats_g * portion_multiplier
                if intake.dish.fiber_g:
                    total_fiber_g += intake.dish.fiber_g * portion_multiplier
                if intake.dish.sugar_g:
                    total_sugar_g += intake.dish.sugar_g * portion_multiplier
        
        return NutritionalSummary(
            total_calories=total_calories,
            total_protein_g=total_protein_g,
            total_carbs_g=total_carbs_g,
            total_fats_g=total_fats_g,
            total_fiber_g=total_fiber_g,
            total_sugar_g=total_sugar_g,
            total_water_ml=total_water_ml
        )

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
        
        # Load the dish relationship and return response with dish details
        db_intake_with_dish = db.query(Intake).options(joinedload(Intake.dish)).filter(Intake.id == db_intake.id).first()
        return IntakeService._create_intake_response(db_intake_with_dish)

    @staticmethod
    def create_intake_by_name(db: Session, intake_data: IntakeCreateByName, current_user_id: int) -> IntakeResponse:
        """Create a new intake record using dish name."""
        # Use the new fuzzy search to find the best matching dish
        best_dish, score = SearchUtils.find_best_dish_by_name(
            db=db,
            dish_name=intake_data.dish_name
        )
        
        if not best_dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No suitable dish found matching '{intake_data.dish_name}'. Please try a different search term or create the dish first."
            )
        
        # Convert to IntakeCreate using the found dish_id
        intake_create_data = IntakeCreate(
            dish_id=best_dish.id,
            intake_time=intake_data.intake_time,
            portion_size=intake_data.portion_size,
            water_ml=intake_data.water_ml
        )
        
        # Use the existing create_intake method
        return IntakeService.create_intake(
            db=db,
            intake_data=intake_create_data,
            current_user_id=current_user_id
        )

    @staticmethod
    def get_intake_by_id(db: Session, intake_id: int, current_user_id: int) -> Optional[IntakeResponse]:
        """Get an intake by its ID (only for the current user)."""
        intake = db.query(Intake).options(joinedload(Intake.dish)).filter(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        ).first()
        
        if not intake:
            return None
        
        return IntakeService._create_intake_response(intake)

    @staticmethod
    def get_user_intakes(
        db: Session, 
        current_user_id: int,
        page: int = 1, 
        page_size: int = 20
    ) -> IntakeListResponse:
        """Get all intakes for the current user with pagination."""
        query = db.query(Intake).options(joinedload(Intake.dish)).filter(Intake.user_id == current_user_id)
        
        # Order by intake_time descending (most recent first)
        query = query.order_by(Intake.intake_time.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        intakes = query.offset(offset).limit(page_size).all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format with dish details
        intake_items = [IntakeService._create_intake_list_item(intake) for intake in intakes]
        
        # Calculate nutritional summary for the current page
        nutritional_summary = IntakeService._calculate_nutritional_summary(intakes)
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            nutritional_summary=nutritional_summary
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
        
        query = db.query(Intake).options(joinedload(Intake.dish)).filter(
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
        
        # Convert to response format with dish details
        intake_items = [IntakeService._create_intake_list_item(intake) for intake in intakes]
        
        # Calculate nutritional summary for the current page
        nutritional_summary = IntakeService._calculate_nutritional_summary(intakes)
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            nutritional_summary=nutritional_summary
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
        
        # Load the dish relationship and return response with dish details
        intake_with_dish = db.query(Intake).options(joinedload(Intake.dish)).filter(Intake.id == intake.id).first()
        return IntakeService._create_intake_response(intake_with_dish)

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
        """Get all intakes from the last 24 hours for the current user."""
        from datetime import datetime, timezone, timedelta
        
        # Get current time and 24 hours ago
        now = datetime.now(timezone.utc)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        return IntakeService.get_intakes_by_period(
            db=db,
            current_user_id=current_user_id,
            start_time=twenty_four_hours_ago,
            end_time=now,
            page=1,
            page_size=100  # Get all intakes from last 24 hours without pagination
        )

    @staticmethod
    def get_calendar_day_intakes(db: Session, current_user_id: int) -> IntakeListResponse:
        """Get all intakes for the current calendar day (00:00 to 23:59 today) for the current user."""
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
            page_size=100  # Get all today's calendar day intakes without pagination
        ) 