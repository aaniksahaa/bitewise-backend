from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, func, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base_class import Base

class LLMModel(Base):
    __tablename__ = "llm_models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    provider_name = Column(String(100), nullable=False)
    model_nickname = Column(String(100))
    cost_per_million_input_tokens = Column(Numeric(10, 4), nullable=False)
    cost_per_million_output_tokens = Column(Numeric(10, 4), nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('model_name', 'provider_name', name='uix_model_provider'),
    ) 