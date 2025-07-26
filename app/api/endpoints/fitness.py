from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.async_session import get_async_db
from app.services.async_auth import AsyncAuthService, get_current_active_user_async
from app.services.async_fitness import AsyncFitnessService
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
    start_date: datetime
    end_date: datetime
    suggestions: dict

class ProgressResponse(BaseModel):
    fitness_plan_id: int
    goal_type: str
    progress: dict

@router.post("/plans", response_model=FitnessPlanResponse)
async def create_fitness_plan(
    plan: FitnessPlanCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Create a fitness plan."""
    fitness_plan = await AsyncFitnessService.create_fitness_plan(
        db=db,
        user_id=current_user.id,
        goal_type=plan.goal_type,
        target_weight_kg=plan.target_weight_kg,
        target_calories_per_day=plan.target_calories_per_day,
        start_date=plan.start_date,
        end_date=plan.end_date
    )
    
    return FitnessPlanResponse(
        fitness_plan_id=fitness_plan.id,
        goal_type=fitness_plan.goal_type,
        start_date=datetime.combine(fitness_plan.start_date, datetime.min.time()),
        end_date=datetime.combine(fitness_plan.end_date, datetime.min.time()),
        suggestions=fitness_plan.suggestions
    )

@router.get("/plans/{plan_id}/progress", response_model=ProgressResponse)
async def get_fitness_progress(
    plan_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get fitness progress."""
    progress = await AsyncFitnessService.get_fitness_progress(
        db=db,
        plan_id=plan_id,
        user_id=current_user.id
    )
    
    if not progress:
        raise HTTPException(status_code=404, detail="Fitness plan not found")
    
    return ProgressResponse(
        fitness_plan_id=progress["fitness_plan_id"],
        goal_type=progress["goal_type"],
        progress=progress
    ) 