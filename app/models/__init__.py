"""Database models."""

# Import all models here to ensure they're recognized by SQLAlchemy
from app.models.auth import OTP, PasswordResetRequest, RefreshToken
from app.models.comment import Comment
from app.models.conversation import Conversation
from app.models.dish import Dish
from app.models.dish_ingredient import DishIngredient
from app.models.fitness_plan import FitnessPlan
from app.models.ingredient import Ingredient
from app.models.intake import Intake
from app.models.llm_model import LLMModel
from app.models.menu import Menu, MenuDish
from app.models.message import Message
from app.models.post import Post
from app.models.user import User
from app.models.user_profile import UserProfile

__all__ = [
    "User",
    "UserProfile",
    "Ingredient",
    "Dish",
    "Intake",
    "Menu",
    "MenuDish",
    "DishIngredient",
    "OTP",
    "RefreshToken",
    "PasswordResetRequest",
    "Conversation",
    "Message",
    "Post",
    "Comment",
    "LLMModel",
    "FitnessPlan",
]
