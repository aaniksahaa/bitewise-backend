from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# Models
class IntakeCreate(BaseModel):
    dish_id: int
    intake_time: datetime
    portion_size: float
    water_ml: Optional[int] = None

class NutritionInfo(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float

class IntakeResponse(BaseModel):
    intake_id: int
    dish_id: int
    dish_name: str
    intake_time: datetime
    portion_size: float
    water_ml: Optional[int] = None
    nutrition: NutritionInfo
    created_at: datetime

class DiarySummary(BaseModel):
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fats_g: float

class DiaryResponse(BaseModel):
    intakes: List[IntakeResponse]
    total_count: int
    summary: DiarySummary

@router.post("/intakes", response_model=IntakeResponse)
async def log_food_intake(intake: IntakeCreate):
    """Log a food intake."""
    return IntakeResponse(
        intake_id=1,
        dish_id=intake.dish_id,
        dish_name="Dummy Dish",
        intake_time=intake.intake_time,
        portion_size=intake.portion_size,
        water_ml=intake.water_ml,
        nutrition=NutritionInfo(
            calories=600.0,
            protein_g=30.0,
            carbs_g=50.0,
            fats_g=20.0
        ),
        created_at=datetime.now()
    )

@router.get("/intakes", response_model=DiaryResponse)
async def get_food_diary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get food diary with nutritional summaries."""
    return DiaryResponse(
        intakes=[
            IntakeResponse(
                intake_id=1,
                dish_id=1,
                dish_name="Dummy Dish",
                intake_time=datetime.now(),
                portion_size=1.0,
                water_ml=500,
                nutrition=NutritionInfo(
                    calories=600.0,
                    protein_g=30.0,
                    carbs_g=50.0,
                    fats_g=20.0
                ),
                created_at=datetime.now()
            )
        ],
        total_count=1,
        summary=DiarySummary(
            total_calories=600.0,
            total_protein_g=30.0,
            total_carbs_g=50.0,
            total_fats_g=20.0
        )
    ) 