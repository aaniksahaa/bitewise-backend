"""
Seed script for dishes with ingredients.
This script reads dishes from JSON file and creates the dishes with their associated ingredients.
It handles ingredient creation if they don't exist and calculates nutritional totals for dishes.
"""

import json
import os
import sys
from decimal import Decimal
from typing import Dict, List, Any, Optional

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.models.ingredient import Ingredient
from app.models.dish import Dish
from app.models.dish_ingredient import DishIngredient


def fix_sequences():
    """
    Fix auto-increment sequences to start from the correct next value.
    This prevents duplicate key errors when inserting new records.
    """
    print("Fixing database sequences...")
    
    with engine.connect() as conn:
        # Fix ingredients sequence
        result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM ingredients"))
        max_ingredient_id = result.scalar()
        conn.execute(text(f"SELECT setval('ingredients_id_seq', {max_ingredient_id + 1})"))
        print(f"  Ingredients sequence set to: {max_ingredient_id + 1}")
        
        # Fix dishes sequence
        result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM dishes"))
        max_dish_id = result.scalar()
        conn.execute(text(f"SELECT setval('dishes_id_seq', {max_dish_id + 1})"))
        print(f"  Dishes sequence set to: {max_dish_id + 1}")
        
        # Fix dish_ingredients sequence
        result = conn.execute(text("SELECT COALESCE(MAX(id), 0) FROM dish_ingredients"))
        max_di_id = result.scalar()
        conn.execute(text(f"SELECT setval('dish_ingredients_id_seq', {max_di_id + 1})"))
        print(f"  Dish_ingredients sequence set to: {max_di_id + 1}")
        
        conn.commit()
    
    print("Sequences fixed successfully!")


def get_or_create_ingredient(db: Session, ingredient_data: Dict[str, Any]) -> Ingredient:
    """
    Get an existing ingredient by name or create a new one.
    
    Args:
        db: Database session
        ingredient_data: Dictionary containing ingredient information
    
    Returns:
        Ingredient object (existing or newly created)
    """
    # Try to find existing ingredient by name
    existing_ingredient = db.query(Ingredient).filter(
        Ingredient.name == ingredient_data["name"]
    ).first()
    
    if existing_ingredient:
        print(f"  Found existing ingredient: {existing_ingredient.name}")
        return existing_ingredient
    
    # Helper function to convert values, keeping 0.0 as 0.0 but converting missing/None to None
    def convert_value(value):
        if value is None:
            return None
        if isinstance(value, (int, float)) and value == 0:
            return Decimal('0.0')
        return Decimal(str(value))
    
    # Create new ingredient
    new_ingredient = Ingredient(
        name=ingredient_data["name"],
        serving_size=Decimal(str(ingredient_data["serving_size"])),
        calories=convert_value(ingredient_data.get("calories")),
        protein_g=convert_value(ingredient_data.get("protein_g")),
        carbs_g=convert_value(ingredient_data.get("carbs_g")),
        fats_g=convert_value(ingredient_data.get("fats_g")),
        sat_fats_g=convert_value(ingredient_data.get("sat_fats_g")),
        unsat_fats_g=convert_value(ingredient_data.get("unsat_fats_g")),
        trans_fats_g=convert_value(ingredient_data.get("trans_fats_g")),
        fiber_g=convert_value(ingredient_data.get("fiber_g")),
        sugar_g=convert_value(ingredient_data.get("sugar_g")),
        calcium_mg=convert_value(ingredient_data.get("calcium_mg")),
        iron_mg=convert_value(ingredient_data.get("iron_mg")),
        potassium_mg=convert_value(ingredient_data.get("potassium_mg")),
        sodium_mg=convert_value(ingredient_data.get("sodium_mg")),
        zinc_mg=convert_value(ingredient_data.get("zinc_mg")),
        magnesium_mg=convert_value(ingredient_data.get("magnesium_mg")),
        vit_a_mcg=convert_value(ingredient_data.get("vit_a_mcg")),
        vit_b1_mg=convert_value(ingredient_data.get("vit_b1_mg")),
        vit_b2_mg=convert_value(ingredient_data.get("vit_b2_mg")),
        vit_b3_mg=convert_value(ingredient_data.get("vit_b3_mg")),
        vit_b5_mg=convert_value(ingredient_data.get("vit_b5_mg")),
        vit_b6_mg=convert_value(ingredient_data.get("vit_b6_mg")),
        vit_b9_mcg=convert_value(ingredient_data.get("vit_b9_mcg")),
        vit_b12_mcg=convert_value(ingredient_data.get("vit_b12_mcg")),
        vit_c_mg=convert_value(ingredient_data.get("vit_c_mg")),
        vit_d_mcg=convert_value(ingredient_data.get("vit_d_mcg")),
        vit_e_mg=convert_value(ingredient_data.get("vit_e_mg")),
        vit_k_mcg=convert_value(ingredient_data.get("vit_k_mcg")),
        image_url=ingredient_data.get("image_url")
    )
    
    try:
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)
        print(f"  Created new ingredient: {new_ingredient.name}")
        return new_ingredient
    except IntegrityError:
        db.rollback()
        # If there was a race condition, try to get the existing one again
        existing = db.query(Ingredient).filter(
            Ingredient.name == ingredient_data["name"]
        ).first()
        if existing:
            return existing
        raise


def calculate_dish_nutritionals(ingredients_data: List[Dict[str, Any]]) -> Dict[str, Optional[Decimal]]:
    """
    Calculate total nutritional values for a dish based on its ingredients and quantities.
    
    Args:
        ingredients_data: List of ingredient dictionaries with quantity and nutritional info
    
    Returns:
        Dictionary of total nutritional values for the dish
    """
    totals = {
        'calories': Decimal('0'),
        'protein_g': Decimal('0'),
        'carbs_g': Decimal('0'),
        'fats_g': Decimal('0'),
        'sat_fats_g': Decimal('0'),
        'unsat_fats_g': Decimal('0'),
        'trans_fats_g': Decimal('0'),
        'fiber_g': Decimal('0'),
        'sugar_g': Decimal('0'),
        'calcium_mg': Decimal('0'),
        'iron_mg': Decimal('0'),
        'potassium_mg': Decimal('0'),
        'sodium_mg': Decimal('0'),
        'zinc_mg': Decimal('0'),
        'magnesium_mg': Decimal('0'),
        'vit_a_mcg': Decimal('0'),
        'vit_b1_mg': Decimal('0'),
        'vit_b2_mg': Decimal('0'),
        'vit_b3_mg': Decimal('0'),
        'vit_b5_mg': Decimal('0'),
        'vit_b6_mg': Decimal('0'),
        'vit_b9_mcg': Decimal('0'),
        'vit_b12_mcg': Decimal('0'),
        'vit_c_mg': Decimal('0'),
        'vit_d_mcg': Decimal('0'),
        'vit_e_mg': Decimal('0'),
        'vit_k_mcg': Decimal('0'),
    }
    
    for ingredient in ingredients_data:
        quantity = Decimal(str(ingredient["quantity"]))
        serving_size = Decimal(str(ingredient["serving_size"]))
        multiplier = quantity / serving_size
        
        for key in totals.keys():
            if ingredient.get(key) is not None:
                totals[key] += Decimal(str(ingredient[key])) * multiplier
    
    # Round to 2 decimal places
    for key in totals:
        totals[key] = totals[key].quantize(Decimal('0.01'))
    
    return totals


def create_dish_with_ingredients(db: Session, dish_data: Dict[str, Any]) -> Dish:
    """
    Create a dish with its associated ingredients.
    
    Args:
        db: Database session
        dish_data: Dictionary containing dish information and ingredients
    
    Returns:
        Created Dish object
    """
    print(f"Creating dish: {dish_data['name']}")
    
    # Check if dish already has nutritional values, otherwise calculate from ingredients
    if dish_data.get('calories') is not None:
        # Use provided nutritional values
        print("  Using pre-calculated nutritional values")
        nutritional_values = {
            'calories': Decimal(str(dish_data['calories'])) if dish_data.get('calories') else None,
            'protein_g': Decimal(str(dish_data['protein_g'])) if dish_data.get('protein_g') else None,
            'carbs_g': Decimal(str(dish_data['carbs_g'])) if dish_data.get('carbs_g') else None,
            'fats_g': Decimal(str(dish_data['fats_g'])) if dish_data.get('fats_g') else None,
            'sat_fats_g': Decimal(str(dish_data['sat_fats_g'])) if dish_data.get('sat_fats_g') else None,
            'unsat_fats_g': Decimal(str(dish_data['unsat_fats_g'])) if dish_data.get('unsat_fats_g') else None,
            'trans_fats_g': Decimal(str(dish_data['trans_fats_g'])) if dish_data.get('trans_fats_g') else None,
            'fiber_g': Decimal(str(dish_data['fiber_g'])) if dish_data.get('fiber_g') else None,
            'sugar_g': Decimal(str(dish_data['sugar_g'])) if dish_data.get('sugar_g') else None,
            'calcium_mg': Decimal(str(dish_data['calcium_mg'])) if dish_data.get('calcium_mg') else None,
            'iron_mg': Decimal(str(dish_data['iron_mg'])) if dish_data.get('iron_mg') else None,
            'potassium_mg': Decimal(str(dish_data['potassium_mg'])) if dish_data.get('potassium_mg') else None,
            'sodium_mg': Decimal(str(dish_data['sodium_mg'])) if dish_data.get('sodium_mg') else None,
            'zinc_mg': Decimal(str(dish_data['zinc_mg'])) if dish_data.get('zinc_mg') else None,
            'magnesium_mg': Decimal(str(dish_data['magnesium_mg'])) if dish_data.get('magnesium_mg') else None,
            'vit_a_mcg': Decimal(str(dish_data['vit_a_mcg'])) if dish_data.get('vit_a_mcg') else None,
            'vit_b1_mg': Decimal(str(dish_data['vit_b1_mg'])) if dish_data.get('vit_b1_mg') else None,
            'vit_b2_mg': Decimal(str(dish_data['vit_b2_mg'])) if dish_data.get('vit_b2_mg') else None,
            'vit_b3_mg': Decimal(str(dish_data['vit_b3_mg'])) if dish_data.get('vit_b3_mg') else None,
            'vit_b5_mg': Decimal(str(dish_data['vit_b5_mg'])) if dish_data.get('vit_b5_mg') else None,
            'vit_b6_mg': Decimal(str(dish_data['vit_b6_mg'])) if dish_data.get('vit_b6_mg') else None,
            'vit_b9_mcg': Decimal(str(dish_data['vit_b9_mcg'])) if dish_data.get('vit_b9_mcg') else None,
            'vit_b12_mcg': Decimal(str(dish_data['vit_b12_mcg'])) if dish_data.get('vit_b12_mcg') else None,
            'vit_c_mg': Decimal(str(dish_data['vit_c_mg'])) if dish_data.get('vit_c_mg') else None,
            'vit_d_mcg': Decimal(str(dish_data['vit_d_mcg'])) if dish_data.get('vit_d_mcg') else None,
            'vit_e_mg': Decimal(str(dish_data['vit_e_mg'])) if dish_data.get('vit_e_mg') else None,
            'vit_k_mcg': Decimal(str(dish_data['vit_k_mcg'])) if dish_data.get('vit_k_mcg') else None,
        }
    else:
        # Calculate nutritional totals from ingredients
        print("  Calculating nutritional values from ingredients")
        nutritional_values = calculate_dish_nutritionals(dish_data["ingredients"])
    
    # Create the dish
    dish = Dish(
        name=dish_data["name"],
        description=dish_data.get("description"),
        cuisine=dish_data.get("cuisine"),
        cooking_steps=dish_data.get("cooking_steps"),
        prep_time_minutes=dish_data.get("prep_time_minutes"),
        cook_time_minutes=dish_data.get("cook_time_minutes"),
        image_urls=dish_data.get("image_urls"),
        servings=dish_data.get("servings"),
        # Set nutritional values (either calculated or provided)
        calories=nutritional_values['calories'],
        protein_g=nutritional_values['protein_g'],
        carbs_g=nutritional_values['carbs_g'],
        fats_g=nutritional_values['fats_g'],
        sat_fats_g=nutritional_values['sat_fats_g'],
        unsat_fats_g=nutritional_values['unsat_fats_g'],
        trans_fats_g=nutritional_values['trans_fats_g'],
        fiber_g=nutritional_values['fiber_g'],
        sugar_g=nutritional_values['sugar_g'],
        calcium_mg=nutritional_values['calcium_mg'],
        iron_mg=nutritional_values['iron_mg'],
        potassium_mg=nutritional_values['potassium_mg'],
        sodium_mg=nutritional_values['sodium_mg'],
        zinc_mg=nutritional_values['zinc_mg'],
        magnesium_mg=nutritional_values['magnesium_mg'],
        vit_a_mcg=nutritional_values['vit_a_mcg'],
        vit_b1_mg=nutritional_values['vit_b1_mg'],
        vit_b2_mg=nutritional_values['vit_b2_mg'],
        vit_b3_mg=nutritional_values['vit_b3_mg'],
        vit_b5_mg=nutritional_values['vit_b5_mg'],
        vit_b6_mg=nutritional_values['vit_b6_mg'],
        vit_b9_mcg=nutritional_values['vit_b9_mcg'],
        vit_b12_mcg=nutritional_values['vit_b12_mcg'],
        vit_c_mg=nutritional_values['vit_c_mg'],
        vit_d_mcg=nutritional_values['vit_d_mcg'],
        vit_e_mg=nutritional_values['vit_e_mg'],
        vit_k_mcg=nutritional_values['vit_k_mcg'],
    )
    
    db.add(dish)
    db.commit()
    db.refresh(dish)
    
    # Process ingredients and create dish-ingredient relationships
    for ingredient_data in dish_data["ingredients"]:
        # Get or create the ingredient
        ingredient = get_or_create_ingredient(db, ingredient_data)
        
        # Create dish-ingredient relationship
        dish_ingredient = DishIngredient(
            dish_id=dish.id,
            ingredient_id=ingredient.id,
            quantity=Decimal(str(ingredient_data["quantity"]))
        )
        
        db.add(dish_ingredient)
    
    db.commit()
    print(f"  Added {len(dish_data['ingredients'])} ingredients to dish")
    print(f"  Total calories: {nutritional_values['calories']}")
    
    return dish


def seed_dishes():
    """Main function to seed dishes from JSON file."""
    # Fix sequences first to prevent ID conflicts
    fix_sequences()
    
    # Get the path to the JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, "dishes_with_ingredients.json")
    
    if not os.path.exists(json_file_path):
        print(f"JSON file not found: {json_file_path}")
        return
    
    # Load dishes data from JSON
    with open(json_file_path, 'r') as file:
        dishes_data = json.load(file)
    
    # Create database session
    db = SessionLocal()
    
    try:
        print(f"Seeding {len(dishes_data)} dishes...")
        
        for dish_data in dishes_data:
            # Check if dish already exists
            existing_dish = db.query(Dish).filter(
                Dish.name == dish_data["name"]
            ).first()
            
            if existing_dish:
                print(f"Dish '{dish_data['name']}' already exists, skipping...")
                continue
            
            # Create the dish with ingredients
            dish = create_dish_with_ingredients(db, dish_data)
            print(f"Successfully created dish: {dish.name} (ID: {dish.id})")
            print("-" * 50)
        
        print("Seeding completed successfully!")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_dishes() 