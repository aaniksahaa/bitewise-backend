from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for social login
    is_active = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    oauth_provider = Column(String, nullable=True)  # google, apple, etc.
    oauth_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile = relationship("UserProfile", uselist=False, back_populates="user") 