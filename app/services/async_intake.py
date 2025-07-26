"""
Async intake service for managing food intake records.

This service provides async database operations for creating, retrieving,
updating, and deleting intake records, as well as calculating nutritional
summaries and statistics.
"""

from typing import Optional, List, Tuple
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, cast, DateTime, update, delete
from sqlalchemy.orm import selectinload, joinedload
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
from app.services.base import AsyncBaseService
from app.utils.logger import intake_logger


class AsyncIntakeService(AsyncBaseService[Intake, IntakeCreate, IntakeUpdate]):
    """
    Async service for managing intake records with comprehensive CRUD operations,
    nutritional calculations, and period-based queries.
    """
    
    def __init__(self):
        super().__init__(Intake)
    
    @staticmethod
    def _create_intake_response(intake: Intake) -> IntakeResponse:
        """Helper method to create IntakeResponse with dish details."""
        dish_detail = DishDetail.model_validate(intake.dish)
        
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

    async def create_intake(self, db: AsyncSession, intake_data: IntakeCreate, current_user_id: int) -> IntakeResponse:
        """Create a new intake record with detailed logging"""
        intake_logger.info(f"Creating intake for user {current_user_id}", "CREATE",
                         dish_id=intake_data.dish_id, portion_size=intake_data.portion_size)
        
        try:
            # Verify dish exists
            stmt = select(Dish).where(Dish.id == intake_data.dish_id)
            result = await db.execute(stmt)
            dish = result.scalar_one_or_none()
            
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
            await db.commit()
            
            intake_logger.debug("Refreshing intake from database", "CREATE")
            await db.refresh(db_intake)
            
            # Load the dish relationship for response
            stmt_with_dish = select(Intake).options(selectinload(Intake.dish)).where(Intake.id == db_intake.id)
            result = await db.execute(stmt_with_dish)
            db_intake = result.scalar_one()
            
            # Verify the intake was saved
            if db_intake.id:
                calories = dish.calories * intake_data.portion_size if dish.calories else None
                intake_logger.success(f"✅ Intake created successfully", "CREATE",
                                    intake_id=db_intake.id, dish_name=dish.name, 
                                    user_id=current_user_id, calories=calories)
            else:
                intake_logger.error("✗ CRITICAL: Intake created but has no ID!", "CREATE")
            
            return self._create_intake_response(db_intake)
            
        except Exception as e:
            intake_logger.error(f"Failed to create intake: {str(e)}", "CREATE",
                              user_id=current_user_id, dish_id=intake_data.dish_id,
                              error=str(e))
            await db.rollback()
            raise

    async def create_intake_by_name(self, db: AsyncSession, intake_data: IntakeCreateByName, current_user_id: int) -> IntakeResponse:
        """Create a new intake record by dish name with detailed logging"""
        
        # Start intake process with clear banner
        intake_logger.section_start("Intake Logging", "PROCESS")
        intake_logger.info(f"Creating intake by name for user {current_user_id}: '{intake_data.dish_name}'", 
                         "REQUEST", portion_size=intake_data.portion_size)
        
        try:
            # Search for dish by name (case-insensitive)
            intake_logger.separator("┈", 25, "SEARCH")
            intake_logger.debug(f"Searching for dish: '{intake_data.dish_name}'", "SEARCH")
            
            stmt = select(Dish).where(
                func.lower(Dish.name) == func.lower(intake_data.dish_name.strip())
            )
            result = await db.execute(stmt)
            dish = result.scalar_one_or_none()
            
            if not dish:
                # Try partial match if exact match fails
                intake_logger.debug(f"Exact match failed, trying partial match", "SEARCH")
                stmt = select(Dish).where(
                    Dish.name.ilike(f"%{intake_data.dish_name.strip()}%")
                )
                result = await db.execute(stmt)
                dish = result.scalar_one_or_none()
            
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
            result = await self.create_intake(db, intake_create, current_user_id)
            
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

    async def get_intake_by_id(self, db: AsyncSession, intake_id: int, current_user_id: int) -> Optional[IntakeResponse]:
        """Get an intake by its ID (only for the current user)."""
        stmt = (
            select(Intake)
            .options(selectinload(Intake.dish))
            .where(
                and_(
                    Intake.id == intake_id,
                    Intake.user_id == current_user_id
                )
            )
        )
        result = await db.execute(stmt)
        intake = result.scalar_one_or_none()
        
        if not intake:
            return None
        
        return self._create_intake_response(intake)

    async def get_user_intakes(
        self, 
        db: AsyncSession, 
        current_user_id: int,
        page: int = 1, 
        page_size: int = 20
    ) -> IntakeListResponse:
        """Get all intakes for the current user with pagination."""
        intake_logger.info(f"Getting all intakes for user {current_user_id}", "GET", page=page, page_size=page_size)
        
        # Base query with dish relationship
        base_stmt = (
            select(Intake)
            .options(selectinload(Intake.dish))
            .where(Intake.user_id == current_user_id)
            .order_by(Intake.intake_time.desc())
        )
        
        # Get total count
        count_stmt = select(func.count(Intake.id)).where(Intake.user_id == current_user_id)
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = base_stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        intakes = result.scalars().all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format with dish details
        intake_items = [self._create_intake_list_item(intake) for intake in intakes]
        
        # Calculate nutritional summary for the current page
        nutritional_summary = self._calculate_nutritional_summary(intakes)
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            nutritional_summary=nutritional_summary
        )

    async def get_intakes_by_period(
        self,
        db: AsyncSession,
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
        
        # Base query with filters
        base_stmt = (
            select(Intake)
            .options(selectinload(Intake.dish))
            .where(
                and_(
                    Intake.user_id == current_user_id,
                    cast(Intake.intake_time, DateTime) >= start_time,
                    cast(Intake.intake_time, DateTime) <= end_time
                )
            )
            .order_by(Intake.intake_time.asc())
        )
        
        # Get total count for the period
        count_stmt = (
            select(func.count(Intake.id))
            .where(
                and_(
                    Intake.user_id == current_user_id,
                    cast(Intake.intake_time, DateTime) >= start_time,
                    cast(Intake.intake_time, DateTime) <= end_time
                )
            )
        )
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * page_size
        paginated_stmt = base_stmt.offset(offset).limit(page_size)
        result = await db.execute(paginated_stmt)
        intakes = result.scalars().all()
        
        # Calculate total pages
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1
        
        # Convert to response format with dish details
        intake_items = [self._create_intake_list_item(intake) for intake in intakes]
        
        # Calculate nutritional summary for the current page
        nutritional_summary = self._calculate_nutritional_summary(intakes)
        
        return IntakeListResponse(
            intakes=intake_items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            nutritional_summary=nutritional_summary
        )

    async def update_intake(
        self,
        db: AsyncSession, 
        intake_id: int, 
        intake_update: IntakeUpdate, 
        current_user_id: int
    ) -> Optional[IntakeResponse]:
        """Update an existing intake (only for the current user)."""
        # Get the existing intake
        stmt = select(Intake).where(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        )
        result = await db.execute(stmt)
        intake = result.scalar_one_or_none()
        
        if not intake:
            return None
        
        # If updating dish_id, verify the new dish exists
        update_data = intake_update.model_dump(exclude_unset=True)
        if "dish_id" in update_data:
            dish_stmt = select(Dish).where(Dish.id == update_data["dish_id"])
            dish_result = await db.execute(dish_stmt)
            dish = dish_result.scalar_one_or_none()
            if not dish:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dish not found"
                )
        
        # Update only provided fields
        for field, value in update_data.items():
            setattr(intake, field, value)
        
        await db.commit()
        await db.refresh(intake)
        
        # Load the dish relationship and return response with dish details
        stmt_with_dish = (
            select(Intake)
            .options(selectinload(Intake.dish))
            .where(Intake.id == intake.id)
        )
        result = await db.execute(stmt_with_dish)
        intake_with_dish = result.scalar_one()
        
        return self._create_intake_response(intake_with_dish)

    async def delete_intake(self, db: AsyncSession, intake_id: int, current_user_id: int) -> bool:
        """Delete an intake (only for the current user)."""
        stmt = select(Intake).where(
            and_(
                Intake.id == intake_id,
                Intake.user_id == current_user_id
            )
        )
        result = await db.execute(stmt)
        intake = result.scalar_one_or_none()
        
        if not intake:
            return False
        
        await db.delete(intake)
        await db.commit()
        
        return True

    async def get_today_intakes(self, db: AsyncSession, current_user_id: int) -> IntakeListResponse:
        """Get all intakes from the last 24 hours for the current user."""
        # Get current UTC time
        now_utc = datetime.now(timezone.utc)
        
        # Define Dhaka's timezone offset
        dhaka_offset = timedelta(hours=6)
        dhaka_timezone = timezone(dhaka_offset) 
        
        # Convert current UTC time to Dhaka's local time
        now_dhaka = now_utc.astimezone(dhaka_timezone)
        
        # Calculate 24 hours ago in Dhaka's local time
        twenty_four_hours_ago_dhaka = now_dhaka - timedelta(hours=24)
        
        # Strip timezone information to get naive datetimes for comparison
        start_time_naive = twenty_four_hours_ago_dhaka.replace(tzinfo=None)
        end_time_naive = now_dhaka.replace(tzinfo=None)
        
        return await self.get_intakes_by_period(
            db=db,
            current_user_id=current_user_id,
            start_time=start_time_naive,
            end_time=end_time_naive,
            page=1,
            page_size=100  # Get all intakes from last 24 hours without pagination
        )

    async def get_calendar_day_intakes(self, db: AsyncSession, current_user_id: int) -> IntakeListResponse:
        """Get all intakes for the current calendar day (00:00 to 23:59 today) for the current user."""
        from datetime import time
        
        # Get today's start and end
        today = date.today()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)
        
        return await self.get_intakes_by_period(
            db=db,
            current_user_id=current_user_id,
            start_time=start_of_day,
            end_time=end_of_day,
            page=1,
            page_size=100  # Get all today's calendar day intakes without pagination
        )

    async def get_daily_nutrition_summary(self, db: AsyncSession, user_id: int, target_date: date) -> dict:
        """Get daily nutrition summary for a user with logging"""
        intake_logger.debug(f"Calculating daily nutrition for user {user_id} on {target_date}", "SUMMARY")
        
        try:
            # Get all intakes for the specified date
            start_datetime = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            stmt = (
                select(Intake)
                .options(selectinload(Intake.dish))
                .where(
                    and_(
                        Intake.user_id == user_id,
                        cast(Intake.intake_time, DateTime) >= start_datetime,
                        cast(Intake.intake_time, DateTime) <= end_datetime
                    )
                )
            )
            result = await db.execute(stmt)
            intakes = result.scalars().all()
            
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


# Create a singleton instance for use in endpoints
async_intake_service = AsyncIntakeService()


# Legacy function for backward compatibility
async def log_intake_async(db: AsyncSession, user_id: int, dish_id: int, quantity: float) -> dict:
    """Legacy function for logging intake - maintained for backward compatibility"""
    intake_logger.info(f"Legacy log_intake_async called", "LEGACY",
                     user_id=user_id, dish_id=dish_id, quantity=quantity)
    
    try:
        # Convert to new format
        intake_data = IntakeCreate(
            dish_id=dish_id,
            portion_size=quantity,
            intake_time=datetime.now(),
            water_ml=None
        )
        
        result = await async_intake_service.create_intake(db, intake_data, user_id)
        
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