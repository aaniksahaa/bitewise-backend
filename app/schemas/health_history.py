from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HealthHistoryBase(BaseModel):
    height_cm: Decimal | None = None
    weight_kg: Decimal | None = None


class HealthHistoryCreate(HealthHistoryBase):
    pass


class HealthHistoryResponse(HealthHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    change_timestamp: datetime
