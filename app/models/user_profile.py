import enum

from sqlalchemy import (
    ARRAY,
    DECIMAL,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class GenderType(enum.Enum):
    male = "male"
    female = "female"
    other = "other"


class CookingSkillLevelType(enum.Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    first_name = Column(String(50))
    last_name = Column(String(50))
    gender = Column(Enum(GenderType, name="gender_type"), nullable=False)
    height_cm = Column(DECIMAL(6, 2), nullable=False)
    weight_kg = Column(DECIMAL(6, 2), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    location_city = Column(String(100))
    location_country = Column(String(100))
    latitude = Column(DECIMAL(9, 6))
    longitude = Column(DECIMAL(9, 6))
    profile_image_url = Column(String(255))
    bio = Column(Text)
    dietary_restrictions = Column(PG_ARRAY(Text))
    allergies = Column(PG_ARRAY(Text))
    medical_conditions = Column(PG_ARRAY(Text))
    fitness_goals = Column(PG_ARRAY(Text))
    taste_preferences = Column(PG_ARRAY(Text))
    cuisine_interests = Column(PG_ARRAY(Text))
    cooking_skill_level = Column(
        Enum(CookingSkillLevelType, name="cooking_skill_level_type"), default="beginner"
    )
    email_notifications_enabled = Column(Boolean, default=True)
    push_notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="profile")
    health_history = relationship(
        "HealthHistory", back_populates="user_profile", cascade="all, delete-orphan"
    )
