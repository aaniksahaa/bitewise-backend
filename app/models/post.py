from sqlalchemy import Column, BigInteger, ForeignKey, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import ARRAY
from app.db.base_class import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    dish_id = Column(BigInteger, ForeignKey("dishes.id", ondelete="SET NULL"), nullable=True)
    tags = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 