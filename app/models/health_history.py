from sqlalchemy import DECIMAL, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class HealthHistory(Base):
    __tablename__ = "health_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("user_profiles.user_id", ondelete="CASCADE"), nullable=False
    )
    height_cm = Column(DECIMAL(6, 2))
    weight_kg = Column(DECIMAL(6, 2))
    change_timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user_profile = relationship("UserProfile", back_populates="health_history")
