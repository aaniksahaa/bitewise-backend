from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.fitness_plan import FitnessPlan
from app.db.session import get_db
from app.services.auth import get_current_active_user
from app.models.user import User

router = APIRouter()

# Models
class FitnessPlanCreate(BaseModel):
    goal_type: str
    target_weight_kg: Optional[float] = None
    target_calories_per_day: Optional[int] = None
    start_date: date
    end_date: date

class FitnessPlanResponse(BaseModel):
    fitness_plan_id: int
    goal_type: str
    target_weight_kg: float
    target_calories_per_day: int
    start_date: datetime
    end_date: datetime
    suggestions: dict

class FitnessPlansResponse(BaseModel):
    plans: List[FitnessPlanResponse]

class ProgressResponse(BaseModel):
    fitness_plan_id: int
    goal_type: str
    progress: dict

@router.post("/plans", response_model=FitnessPlanResponse)
async def create_fitness_plan(plan: FitnessPlanCreate):
    """Create a fitness plan."""
    return FitnessPlanResponse(
        fitness_plan_id=1,
        goal_type=plan.goal_type,
        target_weight_kg=plan.target_weight_kg,
        target_calories_per_day=plan.target_calories_per_day,
        start_date=datetime.combine(plan.start_date, datetime.min.time()),
        end_date=datetime.combine(plan.end_date, datetime.min.time()),
        suggestions={
            "daily_meals": [
                {
                    "meal_type": "breakfast",
                    "dish_id": 1,
                    "dish_name": "Oatmeal",
                    "calories": 200
                }
            ]
        }
    )

@router.get("/plans", response_model=FitnessPlansResponse)
async def get_user_fitness_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all fitness plans for the current user."""
    fitness_plans = db.query(FitnessPlan).filter(FitnessPlan.user_id == current_user.id).all()
    
    return FitnessPlansResponse(
        plans=[
            FitnessPlanResponse(
                fitness_plan_id=plan.id,
                goal_type=plan.goal_type,
                target_weight_kg=plan.target_weight_kg,
                target_calories_per_day=plan.target_calories_per_day,
                start_date=datetime.combine(plan.start_date, datetime.min.time()),
                end_date=datetime.combine(plan.end_date, datetime.min.time()),
                suggestions=plan.suggestions or {}
            ) for plan in fitness_plans
        ]
    )

@router.get("/plans/{plan_id}", response_model=FitnessPlanResponse)
async def get_fitness_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific fitness plan for the current user."""
    fitness_plan = db.query(FitnessPlan).filter(
        FitnessPlan.id == plan_id,
        FitnessPlan.user_id == current_user.id
    ).first()
    
    if not fitness_plan:
        raise HTTPException(status_code=404, detail="Fitness plan not found")
    
    return FitnessPlanResponse(
        fitness_plan_id=fitness_plan.id,
        goal_type=fitness_plan.goal_type,
        target_weight_kg=fitness_plan.target_weight_kg,
        target_calories_per_day=fitness_plan.target_calories_per_day,
        start_date=datetime.combine(fitness_plan.start_date, datetime.min.time()),
        end_date=datetime.combine(fitness_plan.end_date, datetime.min.time()),
        suggestions=fitness_plan.suggestions or {}
    )
 
@router.get("/plans/{plan_id}/progress", response_model=ProgressResponse)
async def get_fitness_progress(plan_id: int):
    """Get fitness progress."""
    return ProgressResponse(
        fitness_plan_id=plan_id,
        goal_type="weight_loss",
        progress={
            "days_completed": 5,
            "total_calories_consumed": 8000,
            "target_calories": 10000,
            "calorie_deficit": 2000
        }
    ) 