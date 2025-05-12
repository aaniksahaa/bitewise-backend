from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

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
    start_date: datetime
    end_date: datetime
    suggestions: dict

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