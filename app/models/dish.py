from sqlalchemy import Column, BigInteger, String, Text, Integer, DECIMAL, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Dish(Base):
    __tablename__ = "dishes"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    cuisine = Column(String(50))
    created_by_user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cooking_steps = Column(ARRAY(Text))
    prep_time_minutes = Column(Integer)
    cook_time_minutes = Column(Integer)
    image_urls = Column(ARRAY(String(255)))
    servings = Column(Integer)
    calories = Column(DECIMAL(10, 2))
    protein_g = Column(DECIMAL(10, 2))
    carbs_g = Column(DECIMAL(10, 2))
    fats_g = Column(DECIMAL(10, 2))
    sat_fats_g = Column(DECIMAL(10, 2))
    unsat_fats_g = Column(DECIMAL(10, 2))
    trans_fats_g = Column(DECIMAL(10, 2))
    fiber_g = Column(DECIMAL(10, 2))
    sugar_g = Column(DECIMAL(10, 2))
    calcium_mg = Column(DECIMAL(10, 2))
    iron_mg = Column(DECIMAL(10, 2))
    potassium_mg = Column(DECIMAL(10, 2))
    sodium_mg = Column(DECIMAL(10, 2))
    zinc_mg = Column(DECIMAL(10, 2))
    magnesium_mg = Column(DECIMAL(10, 2))
    vit_a_mcg = Column(DECIMAL(10, 2))
    vit_b1_mg = Column(DECIMAL(10, 2))
    vit_b2_mg = Column(DECIMAL(10, 2))
    vit_b3_mg = Column(DECIMAL(10, 2))
    vit_b5_mg = Column(DECIMAL(10, 2))
    vit_b6_mg = Column(DECIMAL(10, 2))
    vit_b9_mcg = Column(DECIMAL(10, 2))
    vit_b12_mcg = Column(DECIMAL(10, 2))
    vit_c_mg = Column(DECIMAL(10, 2))
    vit_d_mcg = Column(DECIMAL(10, 2))
    vit_e_mg = Column(DECIMAL(10, 2))
    vit_k_mcg = Column(DECIMAL(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", backref="dishes", foreign_keys=[created_by_user_id]) 