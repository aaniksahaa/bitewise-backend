from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema for all models."""
    model_config = ConfigDict(from_attributes=True)
    

class BaseResponseSchema(BaseSchema):
    """Base response schema with common fields."""
    id: str
    created_at: datetime
    updated_at: datetime 