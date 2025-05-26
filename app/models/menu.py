from sqlalchemy import Column, BigInteger, String, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Menu(Base):
    __tablename__ = "menus"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    occasion = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="menus", foreign_keys=[user_id])
    menu_dishes = relationship("MenuDish", back_populates="menu", cascade="all, delete-orphan")

class MenuDish(Base):
    __tablename__ = "menu_dishes"
    
    __table_args__ = (
        UniqueConstraint('menu_id', 'dish_id', name='uix_menu_dish'),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    menu_id = Column(BigInteger, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    dish_id = Column(BigInteger, ForeignKey("dishes.id", ondelete="RESTRICT"), nullable=False)

    # Relationships
    menu = relationship("Menu", back_populates="menu_dishes")
    dish = relationship("Dish", backref="menu_dishes") 