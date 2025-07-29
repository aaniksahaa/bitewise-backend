import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """Base class for all database models."""
    
    id: Any
    created_at: datetime
    updated_at: datetime
    __name__: str
    
    # Generate tablename automatically
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate database table name automatically."""
        return cls.__name__.lower()
    
    # Common columns for all models
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    # datetime.utcnow is deprecated, use datetime.now(timezone.utc) instead
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)) 