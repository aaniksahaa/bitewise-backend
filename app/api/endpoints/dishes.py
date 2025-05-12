from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# Models
class IngredientInfo(BaseModel):
    ingredient_id: int
    name: str
    quantity: float
    unit_type: str
    nutrition: dict

class DishCreate(BaseModel):
    name: str
    description: Optional[str] = None
    recipe_text: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    ingredients: List[dict]

class DishResponse(BaseModel):
    dish_id: int
    name: str
    description: Optional[str] = None
    recipe_text: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    ingredients: List[IngredientInfo]
    total_nutrition: dict

class DishListResponse(BaseModel):
    dishes: List[dict]
    total_count: int

@router.post("/dishes", response_model=DishResponse)
async def create_dish(dish: DishCreate):
    """Create a new dish."""
    return DishResponse(
        dish_id=1,
        name=dish.name,
        description=dish.description,
        recipe_text=dish.recipe_text,
        prep_time_minutes=dish.prep_time_minutes,
        cook_time_minutes=dish.cook_time_minutes,
        created_by_user_id=1,
        created_at=datetime.now(),
        ingredients=[
            IngredientInfo(
                ingredient_id=1,
                name="Dummy Ingredient",
                quantity=100.0,
                unit_type="gram",
                nutrition={
                    "calories": 100.0,
                    "protein_g": 10.0,
                    "carbs_g": 20.0,
                    "fats_g": 5.0
                }
            )
        ],
        total_nutrition={
            "calories": 100.0,
            "protein_g": 10.0,
            "carbs_g": 20.0,
            "fats_g": 5.0
        }
    )

@router.get("/dishes/{dish_id}", response_model=DishResponse)
async def get_dish(dish_id: int):
    """Get dish details."""
    return DishResponse(
        dish_id=dish_id,
        name="Dummy Dish",
        description="A delicious dummy dish",
        recipe_text="Mix ingredients and cook",
        prep_time_minutes=15,
        cook_time_minutes=30,
        created_by_user_id=1,
        created_at=datetime.now(),
        ingredients=[
            IngredientInfo(
                ingredient_id=1,
                name="Dummy Ingredient",
                quantity=100.0,
                unit_type="gram",
                nutrition={
                    "calories": 100.0,
                    "protein_g": 10.0,
                    "carbs_g": 20.0,
                    "fats_g": 5.0
                }
            )
        ],
        total_nutrition={
            "calories": 100.0,
            "protein_g": 10.0,
            "carbs_g": 20.0,
            "fats_g": 5.0
        }
    )

@router.get("/dishes", response_model=DishListResponse)
async def search_dishes(
    search_query: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Search dishes."""
    return DishListResponse(
        dishes=[
            {
                "dish_id": 1,
                "name": "Dummy Dish",
                "description": "A delicious dummy dish",
                "prep_time_minutes": 15,
                "cook_time_minutes": 30,
                "created_by_user_id": 1,
                "created_at": datetime.now(),
                "ingredient_names": ["Dummy Ingredient 1", "Dummy Ingredient 2"],
                "total_nutrition": {
                    "calories": 100.0,
                    "protein_g": 10.0,
                    "carbs_g": 20.0,
                    "fats_g": 5.0
                }
            }
        ],
        total_count=1
    ) 