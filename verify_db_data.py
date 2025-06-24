#!/usr/bin/env python3
"""
Script to verify what data actually exists in the database.
"""

import os
from dotenv import load_dotenv

def verify_database_data():
    # Load environment
    load_dotenv(override=True)
    print(f"Environment: {os.getenv('ENVIRONMENT', 'not set')}")
    
    try:
        from app.db.session import SessionLocal
        from app.core.config import settings
        from app.models.ingredient import Ingredient
        from app.models.dish import Dish
        from app.models.dish_ingredient import DishIngredient
        
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Create database session
        db = SessionLocal()
        
        # Count ingredients
        ingredient_count = db.query(Ingredient).count()
        print(f"Total ingredients in database: {ingredient_count}")
        
        # Count dishes
        dish_count = db.query(Dish).count()
        print(f"Total dishes in database: {dish_count}")
        
        # Count dish-ingredient relationships
        dish_ingredient_count = db.query(DishIngredient).count()
        print(f"Total dish-ingredient relationships: {dish_ingredient_count}")
        
        # Show sample ingredients
        print("\nSample ingredients:")
        ingredients = db.query(Ingredient).limit(5).all()
        for ing in ingredients:
            print(f"  - ID: {ing.id}, Name: {ing.name}")
        
        # Show sample dishes
        print("\nSample dishes:")
        dishes = db.query(Dish).limit(5).all()
        for dish in dishes:
            print(f"  - ID: {dish.id}, Name: {dish.name}")
        
        # Show sample dish-ingredient relationships
        print("\nSample dish-ingredient relationships:")
        relationships = db.query(DishIngredient).limit(5).all()
        for rel in relationships:
            print(f"  - Dish ID: {rel.dish_id}, Ingredient ID: {rel.ingredient_id}, Quantity: {rel.quantity}")
        
        # Check for dishes created in the last hour (recent)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=1)
        recent_dishes = db.query(Dish).filter(Dish.created_at >= recent_cutoff).all()
        print(f"\nDishes created in last hour: {len(recent_dishes)}")
        for dish in recent_dishes[:5]:
            print(f"  - {dish.name} (created: {dish.created_at})")
        
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_database_data() 