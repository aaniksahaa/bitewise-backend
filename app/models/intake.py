from sqlalchemy import Column, BigInteger, ForeignKey, DECIMAL, Integer, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Intake(Base):
    __tablename__ = "intakes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dish_id = Column(BigInteger, ForeignKey("dishes.id", ondelete="RESTRICT"), nullable=False)
    intake_time = Column(DateTime(timezone=True), nullable=False)
    portion_size = Column(DECIMAL(5, 2), default=1.0)
    water_ml = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to get dish details
    dish = relationship("Dish", foreign_keys=[dish_id]) 