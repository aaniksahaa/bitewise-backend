from sqlalchemy import Column, BigInteger, ForeignKey, Text, Boolean, Integer, DateTime, func, String, JSON, CheckConstraint
from app.db.base_class import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_user_message = Column(Boolean, nullable=False)
    llm_model_id = Column(BigInteger, ForeignKey("llm_models.id", ondelete="SET NULL"), nullable=True)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    parent_message_id = Column(BigInteger, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    message_type = Column(String(50), nullable=False, default="text")
    attachments = Column(JSON)
    reactions = Column(JSON)
    status = Column(String(50), nullable=False, default="sent")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSON)

    __table_args__ = (
        CheckConstraint("message_type IN ('text', 'image', 'file', 'system')", name="valid_message_type"),
        CheckConstraint("status IN ('sent', 'delivered', 'read', 'edited', 'deleted')", name="valid_status"),
    ) 