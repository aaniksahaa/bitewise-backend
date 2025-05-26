from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class DishBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the dish")
    description: Optional[str] = Field(None, description="Description of the dish")
    cuisine: Optional[str] = Field(None, max_length=50, description="Cuisine type")
    cooking_steps: Optional[List[str]] = Field(None, description="List of cooking steps")
    prep_time_minutes: Optional[int] = Field(None, ge=0, description="Preparation time in minutes")
    cook_time_minutes: Optional[int] = Field(None, ge=0, description="Cooking time in minutes")
    image_urls: Optional[List[str]] = Field(None, description="List of image URLs")
    servings: Optional[int] = Field(None, ge=1, description="Number of servings")


class DishCreate(DishBase):
    """Schema for creating a new dish"""
    # Nutritional information (optional for create)
    calories: Optional[Decimal] = Field(None, ge=0, description="Calories per serving")
    protein_g: Optional[Decimal] = Field(None, ge=0, description="Protein in grams")
    carbs_g: Optional[Decimal] = Field(None, ge=0, description="Carbohydrates in grams")
    fats_g: Optional[Decimal] = Field(None, ge=0, description="Fats in grams")
    sat_fats_g: Optional[Decimal] = Field(None, ge=0, description="Saturated fats in grams")
    unsat_fats_g: Optional[Decimal] = Field(None, ge=0, description="Unsaturated fats in grams")
    trans_fats_g: Optional[Decimal] = Field(None, ge=0, description="Trans fats in grams")
    fiber_g: Optional[Decimal] = Field(None, ge=0, description="Fiber in grams")
    sugar_g: Optional[Decimal] = Field(None, ge=0, description="Sugar in grams")
    calcium_mg: Optional[Decimal] = Field(None, ge=0, description="Calcium in milligrams")
    iron_mg: Optional[Decimal] = Field(None, ge=0, description="Iron in milligrams")
    potassium_mg: Optional[Decimal] = Field(None, ge=0, description="Potassium in milligrams")
    sodium_mg: Optional[Decimal] = Field(None, ge=0, description="Sodium in milligrams")
    zinc_mg: Optional[Decimal] = Field(None, ge=0, description="Zinc in milligrams")
    magnesium_mg: Optional[Decimal] = Field(None, ge=0, description="Magnesium in milligrams")
    vit_a_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin A in micrograms")
    vit_b1_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B1 in milligrams")
    vit_b2_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B2 in milligrams")
    vit_b3_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B3 in milligrams")
    vit_b5_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B5 in milligrams")
    vit_b6_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B6 in milligrams")
    vit_b9_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B9 in micrograms")
    vit_b12_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B12 in micrograms")
    vit_c_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin C in milligrams")
    vit_d_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin D in micrograms")
    vit_e_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin E in milligrams")
    vit_k_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin K in micrograms")


class DishUpdate(BaseModel):
    """Schema for updating an existing dish"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the dish")
    description: Optional[str] = Field(None, description="Description of the dish")
    cuisine: Optional[str] = Field(None, max_length=50, description="Cuisine type")
    cooking_steps: Optional[List[str]] = Field(None, description="List of cooking steps")
    prep_time_minutes: Optional[int] = Field(None, ge=0, description="Preparation time in minutes")
    cook_time_minutes: Optional[int] = Field(None, ge=0, description="Cooking time in minutes")
    image_urls: Optional[List[str]] = Field(None, description="List of image URLs")
    servings: Optional[int] = Field(None, ge=1, description="Number of servings")
    # Nutritional information
    calories: Optional[Decimal] = Field(None, ge=0, description="Calories per serving")
    protein_g: Optional[Decimal] = Field(None, ge=0, description="Protein in grams")
    carbs_g: Optional[Decimal] = Field(None, ge=0, description="Carbohydrates in grams")
    fats_g: Optional[Decimal] = Field(None, ge=0, description="Fats in grams")
    sat_fats_g: Optional[Decimal] = Field(None, ge=0, description="Saturated fats in grams")
    unsat_fats_g: Optional[Decimal] = Field(None, ge=0, description="Unsaturated fats in grams")
    trans_fats_g: Optional[Decimal] = Field(None, ge=0, description="Trans fats in grams")
    fiber_g: Optional[Decimal] = Field(None, ge=0, description="Fiber in grams")
    sugar_g: Optional[Decimal] = Field(None, ge=0, description="Sugar in grams")
    calcium_mg: Optional[Decimal] = Field(None, ge=0, description="Calcium in milligrams")
    iron_mg: Optional[Decimal] = Field(None, ge=0, description="Iron in milligrams")
    potassium_mg: Optional[Decimal] = Field(None, ge=0, description="Potassium in milligrams")
    sodium_mg: Optional[Decimal] = Field(None, ge=0, description="Sodium in milligrams")
    zinc_mg: Optional[Decimal] = Field(None, ge=0, description="Zinc in milligrams")
    magnesium_mg: Optional[Decimal] = Field(None, ge=0, description="Magnesium in milligrams")
    vit_a_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin A in micrograms")
    vit_b1_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B1 in milligrams")
    vit_b2_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B2 in milligrams")
    vit_b3_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B3 in milligrams")
    vit_b5_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B5 in milligrams")
    vit_b6_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B6 in milligrams")
    vit_b9_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B9 in micrograms")
    vit_b12_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin B12 in micrograms")
    vit_c_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin C in milligrams")
    vit_d_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin D in micrograms")
    vit_e_mg: Optional[Decimal] = Field(None, ge=0, description="Vitamin E in milligrams")
    vit_k_mcg: Optional[Decimal] = Field(None, ge=0, description="Vitamin K in micrograms")


class DishResponse(DishBase):
    """Schema for dish response with full details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Nutritional information
    calories: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fats_g: Optional[Decimal] = None
    sat_fats_g: Optional[Decimal] = None
    unsat_fats_g: Optional[Decimal] = None
    trans_fats_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    calcium_mg: Optional[Decimal] = None
    iron_mg: Optional[Decimal] = None
    potassium_mg: Optional[Decimal] = None
    sodium_mg: Optional[Decimal] = None
    zinc_mg: Optional[Decimal] = None
    magnesium_mg: Optional[Decimal] = None
    vit_a_mcg: Optional[Decimal] = None
    vit_b1_mg: Optional[Decimal] = None
    vit_b2_mg: Optional[Decimal] = None
    vit_b3_mg: Optional[Decimal] = None
    vit_b5_mg: Optional[Decimal] = None
    vit_b6_mg: Optional[Decimal] = None
    vit_b9_mcg: Optional[Decimal] = None
    vit_b12_mcg: Optional[Decimal] = None
    vit_c_mg: Optional[Decimal] = None
    vit_d_mcg: Optional[Decimal] = None
    vit_e_mg: Optional[Decimal] = None
    vit_k_mcg: Optional[Decimal] = None


class DishListItem(BaseModel):
    """Schema for dish items in lists (lighter version)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    cook_time_minutes: Optional[int] = None
    servings: Optional[int] = None
    image_urls: Optional[List[str]] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    
    # Key nutritional info for lists
    calories: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fats_g: Optional[Decimal] = None


class DishListResponse(BaseModel):
    """Schema for paginated list of dishes"""
    dishes: List[DishListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int 