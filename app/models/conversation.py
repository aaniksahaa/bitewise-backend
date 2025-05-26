from sqlalchemy import Column, BigInteger, ForeignKey, String, DateTime, func, JSON, CheckConstraint
from app.db.base_class import Base

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255))
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    extra_data = Column(JSON)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived', 'deleted')", name="valid_status"),
    ) 