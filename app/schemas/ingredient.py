from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the ingredient")
    serving_size: Decimal = Field(..., ge=0, description="Default serving size")
    image_url: Optional[str] = Field(None, description="Image URL for the ingredient")


class IngredientCreate(IngredientBase):
    """Schema for creating a new ingredient"""
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


class IngredientResponse(IngredientBase):
    """Schema for ingredient response with full details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    
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


class IngredientListItem(BaseModel):
    """Schema for ingredient items in lists (lighter version)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    serving_size: Decimal
    image_url: Optional[str] = None
    
    # Key nutritional info for lists
    calories: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fats_g: Optional[Decimal] = None


class IngredientListResponse(BaseModel):
    """Schema for paginated list of ingredients"""
    ingredients: List[IngredientListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class DishIngredientResponse(BaseModel):
    """Schema for dish-ingredient relationship"""
    model_config = ConfigDict(from_attributes=True)
    
    ingredient: IngredientResponse
    quantity: Decimal 