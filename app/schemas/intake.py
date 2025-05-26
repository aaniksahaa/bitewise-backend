from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class IntakeBase(BaseModel):
    dish_id: int = Field(..., description="ID of the dish being consumed")
    intake_time: datetime = Field(..., description="When the dish was consumed")
    portion_size: Optional[Decimal] = Field(1.0, ge=0.1, le=10.0, description="Portion size relative to dish serving")
    water_ml: Optional[int] = Field(None, ge=0, le=5000, description="Water intake in milliliters")


class IntakeCreate(IntakeBase):
    """Schema for creating a new intake record"""
    pass


class IntakeUpdate(BaseModel):
    """Schema for updating an existing intake record"""
    dish_id: Optional[int] = Field(None, description="ID of the dish being consumed")
    intake_time: Optional[datetime] = Field(None, description="When the dish was consumed")
    portion_size: Optional[Decimal] = Field(None, ge=0.1, le=10.0, description="Portion size relative to dish serving")
    water_ml: Optional[int] = Field(None, ge=0, le=5000, description="Water intake in milliliters")


class NutritionInfo(BaseModel):
    """Nutritional information for an intake"""
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


class IntakeResponse(IntakeBase):
    """Schema for intake response with full details"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    dish_name: str
    dish_cuisine: Optional[str] = None
    nutrition: NutritionInfo
    created_at: datetime


class IntakeListResponse(BaseModel):
    """Schema for list of intakes with pagination"""
    intakes: list[IntakeResponse]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class IntakeSummary(BaseModel):
    """Schema for nutritional summary of intakes"""
    total_calories: Optional[Decimal] = None
    total_protein_g: Optional[Decimal] = None
    total_carbs_g: Optional[Decimal] = None
    total_fats_g: Optional[Decimal] = None
    total_sat_fats_g: Optional[Decimal] = None
    total_unsat_fats_g: Optional[Decimal] = None
    total_trans_fats_g: Optional[Decimal] = None
    total_fiber_g: Optional[Decimal] = None
    total_sugar_g: Optional[Decimal] = None
    total_calcium_mg: Optional[Decimal] = None
    total_iron_mg: Optional[Decimal] = None
    total_potassium_mg: Optional[Decimal] = None
    total_sodium_mg: Optional[Decimal] = None
    total_zinc_mg: Optional[Decimal] = None
    total_magnesium_mg: Optional[Decimal] = None
    total_vit_a_mcg: Optional[Decimal] = None
    total_vit_b1_mg: Optional[Decimal] = None
    total_vit_b2_mg: Optional[Decimal] = None
    total_vit_b3_mg: Optional[Decimal] = None
    total_vit_b5_mg: Optional[Decimal] = None
    total_vit_b6_mg: Optional[Decimal] = None
    total_vit_b9_mcg: Optional[Decimal] = None
    total_vit_b12_mcg: Optional[Decimal] = None
    total_vit_c_mg: Optional[Decimal] = None
    total_vit_d_mcg: Optional[Decimal] = None
    total_vit_e_mg: Optional[Decimal] = None
    total_vit_k_mcg: Optional[Decimal] = None
    total_water_ml: Optional[int] = None
    intake_count: int 