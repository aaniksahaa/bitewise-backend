from datetime import datetime, date
from typing import List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from fastapi import HTTPException, status

from app.models.intake import Intake
from app.models.dish import Dish
from app.models.user import User
from app.schemas.intake import (
    IntakeCreate, 
    IntakeUpdate, 
    IntakeResponse, 
    IntakeListResponse,
    IntakeSummary,
    NutritionInfo
)


class IntakeService:
    """Service class for intake-related operations"""

    @staticmethod
    def create_intake(db: Session, intake_data: IntakeCreate, user_id: int) -> Intake:
        """Create a new food intake record"""
        
        # Verify dish exists
        dish = db.query(Dish).filter(Dish.id == intake_data.dish_id).first()
        if not dish:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dish not found"
            )
        
        # Create intake record
        intake = Intake(
            user_id=user_id,
            dish_id=intake_data.dish_id,
            intake_time=intake_data.intake_time,
            portion_size=intake_data.portion_size or Decimal('1.0'),
            water_ml=intake_data.water_ml
        )
        
        db.add(intake)
        db.commit()
        db.refresh(intake)
        
        return intake

    @staticmethod
    def get_intake_by_id(db: Session, intake_id: int, user_id: int) -> Optional[Intake]:
        """Get a specific intake by ID for the authenticated user"""
        return db.query(Intake).filter(
            and_(Intake.id == intake_id, Intake.user_id == user_id)
        ).first()

    @staticmethod
    def get_intakes(
        db: Session, 
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[Intake], int]:
        """Get intakes for a user with optional date filtering and pagination"""
        
        query = db.query(Intake).filter(Intake.user_id == user_id)
        
        # Apply date filters if provided
        if start_date:
            query = query.filter(func.date(Intake.intake_time) >= start_date)
        if end_date:
            query = query.filter(func.date(Intake.intake_time) <= end_date)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        intakes = query.order_by(desc(Intake.intake_time)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return intakes, total_count

    @staticmethod
    def update_intake(
        db: Session, 
        intake_id: int, 
        intake_data: IntakeUpdate, 
        user_id: int
    ) -> Optional[Intake]:
        """Update an existing intake record"""
        
        intake = IntakeService.get_intake_by_id(db, intake_id, user_id)
        if not intake:
            return None
        
        # If dish_id is being updated, verify the new dish exists
        if intake_data.dish_id is not None:
            dish = db.query(Dish).filter(Dish.id == intake_data.dish_id).first()
            if not dish:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Dish not found"
                )
            intake.dish_id = intake_data.dish_id
        
        # Update other fields if provided
        if intake_data.intake_time is not None:
            intake.intake_time = intake_data.intake_time
        if intake_data.portion_size is not None:
            intake.portion_size = intake_data.portion_size
        if intake_data.water_ml is not None:
            intake.water_ml = intake_data.water_ml
        
        db.commit()
        db.refresh(intake)
        
        return intake

    @staticmethod
    def delete_intake(db: Session, intake_id: int, user_id: int) -> bool:
        """Delete an intake record"""
        
        intake = IntakeService.get_intake_by_id(db, intake_id, user_id)
        if not intake:
            return False
        
        db.delete(intake)
        db.commit()
        
        return True

    @staticmethod
    def calculate_nutrition(dish: Dish, portion_size: Decimal) -> NutritionInfo:
        """Calculate nutritional information for an intake based on dish and portion size"""
        
        def safe_multiply(value: Optional[Decimal], multiplier: Decimal) -> Optional[Decimal]:
            return value * multiplier if value is not None else None
        
        return NutritionInfo(
            calories=safe_multiply(dish.calories, portion_size),
            protein_g=safe_multiply(dish.protein_g, portion_size),
            carbs_g=safe_multiply(dish.carbs_g, portion_size),
            fats_g=safe_multiply(dish.fats_g, portion_size),
            sat_fats_g=safe_multiply(dish.sat_fats_g, portion_size),
            unsat_fats_g=safe_multiply(dish.unsat_fats_g, portion_size),
            trans_fats_g=safe_multiply(dish.trans_fats_g, portion_size),
            fiber_g=safe_multiply(dish.fiber_g, portion_size),
            sugar_g=safe_multiply(dish.sugar_g, portion_size),
            calcium_mg=safe_multiply(dish.calcium_mg, portion_size),
            iron_mg=safe_multiply(dish.iron_mg, portion_size),
            potassium_mg=safe_multiply(dish.potassium_mg, portion_size),
            sodium_mg=safe_multiply(dish.sodium_mg, portion_size),
            zinc_mg=safe_multiply(dish.zinc_mg, portion_size),
            magnesium_mg=safe_multiply(dish.magnesium_mg, portion_size),
            vit_a_mcg=safe_multiply(dish.vit_a_mcg, portion_size),
            vit_b1_mg=safe_multiply(dish.vit_b1_mg, portion_size),
            vit_b2_mg=safe_multiply(dish.vit_b2_mg, portion_size),
            vit_b3_mg=safe_multiply(dish.vit_b3_mg, portion_size),
            vit_b5_mg=safe_multiply(dish.vit_b5_mg, portion_size),
            vit_b6_mg=safe_multiply(dish.vit_b6_mg, portion_size),
            vit_b9_mcg=safe_multiply(dish.vit_b9_mcg, portion_size),
            vit_b12_mcg=safe_multiply(dish.vit_b12_mcg, portion_size),
            vit_c_mg=safe_multiply(dish.vit_c_mg, portion_size),
            vit_d_mcg=safe_multiply(dish.vit_d_mcg, portion_size),
            vit_e_mg=safe_multiply(dish.vit_e_mg, portion_size),
            vit_k_mcg=safe_multiply(dish.vit_k_mcg, portion_size)
        )

    @staticmethod
    def build_intake_response(intake: Intake, dish: Dish) -> IntakeResponse:
        """Build an IntakeResponse from intake and dish data"""
        
        nutrition = IntakeService.calculate_nutrition(dish, intake.portion_size)
        
        return IntakeResponse(
            id=intake.id,
            user_id=intake.user_id,
            dish_id=intake.dish_id,
            dish_name=dish.name,
            dish_cuisine=dish.cuisine,
            intake_time=intake.intake_time,
            portion_size=intake.portion_size,
            water_ml=intake.water_ml,
            nutrition=nutrition,
            created_at=intake.created_at
        )

    @staticmethod
    def get_intake_summary(
        db: Session,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> IntakeSummary:
        """Calculate nutritional summary for user's intakes within date range"""
        
        # Get all intakes for the period
        intakes, _ = IntakeService.get_intakes(
            db, user_id, start_date, end_date, page=1, page_size=10000
        )
        
        # Initialize totals
        summary = IntakeSummary(
            intake_count=len(intakes),
            total_calories=Decimal('0'),
            total_protein_g=Decimal('0'),
            total_carbs_g=Decimal('0'),
            total_fats_g=Decimal('0'),
            total_sat_fats_g=Decimal('0'),
            total_unsat_fats_g=Decimal('0'),
            total_trans_fats_g=Decimal('0'),
            total_fiber_g=Decimal('0'),
            total_sugar_g=Decimal('0'),
            total_calcium_mg=Decimal('0'),
            total_iron_mg=Decimal('0'),
            total_potassium_mg=Decimal('0'),
            total_sodium_mg=Decimal('0'),
            total_zinc_mg=Decimal('0'),
            total_magnesium_mg=Decimal('0'),
            total_vit_a_mcg=Decimal('0'),
            total_vit_b1_mg=Decimal('0'),
            total_vit_b2_mg=Decimal('0'),
            total_vit_b3_mg=Decimal('0'),
            total_vit_b5_mg=Decimal('0'),
            total_vit_b6_mg=Decimal('0'),
            total_vit_b9_mcg=Decimal('0'),
            total_vit_b12_mcg=Decimal('0'),
            total_vit_c_mg=Decimal('0'),
            total_vit_d_mcg=Decimal('0'),
            total_vit_e_mg=Decimal('0'),
            total_vit_k_mcg=Decimal('0'),
            total_water_ml=0
        )
        
        for intake in intakes:
            dish = db.query(Dish).filter(Dish.id == intake.dish_id).first()
            if not dish:
                continue
                
            nutrition = IntakeService.calculate_nutrition(dish, intake.portion_size)
            
            # Add to totals (handling None values)
            def add_to_total(total: Decimal, value: Optional[Decimal]) -> Decimal:
                return total + (value or Decimal('0'))
            
            summary.total_calories = add_to_total(summary.total_calories, nutrition.calories)
            summary.total_protein_g = add_to_total(summary.total_protein_g, nutrition.protein_g)
            summary.total_carbs_g = add_to_total(summary.total_carbs_g, nutrition.carbs_g)
            summary.total_fats_g = add_to_total(summary.total_fats_g, nutrition.fats_g)
            summary.total_sat_fats_g = add_to_total(summary.total_sat_fats_g, nutrition.sat_fats_g)
            summary.total_unsat_fats_g = add_to_total(summary.total_unsat_fats_g, nutrition.unsat_fats_g)
            summary.total_trans_fats_g = add_to_total(summary.total_trans_fats_g, nutrition.trans_fats_g)
            summary.total_fiber_g = add_to_total(summary.total_fiber_g, nutrition.fiber_g)
            summary.total_sugar_g = add_to_total(summary.total_sugar_g, nutrition.sugar_g)
            summary.total_calcium_mg = add_to_total(summary.total_calcium_mg, nutrition.calcium_mg)
            summary.total_iron_mg = add_to_total(summary.total_iron_mg, nutrition.iron_mg)
            summary.total_potassium_mg = add_to_total(summary.total_potassium_mg, nutrition.potassium_mg)
            summary.total_sodium_mg = add_to_total(summary.total_sodium_mg, nutrition.sodium_mg)
            summary.total_zinc_mg = add_to_total(summary.total_zinc_mg, nutrition.zinc_mg)
            summary.total_magnesium_mg = add_to_total(summary.total_magnesium_mg, nutrition.magnesium_mg)
            summary.total_vit_a_mcg = add_to_total(summary.total_vit_a_mcg, nutrition.vit_a_mcg)
            summary.total_vit_b1_mg = add_to_total(summary.total_vit_b1_mg, nutrition.vit_b1_mg)
            summary.total_vit_b2_mg = add_to_total(summary.total_vit_b2_mg, nutrition.vit_b2_mg)
            summary.total_vit_b3_mg = add_to_total(summary.total_vit_b3_mg, nutrition.vit_b3_mg)
            summary.total_vit_b5_mg = add_to_total(summary.total_vit_b5_mg, nutrition.vit_b5_mg)
            summary.total_vit_b6_mg = add_to_total(summary.total_vit_b6_mg, nutrition.vit_b6_mg)
            summary.total_vit_b9_mcg = add_to_total(summary.total_vit_b9_mcg, nutrition.vit_b9_mcg)
            summary.total_vit_b12_mcg = add_to_total(summary.total_vit_b12_mcg, nutrition.vit_b12_mcg)
            summary.total_vit_c_mg = add_to_total(summary.total_vit_c_mg, nutrition.vit_c_mg)
            summary.total_vit_d_mcg = add_to_total(summary.total_vit_d_mcg, nutrition.vit_d_mcg)
            summary.total_vit_e_mg = add_to_total(summary.total_vit_e_mg, nutrition.vit_e_mg)
            summary.total_vit_k_mcg = add_to_total(summary.total_vit_k_mcg, nutrition.vit_k_mcg)
            
            # Add water intake
            if intake.water_ml:
                summary.total_water_ml += intake.water_ml
        
        return summary 