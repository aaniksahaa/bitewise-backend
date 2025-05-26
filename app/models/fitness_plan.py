from sqlalchemy import Column, BigInteger, ForeignKey, String, DECIMAL, Integer, Date, DateTime, JSON, func
from app.db.base_class import Base

class FitnessPlan(Base):
    __tablename__ = "fitness_plans"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_type = Column(String(50), nullable=False)
    target_weight_kg = Column(DECIMAL(5, 2))
    target_calories_per_day = Column(Integer)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    suggestions = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 