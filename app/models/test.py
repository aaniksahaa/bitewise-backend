from sqlalchemy import Column, BigInteger, String, Text, Integer, DECIMAL, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.db.base_class import Base

# class Test(Base):
#     __tablename__ = "tests"

#     id = Column(BigInteger, primary_key=True, autoincrement=True)
#     name = Column(String(100), nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Test(Base):
    __tablename__ = "tests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())