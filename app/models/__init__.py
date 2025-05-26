"""Database models."""

# Import all models here to ensure they're recognized by SQLAlchemy
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.ingredient import Ingredient
from app.models.dish import Dish
from app.models.dish_ingredient import DishIngredient
from app.models.menu import Menu, MenuDish

__all__ = ["User", "UserProfile", "Ingredient", "Dish", "DishIngredient", "Menu", "MenuDish"] 