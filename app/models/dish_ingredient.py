from sqlalchemy import Column, BigInteger, DECIMAL, ForeignKey, UniqueConstraint
from app.db.base_class import Base

class DishIngredient(Base):
    __tablename__ = "dish_ingredients"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dish_id = Column(BigInteger, ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False)
    ingredient_id = Column(BigInteger, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint('dish_id', 'ingredient_id', name='uix_dish_ingredient'),
    ) 