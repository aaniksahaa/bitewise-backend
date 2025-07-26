#!/usr/bin/env python3
"""
Script to seed 5 dishes for testing purposes.
This is a utility script, not a test.
"""

import os
import json
import sys
from decimal import Decimal
from typing import Dict, Optional
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def reload_environment():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        print(f"Environment reloaded. Current ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
        return True
    except ImportError:
        print("Warning: python-dotenv not installed.")
        return False


def seed_5_dishes():
    """Seed 5 dishes for testing purposes."""
    # Force reload environment
    reload_environment()
    
    try:
        from app.db.session import SessionLocal
        from app.core.config import settings
        from app.models.ingredient import Ingredient
        from app.models.dish import Dish
        
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Create database session
        db = SessionLocal()
        
        # Add your seeding logic here
        print("Seeding 5 dishes...")
        
        # Example dish data (you'll need to implement the actual seeding logic)
        dishes_data = [
            {"name": "Test Dish 1", "description": "Test dish for development"},
            {"name": "Test Dish 2", "description": "Another test dish"},
            {"name": "Test Dish 3", "description": "Third test dish"},
            {"name": "Test Dish 4", "description": "Fourth test dish"},
            {"name": "Test Dish 5", "description": "Fifth test dish"},
        ]
        
        for dish_data in dishes_data:
            # Check if dish already exists
            existing_dish = db.query(Dish).filter(Dish.name == dish_data["name"]).first()
            if not existing_dish:
                dish = Dish(**dish_data)
                db.add(dish)
                print(f"Added dish: {dish_data['name']}")
            else:
                print(f"Dish already exists: {dish_data['name']}")
        
        db.commit()
        db.close()
        
        print("✅ Successfully seeded 5 dishes!")
        
    except Exception as e:
        print(f"❌ Error seeding dishes: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    seed_5_dishes()