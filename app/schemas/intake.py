from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class IntakeBase(BaseModel):
    """Base schema for intake operations."""
    dish_id: int = Field(..., description="ID of the dish consumed")
    intake_time: datetime = Field(..., description="Time when the dish was consumed")
    portion_size: Optional[Decimal] = Field(default=Decimal("1.0"), description="Portion size multiplier")
    water_ml: Optional[int] = Field(default=None, description="Water consumed in milliliters")


class IntakeCreate(IntakeBase):
    """Schema for creating a new intake."""
    pass


class IntakeUpdate(BaseModel):
    """Schema for updating an intake."""
    dish_id: Optional[int] = Field(default=None, description="ID of the dish consumed")
    intake_time: Optional[datetime] = Field(default=None, description="Time when the dish was consumed")
    portion_size: Optional[Decimal] = Field(default=None, description="Portion size multiplier")
    water_ml: Optional[int] = Field(default=None, description="Water consumed in milliliters")


class IntakeResponse(IntakeBase):
    """Schema for intake response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    created_at: datetime


class IntakeListItem(BaseModel):
    """Schema for intake list item."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    dish_id: int
    intake_time: datetime
    portion_size: Decimal
    water_ml: Optional[int]
    created_at: datetime


class IntakeListResponse(BaseModel):
    """Schema for paginated intake list response."""
    intakes: List[IntakeListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class IntakePeriodQuery(BaseModel):
    """Schema for querying intakes between specific periods."""
    start_time: datetime = Field(..., description="Start of the time period")
    end_time: datetime = Field(..., description="End of the time period")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page") 