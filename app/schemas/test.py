from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class TestBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Name of the test")

class TestCreate(TestBase):
    pass 

class TestUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the test")

class TestResponse(TestBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 


class TestListItem(BaseModel):
    id: int
    name: str 
    created_at: datetime

    class Config:
        from_attributes = True 


class TestListResponse(BaseModel):
    tests: list[TestListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        from_attributes = True 