from typing import Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func
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
from app.utils.logger import intake_logger


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
        """Create a new intake record with detailed logging"""
        intake_logger.info(f"Creating intake for user {current_user_id}", "CREATE",
                         dish_id=intake_data.dish_id, portion_size=intake_data.portion_size)
        
        try:
            # Verify dish exists
            dish = db.query(Dish).filter(Dish.id == intake_data.dish_id).first()
            if not dish:
                error_msg = f"Dish with ID {intake_data.dish_id} not found"
                intake_logger.error(error_msg, "CREATE", dish_id=intake_data.dish_id)
                raise ValueError(error_msg)
            
            intake_logger.debug(f"Found dish: '{dish.name}'", "CREATE", 
                              dish_id=dish.id, calories=dish.calories)
            
            # Create intake record
            db_intake = Intake(
                user_id=current_user_id,
                dish_id=intake_data.dish_id,
                portion_size=intake_data.portion_size,
                intake_time=intake_data.intake_time,
                water_ml=intake_data.water_ml
            )
            
            intake_logger.debug("Adding intake to database session", "CREATE",
                              user_id=current_user_id, dish_name=dish.name)
            
            db.add(db_intake)
            
            intake_logger.debug("Committing intake to database", "CREATE")
            db.commit()
            
            intake_logger.debug("Refreshing intake from database", "CREATE")
            db.refresh(db_intake)
            
            # Verify the intake was saved
            if db_intake.id:
                calories = dish.calories * intake_data.portion_size if dish.calories else None
                intake_logger.success(f"✅ Intake created successfully", "CREATE",
                                    intake_id=db_intake.id, dish_name=dish.name, 
                                    user_id=current_user_id, calories=calories)
                
                # Double-check by querying it back
                verification = db.query(Intake).filter(Intake.id == db_intake.id).first()
                if verification:
                    intake_logger.success("✓ Intake verified in database", "CREATE",
                                        intake_id=db_intake.id)
                else:
                    intake_logger.error("✗ CRITICAL: Intake not found after commit!", "CREATE",
                                      intake_id=db_intake.id)
            else:
                intake_logger.error("✗ CRITICAL: Intake created but has no ID!", "CREATE")
            
            return IntakeService._create_intake_response(db_intake)
            
        except Exception as e:
            intake_logger.error(f"Failed to create intake: {str(e)}", "CREATE",
                              user_id=current_user_id, dish_id=intake_data.dish_id,
                              error=str(e))
            db.rollback()
            raise

    @staticmethod
    def create_intake_by_name(db: Session, intake_data: IntakeCreateByName, current_user_id: int) -> IntakeResponse:
        """Create a new intake record by dish name with detailed logging"""
        
        # Start intake process with clear banner
        intake_logger.section_start("Intake Logging", "PROCESS")
        intake_logger.info(f"Creating intake by name for user {current_user_id}: '{intake_data.dish_name}'", 
                         "REQUEST", portion_size=intake_data.portion_size)
        
        try:
            # Search for dish by name (case-insensitive)
            intake_logger.separator("┈", 25, "SEARCH")
            intake_logger.debug(f"Searching for dish: '{intake_data.dish_name}'", "SEARCH")
            
            dish = db.query(Dish).filter(
                func.lower(Dish.name) == func.lower(intake_data.dish_name.strip())
            ).first()
            
            if not dish:
                # Try partial match if exact match fails
                intake_logger.debug(f"Exact match failed, trying partial match", "SEARCH")
                dish = db.query(Dish).filter(
                    Dish.name.ilike(f"%{intake_data.dish_name.strip()}%")
                ).first()
            
            if not dish:
                error_msg = f"Dish '{intake_data.dish_name}' not found in database"
                intake_logger.error(error_msg, "SEARCH", dish_name=intake_data.dish_name)
                intake_logger.section_end("Intake Logging", "PROCESS", success=False)
                raise ValueError(error_msg)
            
            intake_logger.success(f"Found dish: '{dish.name}' (ID: {dish.id})", "SEARCH",
                                dish_id=dish.id, calories=dish.calories)
            
            # Create IntakeCreate object
            intake_create = IntakeCreate(
                dish_id=dish.id,
                portion_size=intake_data.portion_size,
                intake_time=intake_data.intake_time,
                water_ml=intake_data.water_ml
            )
            
            intake_logger.separator("┈", 25, "DATABASE")
            intake_logger.debug("Converting to IntakeCreate and calling create_intake", "DATABASE")
            
            # Use the regular create_intake method
            result = IntakeService.create_intake(db, intake_create, current_user_id)
            
            intake_logger.success(f"✅ Intake by name completed", "PROCESS",
                                intake_id=result.id, dish_name=dish.name)
            
            intake_logger.section_end("Intake Logging", "PROCESS", success=True)
            return result
            
        except Exception as e:
            intake_logger.error(f"Failed to create intake by name: {str(e)}", "ERROR",
                              user_id=current_user_id, dish_name=intake_data.dish_name,
                              error=str(e))
            intake_logger.section_end("Intake Logging", "PROCESS", success=False)
            raise

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

    @staticmethod
    def get_daily_nutrition_summary(db: Session, user_id: int, target_date: date) -> dict:
        """Get daily nutrition summary for a user with logging"""
        intake_logger.debug(f"Calculating daily nutrition for user {user_id} on {target_date}", "SUMMARY")
        
        try:
            # Get all intakes for the specified date
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            intakes = db.query(Intake).filter(
                and_(
                    Intake.user_id == user_id,
                    Intake.intake_time >= start_datetime,
                    Intake.intake_time <= end_datetime
                )
            ).all()
            
            intake_logger.debug(f"Found {len(intakes)} intakes for summary", "SUMMARY", count=len(intakes))
            
            total_calories = 0.0
            total_protein = 0.0
            total_carbs = 0.0
            total_fat = 0.0
            total_fiber = 0.0
            total_water = 0.0
            
            for intake in intakes:
                if intake.dish:
                    multiplier = float(intake.portion_size)
                    
                    if intake.dish.calories:
                        total_calories += float(intake.dish.calories) * multiplier
                    if intake.dish.protein_g:
                        total_protein += float(intake.dish.protein_g) * multiplier
                    if intake.dish.carbs_g:
                        total_carbs += float(intake.dish.carbs_g) * multiplier
                    if intake.dish.fats_g:
                        total_fat += float(intake.dish.fats_g) * multiplier
                    if intake.dish.fiber_g:
                        total_fiber += float(intake.dish.fiber_g) * multiplier
                
                if intake.water_ml:
                    total_water += float(intake.water_ml)
            
            summary = {
                "date": target_date.isoformat(),
                "total_calories": round(total_calories, 2),
                "total_protein_g": round(total_protein, 2),
                "total_carbs_g": round(total_carbs, 2),
                "total_fat_g": round(total_fat, 2),
                "total_fiber_g": round(total_fiber, 2),
                "total_water_ml": round(total_water, 2),
                "intake_count": len(intakes)
            }
            
            intake_logger.success(f"Daily summary calculated", "SUMMARY",
                                calories=summary["total_calories"], 
                                intake_count=summary["intake_count"])
            
            return summary
            
        except Exception as e:
            intake_logger.error(f"Failed to calculate daily summary: {str(e)}", "SUMMARY",
                              user_id=user_id, date=target_date, error=str(e))
            raise

# Legacy function for backward compatibility
def log_intake(db: Session, user_id: int, dish_id: int, quantity: float) -> dict:
    """Legacy function for logging intake - maintained for backward compatibility"""
    intake_logger.info(f"Legacy log_intake called", "LEGACY",
                     user_id=user_id, dish_id=dish_id, quantity=quantity)
    
    try:
        # Convert to new format
        intake_data = IntakeCreate(
            dish_id=dish_id,
            portion_size=quantity,
            intake_time=datetime.now(),
            water_ml=None
        )
        
        result = IntakeService.create_intake(db, intake_data, user_id)
        
        intake_logger.success(f"Legacy intake logged successfully", "LEGACY",
                            intake_id=result.id)
        
        return {
            "success": True,
            "intake_id": result.id,
            "message": f"Successfully logged {quantity} serving(s)"
        }
        
    except Exception as e:
        intake_logger.error(f"Legacy intake logging failed: {str(e)}", "LEGACY",
                          user_id=user_id, dish_id=dish_id, error=str(e))
        return {
            "success": False,
            "error": str(e)
        } 