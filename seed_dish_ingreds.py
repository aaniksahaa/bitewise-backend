#!/usr/bin/env python3
"""
Comprehensive script to seed the database with dishes and ingredients from JSON files.
This script handles auto-incrementing IDs, duplication checking, and comprehensive error handling.
"""

import json
import sys
import os
import decimal
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def reload_environment():
    """Force reload environment variables from .env file."""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Override existing environment variables
        print(f"Environment reloaded. Current ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
        return True
    except ImportError:
        print("Warning: python-dotenv not installed. Cannot reload environment variables.")
        return False

# Import these after potential environment reload - moved to __enter__ method
# from app.db.session import SessionLocal
# from app.models.ingredient import Ingredient
# from app.models.dish import Dish
# from app.models.dish_ingredient import DishIngredient
# from app.models.user import User


class DatabaseSeeder:
    def __init__(self):
        self.db: Optional[Session] = None
        self.ingredient_uuid_to_db_id: Dict[str, int] = {}
        self.stats = {
            'ingredients_processed': 0,
            'ingredients_created': 0,
            'ingredients_skipped': 0,
            'dishes_processed': 0,
            'dishes_created': 0,
            'dishes_skipped': 0,
            'dish_ingredients_created': 0,
            'errors': [],
            'warnings': []
        }

    def __enter__(self):
        # Import database modules after environment is reloaded
        from app.db.session import SessionLocal
        from app.models.ingredient import Ingredient
        from app.models.dish import Dish
        from app.models.dish_ingredient import DishIngredient
        from app.models.user import User
        
        # Store the imports as class attributes
        self.SessionLocal = SessionLocal
        self.Ingredient = Ingredient
        self.Dish = Dish
        self.DishIngredient = DishIngredient
        self.User = User
        
        # Create database session after environment is loaded
        self.db = SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            try:
                if exc_type is not None:
                    # Exception occurred, rollback any pending changes
                    self.db.rollback()
                    print(f"Rolling back due to exception: {exc_val}")
                else:
                    # No exception, but don't commit here since we do batch commits
                    print("Session cleanup - no additional commit needed")
            except Exception as e:
                print(f"Error during session cleanup: {e}")
                try:
                    self.db.rollback()
                except:
                    pass
            finally:
                self.db.close()

    def safe_decimal(self, value) -> Optional[Decimal]:
        """Safely convert a value to Decimal, handling None and invalid values."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError, decimal.InvalidOperation):
            return None

    def safe_string(self, value: str, max_length: int, field_name: str = "field") -> str:
        """Safely truncate string to fit database constraints."""
        if not value:
            return ""
        
        value = str(value).strip()
        if len(value) > max_length:
            truncated = value[:max_length-3] + "..."
            self.stats['warnings'].append(f"Truncated {field_name} from {len(value)} to {max_length} characters: '{value[:50]}...'")
            return truncated
        return value

    def clean_ingredient_name(self, name: str) -> Optional[str]:
        """Clean and validate ingredient name."""
        if not name:
            return None
            
        # Remove problematic characters
        name = name.strip()
        
        # Skip names that are just dashes or special characters
        if name in ['————————', '—', '--', '---']:
            return None
            
        # Truncate if too long (100 char limit)
        return self.safe_string(name, 100, "ingredient name")

    def check_ingredient_exists(self, name: str) -> Optional['Ingredient']:
        """Check if an ingredient already exists by name (case-insensitive)."""
        try:
            return self.db.query(self.Ingredient).filter(
                self.Ingredient.name.ilike(name.strip())
            ).first()
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error checking ingredient '{name}': {str(e)}")
            return None

    def check_dish_exists(self, name: str) -> Optional['Dish']:
        """Check if a dish already exists by name (case-insensitive)."""
        try:
            return self.db.query(self.Dish).filter(
                self.Dish.name.ilike(name.strip())
            ).first()
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error checking dish '{name}': {str(e)}")
            return None

    def create_ingredient(self, ingredient_data: dict) -> Optional['Ingredient']:
        """Create a new ingredient from JSON data."""
        try:
            # Extract and validate required fields
            raw_name = ingredient_data.get('name', '').strip()
            name = self.clean_ingredient_name(raw_name)
            
            if not name:
                self.stats['errors'].append(f"Ingredient has invalid or empty name: '{raw_name}'")
                return None

            serving_size = self.safe_decimal(ingredient_data.get('serving_size'))
            if serving_size is None:
                self.stats['errors'].append(f"Ingredient '{name}' missing valid serving_size")
                return None

            # Clean image URL
            image_url = self.safe_string(ingredient_data.get('image_url', ''), 255, "image URL")

            # Create ingredient with all nutritional data
            ingredient = self.Ingredient(
                name=name,
                serving_size=serving_size,
                calories=self.safe_decimal(ingredient_data.get('calories')),
                protein_g=self.safe_decimal(ingredient_data.get('protein_g')),
                carbs_g=self.safe_decimal(ingredient_data.get('carbs_g')),
                fats_g=self.safe_decimal(ingredient_data.get('fats_g')),
                sat_fats_g=self.safe_decimal(ingredient_data.get('sat_fats_g')),
                unsat_fats_g=self.safe_decimal(ingredient_data.get('unsat_fats_g')),
                trans_fats_g=self.safe_decimal(ingredient_data.get('trans_fats_g')),
                fiber_g=self.safe_decimal(ingredient_data.get('fiber_g')),
                sugar_g=self.safe_decimal(ingredient_data.get('sugar_g')),
                calcium_mg=self.safe_decimal(ingredient_data.get('calcium_mg')),
                iron_mg=self.safe_decimal(ingredient_data.get('iron_mg')),
                potassium_mg=self.safe_decimal(ingredient_data.get('potassium_mg')),
                sodium_mg=self.safe_decimal(ingredient_data.get('sodium_mg')),
                zinc_mg=self.safe_decimal(ingredient_data.get('zinc_mg')),
                magnesium_mg=self.safe_decimal(ingredient_data.get('magnesium_mg')),
                vit_a_mcg=self.safe_decimal(ingredient_data.get('vit_a_mcg')),
                vit_b1_mg=self.safe_decimal(ingredient_data.get('vit_b1_mg')),
                vit_b2_mg=self.safe_decimal(ingredient_data.get('vit_b2_mg')),
                vit_b3_mg=self.safe_decimal(ingredient_data.get('vit_b3_mg')),
                vit_b5_mg=self.safe_decimal(ingredient_data.get('vit_b5_mg')),
                vit_b6_mg=self.safe_decimal(ingredient_data.get('vit_b6_mg')),
                vit_b9_mcg=self.safe_decimal(ingredient_data.get('vit_b9_mcg')),
                vit_b12_mcg=self.safe_decimal(ingredient_data.get('vit_b12_mcg')),
                vit_c_mg=self.safe_decimal(ingredient_data.get('vit_c_mg')),
                vit_d_mcg=self.safe_decimal(ingredient_data.get('vit_d_mcg')),
                vit_e_mg=self.safe_decimal(ingredient_data.get('vit_e_mg')),
                vit_k_mcg=self.safe_decimal(ingredient_data.get('vit_k_mcg')),
                image_url=image_url if image_url else None
            )

            self.db.add(ingredient)
            self.db.flush()  # Get the ID without committing
            return ingredient

        except (SQLAlchemyError, IntegrityError) as e:
            self.stats['errors'].append(f"Error creating ingredient '{name}': {str(e)}")
            self.db.rollback()
            return None
        except Exception as e:
            self.stats['errors'].append(f"Unexpected error creating ingredient '{name}': {str(e)}")
            self.db.rollback()
            return None

    def create_dish(self, dish_data: dict) -> Optional['Dish']:
        """Create a new dish from JSON data."""
        try:
            # Extract and validate required fields
            raw_name = dish_data.get('name', '').strip()
            name = self.safe_string(raw_name, 100, "dish name")
            
            if not name:
                self.stats['errors'].append(f"Dish has invalid or empty name: '{raw_name}'")
                return None

            # Clean image URLs in the array
            image_urls = dish_data.get('image_urls', [])
            if image_urls:
                cleaned_urls = []
                for url in image_urls:
                    if url:
                        cleaned_url = self.safe_string(str(url), 255, "dish image URL")
                        if cleaned_url:
                            cleaned_urls.append(cleaned_url)
                image_urls = cleaned_urls if cleaned_urls else None
            else:
                image_urls = None

            # Create dish with all available data
            dish = self.Dish(
                name=name,
                description=dish_data.get('description'),
                cuisine=dish_data.get('cuisine'),
                cooking_steps=dish_data.get('cooking_steps'),
                prep_time_minutes=dish_data.get('prep_time_minutes'),
                cook_time_minutes=dish_data.get('cook_time_minutes'),
                image_urls=image_urls,
                servings=dish_data.get('servings'),
                calories=self.safe_decimal(dish_data.get('calories')),
                protein_g=self.safe_decimal(dish_data.get('protein_g')),
                carbs_g=self.safe_decimal(dish_data.get('carbs_g')),
                fats_g=self.safe_decimal(dish_data.get('fats_g')),
                sat_fats_g=self.safe_decimal(dish_data.get('sat_fats_g')),
                unsat_fats_g=self.safe_decimal(dish_data.get('unsat_fats_g')),
                trans_fats_g=self.safe_decimal(dish_data.get('trans_fats_g')),
                fiber_g=self.safe_decimal(dish_data.get('fiber_g')),
                sugar_g=self.safe_decimal(dish_data.get('sugar_g')),
                calcium_mg=self.safe_decimal(dish_data.get('calcium_mg')),
                iron_mg=self.safe_decimal(dish_data.get('iron_mg')),
                potassium_mg=self.safe_decimal(dish_data.get('potassium_mg')),
                sodium_mg=self.safe_decimal(dish_data.get('sodium_mg')),
                zinc_mg=self.safe_decimal(dish_data.get('zinc_mg')),
                magnesium_mg=self.safe_decimal(dish_data.get('magnesium_mg')),
                vit_a_mcg=self.safe_decimal(dish_data.get('vit_a_mcg')),
                vit_b1_mg=self.safe_decimal(dish_data.get('vit_b1_mg')),
                vit_b2_mg=self.safe_decimal(dish_data.get('vit_b2_mg')),
                vit_b3_mg=self.safe_decimal(dish_data.get('vit_b3_mg')),
                vit_b5_mg=self.safe_decimal(dish_data.get('vit_b5_mg')),
                vit_b6_mg=self.safe_decimal(dish_data.get('vit_b6_mg')),
                vit_b9_mcg=self.safe_decimal(dish_data.get('vit_b9_mcg')),
                vit_b12_mcg=self.safe_decimal(dish_data.get('vit_b12_mcg')),
                vit_c_mg=self.safe_decimal(dish_data.get('vit_c_mg')),
                vit_d_mcg=self.safe_decimal(dish_data.get('vit_d_mcg')),
                vit_e_mg=self.safe_decimal(dish_data.get('vit_e_mg')),
                vit_k_mcg=self.safe_decimal(dish_data.get('vit_k_mcg')),
                created_by_user_id=None  # No specific user for seeded dishes
            )

            self.db.add(dish)
            self.db.flush()  # Get the ID without committing
            return dish

        except (SQLAlchemyError, IntegrityError) as e:
            self.stats['errors'].append(f"Error creating dish '{name}': {str(e)}")
            self.db.rollback()
            return None
        except Exception as e:
            self.stats['errors'].append(f"Unexpected error creating dish '{name}': {str(e)}")
            self.db.rollback()
            return None

    def create_dish_ingredient_relationship(self, dish_id: int, ingredient_id: int, quantity: float) -> bool:
        """Create a dish-ingredient relationship."""
        try:
            # Check if relationship already exists
            existing = self.db.query(self.DishIngredient).filter(
                self.DishIngredient.dish_id == dish_id,
                self.DishIngredient.ingredient_id == ingredient_id
            ).first()

            if existing:
                # Update quantity if different
                if existing.quantity != Decimal(str(quantity)):
                    existing.quantity = Decimal(str(quantity))
                return True

            # Create new relationship
            dish_ingredient = self.DishIngredient(
                dish_id=dish_id,
                ingredient_id=ingredient_id,
                quantity=self.safe_decimal(quantity) or Decimal('0')
            )

            self.db.add(dish_ingredient)
            self.stats['dish_ingredients_created'] += 1
            return True

        except (SQLAlchemyError, IntegrityError) as e:
            self.stats['errors'].append(f"Error creating dish-ingredient relationship (dish_id={dish_id}, ingredient_id={ingredient_id}): {str(e)}")
            return False
        except Exception as e:
            self.stats['errors'].append(f"Unexpected error creating dish-ingredient relationship: {str(e)}")
            return False

    def load_ingredients(self, file_path: str) -> bool:
        """Load and process ingredients from JSON file."""
        print(f"Loading ingredients from {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ingredients_data = json.load(f)
        except FileNotFoundError:
            self.stats['errors'].append(f"Ingredients file not found: {file_path}")
            return False
        except json.JSONDecodeError as e:
            self.stats['errors'].append(f"Invalid JSON in ingredients file: {str(e)}")
            return False

        if not isinstance(ingredients_data, list):
            self.stats['errors'].append("Ingredients data must be a list")
            return False

        print(f"Found {len(ingredients_data)} ingredients to process")

        for ingredient_data in ingredients_data:
            self.stats['ingredients_processed'] += 1
            
            if self.stats['ingredients_processed'] % 100 == 0:
                print(f"Processed {self.stats['ingredients_processed']} ingredients...")

            name = ingredient_data.get('name', '').strip()
            uuid_id = ingredient_data.get('id')

            if not name or not uuid_id:
                self.stats['errors'].append(f"Ingredient missing name or id: {ingredient_data}")
                continue

            # Check if ingredient already exists
            existing_ingredient = self.check_ingredient_exists(name)
            if existing_ingredient:
                self.stats['ingredients_skipped'] += 1
                self.ingredient_uuid_to_db_id[uuid_id] = existing_ingredient.id
                continue

            # Create new ingredient
            new_ingredient = self.create_ingredient(ingredient_data)
            if new_ingredient:
                self.stats['ingredients_created'] += 1
                self.ingredient_uuid_to_db_id[uuid_id] = new_ingredient.id
            else:
                self.stats['errors'].append(f"Failed to create ingredient: {name}")

        # Commit all ingredient changes
        try:
            self.db.commit()
            print(f"Successfully committed {self.stats['ingredients_created']} new ingredients")
            
            # Verify the commit by counting ingredients in database
            actual_ingredient_count = self.db.query(self.Ingredient).count()
            print(f"Verification: Database now contains {actual_ingredient_count} total ingredients")
            
            return True
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error committing ingredients: {str(e)}")
            self.db.rollback()
            return False

    def load_dishes(self, file_path: str) -> bool:
        """Load and process dishes from JSON file."""
        print(f"Loading dishes from {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dishes_data = json.load(f)
        except FileNotFoundError:
            self.stats['errors'].append(f"Dishes file not found: {file_path}")
            return False
        except json.JSONDecodeError as e:
            self.stats['errors'].append(f"Invalid JSON in dishes file: {str(e)}")
            return False

        if not isinstance(dishes_data, list):
            self.stats['errors'].append("Dishes data must be a list")
            return False

        print(f"Found {len(dishes_data)} dishes to process")

        for dish_data in dishes_data:
            self.stats['dishes_processed'] += 1
            
            if self.stats['dishes_processed'] % 10 == 0:
                print(f"Processed {self.stats['dishes_processed']} dishes...")

            name = dish_data.get('name', '').strip()
            if not name:
                self.stats['errors'].append(f"Dish missing name: {dish_data}")
                continue

            # Check if dish already exists
            existing_dish = self.check_dish_exists(name)
            if existing_dish:
                self.stats['dishes_skipped'] += 1
                print(f"Skipping existing dish: {name}")
                continue

            # Create new dish with individual commit
            try:
                new_dish = self.create_dish(dish_data)
                if not new_dish:
                    continue  # Error already logged in create_dish

                # Process ingredients for this dish
                ingredients = dish_data.get('ingredients', [])
                relationships_created = 0
                
                for ingredient_ref in ingredients:
                    ingredient_uuid = ingredient_ref.get('id')
                    quantity = ingredient_ref.get('quantity', 0)

                    if not ingredient_uuid:
                        self.stats['errors'].append(f"Missing ingredient UUID in dish '{name}': {ingredient_ref}")
                        continue

                    # Find the ingredient in our mapping
                    ingredient_db_id = self.ingredient_uuid_to_db_id.get(ingredient_uuid)
                    if not ingredient_db_id:
                        self.stats['errors'].append(f"Ingredient UUID '{ingredient_uuid}' not found for dish '{name}'")
                        continue

                    # Create the relationship
                    if self.create_dish_ingredient_relationship(new_dish.id, ingredient_db_id, quantity):
                        relationships_created += 1

                # Commit this dish and its relationships immediately
                try:
                    self.db.commit()
                    self.stats['dishes_created'] += 1
                    
                    if self.stats['dishes_created'] % 5 == 0:  # Progress update every 5 dishes
                        print(f"  ✅ Committed dish '{name}' with {relationships_created} ingredients. Total dishes: {self.stats['dishes_created']}")
                    
                except Exception as commit_error:
                    self.stats['errors'].append(f"Error committing dish '{name}': {str(commit_error)}")
                    self.db.rollback()
                    # Adjust relationship stats since this dish failed
                    self.stats['dish_ingredients_created'] -= relationships_created
                    continue

            except Exception as e:
                self.stats['errors'].append(f"Unexpected error processing dish '{name}': {str(e)}")
                self.db.rollback()
                continue

        # Final verification
        try:
            final_dish_count = self.db.query(self.Dish).count()
            final_rel_count = self.db.query(self.DishIngredient).count()
            print(f"\nFinal verification: {final_dish_count} total dishes, {final_rel_count} total relationships")
            print(f"Successfully processed {self.stats['dishes_created']} new dishes")
            return True
        except Exception as e:
            self.stats['errors'].append(f"Error in final verification: {str(e)}")
            return False

    def print_summary(self):
        """Print a summary of the seeding operation."""
        print("\n" + "="*60)
        print("DATABASE SEEDING SUMMARY")
        print("="*60)
        print(f"Ingredients processed: {self.stats['ingredients_processed']}")
        print(f"Ingredients created: {self.stats['ingredients_created']}")
        print(f"Ingredients skipped (duplicates): {self.stats['ingredients_skipped']}")
        print()
        print(f"Dishes processed: {self.stats['dishes_processed']}")
        print(f"Dishes created: {self.stats['dishes_created']}")
        print(f"Dishes skipped (duplicates): {self.stats['dishes_skipped']}")
        print()
        print(f"Dish-ingredient relationships created: {self.stats['dish_ingredients_created']}")
        print()
        print(f"Total errors: {len(self.stats['errors'])}")
        print(f"Total warnings: {len(self.stats['warnings'])}")
        
        if self.stats['errors']:
            print("\nERRORS:")
            print("-"*40)
            for i, error in enumerate(self.stats['errors'][:10], 1):  # Show first 10 errors
                print(f"{i}. {error}")
            if len(self.stats['errors']) > 10:
                print(f"... and {len(self.stats['errors']) - 10} more errors")

        if self.stats['warnings']:
            print("\nWARNINGS (first 5):")
            print("-"*40)
            for i, warning in enumerate(self.stats['warnings'][:5], 1):  # Show first 5 warnings
                print(f"{i}. {warning}")
            if len(self.stats['warnings']) > 5:
                print(f"... and {len(self.stats['warnings']) - 5} more warnings")

        print("="*60)


def main():
    """Main function to run the seeding script."""
    print("Starting database seeding process...")
    
    # Force reload environment variables to ensure we use current settings
    reload_environment()

    # File paths
    ingredients_file = "seed_data/final/ingredients.json"
    dishes_file = "seed_data/final/dishes.json"
    
    # Check if files exist
    if not os.path.exists(ingredients_file):
        print(f"Error: Ingredients file not found: {ingredients_file}")
        return False
        
    if not os.path.exists(dishes_file):
        print(f"Error: Dishes file not found: {dishes_file}")
        return False

    # Initialize database connection early to check connectivity and show info
    print("\nInitializing database connection...")
    seeder = DatabaseSeeder()
    
    try:
        # Manually call the initialization that normally happens in __enter__
        from app.db.session import SessionLocal
        from app.models.ingredient import Ingredient
        from app.models.dish import Dish
        from app.models.dish_ingredient import DishIngredient
        from app.models.user import User
        
        # Store the imports as class attributes
        seeder.SessionLocal = SessionLocal
        seeder.Ingredient = Ingredient
        seeder.Dish = Dish
        seeder.DishIngredient = DishIngredient
        seeder.User = User
        
        # Create database session
        seeder.db = SessionLocal()
        
        # Check current database state
        current_ingredients = seeder.db.query(Ingredient).count()
        current_dishes = seeder.db.query(Dish).count()
        current_relationships = seeder.db.query(DishIngredient).count()
        
        print(f"✅ Database connection successful!")
        print(f"📊 Current database state:")
        print(f"   - Ingredients: {current_ingredients}")
        print(f"   - Dishes: {current_dishes}")
        print(f"   - Dish-Ingredient relationships: {current_relationships}")
        print(f"📁 Files to process:")
        print(f"   - Ingredients file: {ingredients_file}")
        print(f"   - Dishes file: {dishes_file}")
        
        # Get confirmation from user
        print("\n" + "="*60)
        confirmation = input("🚀 Do you want to continue with database seeding? (yes/y to continue): ").strip().lower()
        
        if confirmation not in ['yes', 'y']:
            print("❌ Seeding cancelled by user.")
            seeder.db.close()
            return False
            
        print("✅ Proceeding with database seeding...\n")
        
    except Exception as e:
        print(f"❌ Error initializing database connection: {str(e)}")
        print("Please check your database configuration and try again.")
        if seeder.db:
            seeder.db.close()
        return False

    try:
        # Load ingredients first (required for dishes)
        if not seeder.load_ingredients(ingredients_file):
            print("Failed to load ingredients. Stopping.")
            seeder.print_summary()
            return False

        # Load dishes and their ingredient relationships
        if not seeder.load_dishes(dishes_file):
            print("Failed to load dishes.")
            seeder.print_summary()
            return False

        # Print final summary
        seeder.print_summary()
        return True

    except Exception as e:
        print(f"Unexpected error during seeding: {str(e)}")
        return False
    finally:
        # Ensure database connection is closed
        if seeder.db:
            seeder.db.close()


if __name__ == "__main__":
    success = main()
    if success:
        print("\nDatabase seeding completed successfully!")
        sys.exit(0)
    else:
        print("\nDatabase seeding failed!")
        sys.exit(1) 