#!/usr/bin/env python3
"""
Test script to seed only 5 dishes with extensive debugging.
"""

import os
import json
import sys
from decimal import Decimal
from typing import Dict, Optional
from dotenv import load_dotenv

def reload_environment():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        print(f"Environment reloaded. Current ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
        return True
    except ImportError:
        print("Warning: python-dotenv not installed.")
        return False

def test_seed_5_dishes():
    # Force reload environment
    reload_environment()
    
    try:
        from app.db.session import SessionLocal
        from app.core.config import settings
        from app.models.ingredient import Ingredient
        from app.models.dish import Dish
        from app.models.dish_ingredient import DishIngredient
        
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Create database session
        db = SessionLocal()
        
        print("Initial state:")
        ingredient_count = db.query(Ingredient).count()
        dish_count_before = db.query(Dish).count()
        rel_count_before = db.query(DishIngredient).count()
        print(f"  Ingredients: {ingredient_count}")
        print(f"  Dishes: {dish_count_before}")
        print(f"  Relationships: {rel_count_before}")
        
        # Load dishes data
        with open('seed_data/final/dishes.json', 'r', encoding='utf-8') as f:
            dishes_data = json.load(f)
        
        # Load ingredients data to build UUID mapping
        with open('seed_data/final/ingredients.json', 'r', encoding='utf-8') as f:
            ingredients_data = json.load(f)
        
        # Build ingredient UUID to DB ID mapping
        ingredient_uuid_to_db_id = {}
        print("Building ingredient UUID mapping...")
        for ingredient_data in ingredients_data:
            name = ingredient_data.get('name', '').strip()
            uuid_id = ingredient_data.get('id')
            if name and uuid_id:
                existing_ingredient = db.query(Ingredient).filter(
                    Ingredient.name.ilike(name)
                ).first()
                if existing_ingredient:
                    ingredient_uuid_to_db_id[uuid_id] = existing_ingredient.id
        
        print(f"Mapped {len(ingredient_uuid_to_db_id)} ingredient UUIDs to DB IDs")
        
        def safe_decimal(value):
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except:
                return None
        
        def safe_string(value, max_length):
            if not value:
                return ""
            value = str(value).strip()
            if len(value) > max_length:
                return value[:max_length-3] + "..."
            return value
        
        # Process only first 5 dishes
        dishes_to_process = dishes_data[:5]
        dishes_created = 0
        relationships_created = 0
        
        for i, dish_data in enumerate(dishes_to_process, 1):
            print(f"\n--- Processing dish {i}/5: {dish_data.get('name')} ---")
            
            name = dish_data.get('name', '').strip()
            if not name:
                print(f"  ❌ Dish missing name, skipping")
                continue
            
            # Check if dish already exists
            existing_dish = db.query(Dish).filter(Dish.name.ilike(name)).first()
            if existing_dish:
                print(f"  ⏭️  Dish already exists: {name}")
                continue
            
            # Handle image URLs
            image_urls = dish_data.get('image_urls', [])
            if image_urls:
                cleaned_urls = []
                for url in image_urls:
                    if url:
                        cleaned_url = safe_string(str(url), 255)
                        if cleaned_url:
                            cleaned_urls.append(cleaned_url)
                image_urls = cleaned_urls if cleaned_urls else None
            else:
                image_urls = None
            
            # Create dish
            try:
                dish = Dish(
                    name=safe_string(name, 100),
                    description=dish_data.get('description'),
                    cuisine=dish_data.get('cuisine'),
                    cooking_steps=dish_data.get('cooking_steps'),
                    prep_time_minutes=dish_data.get('prep_time_minutes'),
                    cook_time_minutes=dish_data.get('cook_time_minutes'),
                    image_urls=image_urls,
                    servings=dish_data.get('servings'),
                    calories=safe_decimal(dish_data.get('calories')),
                    protein_g=safe_decimal(dish_data.get('protein_g')),
                    carbs_g=safe_decimal(dish_data.get('carbs_g')),
                    fats_g=safe_decimal(dish_data.get('fats_g')),
                    sat_fats_g=safe_decimal(dish_data.get('sat_fats_g')),
                    unsat_fats_g=safe_decimal(dish_data.get('unsat_fats_g')),
                    trans_fats_g=safe_decimal(dish_data.get('trans_fats_g')),
                    fiber_g=safe_decimal(dish_data.get('fiber_g')),
                    sugar_g=safe_decimal(dish_data.get('sugar_g')),
                    calcium_mg=safe_decimal(dish_data.get('calcium_mg')),
                    iron_mg=safe_decimal(dish_data.get('iron_mg')),
                    potassium_mg=safe_decimal(dish_data.get('potassium_mg')),
                    sodium_mg=safe_decimal(dish_data.get('sodium_mg')),
                    zinc_mg=safe_decimal(dish_data.get('zinc_mg')),
                    magnesium_mg=safe_decimal(dish_data.get('magnesium_mg')),
                    vit_a_mcg=safe_decimal(dish_data.get('vit_a_mcg')),
                    vit_b1_mg=safe_decimal(dish_data.get('vit_b1_mg')),
                    vit_b2_mg=safe_decimal(dish_data.get('vit_b2_mg')),
                    vit_b3_mg=safe_decimal(dish_data.get('vit_b3_mg')),
                    vit_b5_mg=safe_decimal(dish_data.get('vit_b5_mg')),
                    vit_b6_mg=safe_decimal(dish_data.get('vit_b6_mg')),
                    vit_b9_mcg=safe_decimal(dish_data.get('vit_b9_mcg')),
                    vit_b12_mcg=safe_decimal(dish_data.get('vit_b12_mcg')),
                    vit_c_mg=safe_decimal(dish_data.get('vit_c_mg')),
                    vit_d_mcg=safe_decimal(dish_data.get('vit_d_mcg')),
                    vit_e_mg=safe_decimal(dish_data.get('vit_e_mg')),
                    vit_k_mcg=safe_decimal(dish_data.get('vit_k_mcg')),
                    created_by_user_id=None
                )
                
                db.add(dish)
                db.flush()
                print(f"  ✅ Created dish: {dish.name} (ID: {dish.id})")
                dishes_created += 1
                
                # Process ingredients for this dish
                ingredients = dish_data.get('ingredients', [])
                print(f"  Processing {len(ingredients)} ingredients...")
                
                for j, ingredient_ref in enumerate(ingredients):
                    ingredient_uuid = ingredient_ref.get('id')
                    quantity = ingredient_ref.get('quantity', 0)
                    
                    if not ingredient_uuid:
                        print(f"    ❌ Missing ingredient UUID at index {j}")
                        continue
                    
                    ingredient_db_id = ingredient_uuid_to_db_id.get(ingredient_uuid)
                    if not ingredient_db_id:
                        print(f"    ❌ Ingredient UUID '{ingredient_uuid}' not found")
                        continue
                    
                    # Check if relationship already exists
                    existing_rel = db.query(DishIngredient).filter(
                        DishIngredient.dish_id == dish.id,
                        DishIngredient.ingredient_id == ingredient_db_id
                    ).first()
                    
                    if existing_rel:
                        print(f"    ⏭️  Relationship already exists for ingredient {ingredient_db_id}")
                        continue
                    
                    # Create relationship
                    dish_ingredient = DishIngredient(
                        dish_id=dish.id,
                        ingredient_id=ingredient_db_id,
                        quantity=safe_decimal(quantity) or Decimal('0')
                    )
                    
                    db.add(dish_ingredient)
                    relationships_created += 1
                    
                    if j < 3:  # Only print first 3
                        print(f"    ✅ Added ingredient {ingredient_db_id} with quantity {quantity}")
                
                if len(ingredients) > 3:
                    print(f"    ... and {len(ingredients) - 3} more ingredients")
                
            except Exception as e:
                print(f"  ❌ Error creating dish: {e}")
                db.rollback()
                continue
        
        # Commit all changes
        print(f"\nCommitting {dishes_created} dishes and {relationships_created} relationships...")
        try:
            db.commit()
            print("✅ Committed successfully")
            
            # Verify
            dish_count_after = db.query(Dish).count()
            rel_count_after = db.query(DishIngredient).count()
            print(f"Final counts: {dish_count_after} dishes (+{dish_count_after - dish_count_before}), {rel_count_after} relationships (+{rel_count_after - rel_count_before})")
            
        except Exception as e:
            print(f"❌ Error committing: {e}")
            db.rollback()
        
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_seed_5_dishes() 