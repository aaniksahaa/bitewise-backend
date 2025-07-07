#!/usr/bin/env python3
"""
Comprehensive script to seed the database with users and user profiles from CSV files.
This script handles auto-incrementing IDs, duplication checking, dependency management,
and comprehensive error handling.
"""

import csv
import sys
import os
from datetime import datetime, date
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


class UserSeeder:
    def __init__(self):
        self.db: Optional[Session] = None
        self.user_id_mapping: Dict[int, int] = {}  # Maps CSV user_id to DB user_id
        self.stats = {
            'users_processed': 0,
            'users_created': 0,
            'users_skipped': 0,
            'profiles_processed': 0,
            'profiles_created': 0,
            'profiles_skipped': 0,
            'errors': [],
            'warnings': []
        }

    def __enter__(self):
        # Import database modules after environment is reloaded
        from app.db.session import SessionLocal
        from app.models.user import User
        from app.models.user_profile import UserProfile, GenderType, CookingSkillLevelType
        from app.services.auth import AuthService
        
        # Store the imports as class attributes
        self.SessionLocal = SessionLocal
        self.User = User
        self.UserProfile = UserProfile
        self.GenderType = GenderType
        self.CookingSkillLevelType = CookingSkillLevelType
        self.AuthService = AuthService
        
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
        if value is None or value == '':
            return None
        try:
            return Decimal(str(value))
        except (TypeError, ValueError):
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

    def safe_date(self, date_str: str) -> Optional[date]:
        """Safely parse date string to date object."""
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            # Try different date formats
            for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']:
                try:
                    return datetime.strptime(date_str.strip(), fmt).date()
                except ValueError:
                    continue
            
            # If no format worked, log error
            self.stats['errors'].append(f"Invalid date format: {date_str}")
            return None
            
        except Exception as e:
            self.stats['errors'].append(f"Error parsing date '{date_str}': {str(e)}")
            return None

    def safe_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Safely parse datetime string to datetime object."""
        if not datetime_str or datetime_str.strip() == '':
            return None
        
        try:
            # Try different datetime formats, including timezone-aware formats
            formats = [
                '%Y-%m-%d %H:%M:%S.%f%z',     # 2025-06-24 19:10:14.083781+00
                '%Y-%m-%d %H:%M:%S%z',        # 2025-06-24 19:10:14+00
                '%Y-%m-%d %H:%M:%S.%f',       # 2025-06-24 19:10:14.083781
                '%Y-%m-%d %H:%M:%S',          # 2025-06-24 19:10:14
                '%Y-%m-%d %H:%M:%S.%f+00:00', # Alternative timezone format
                '%Y-%m-%d %H:%M:%S+00:00',    # Alternative timezone format
            ]
            
            datetime_str = datetime_str.strip()
            
            # Handle the specific format from your CSV: "2025-06-24 19:10:14.083781+00"
            # Convert "+00" to "+0000" for proper parsing
            if datetime_str.endswith('+00'):
                datetime_str = datetime_str[:-3] + '+0000'
            
            for fmt in formats:
                try:
                    return datetime.strptime(datetime_str, fmt)
                except ValueError:
                    continue
            
            # If no format worked, log error
            self.stats['errors'].append(f"Invalid datetime format: {datetime_str}")
            return None
            
        except Exception as e:
            self.stats['errors'].append(f"Error parsing datetime '{datetime_str}': {str(e)}")
            return None

    def safe_boolean(self, value: str) -> bool:
        """Safely convert string to boolean."""
        if isinstance(value, bool):
            return value
        if not value:
            return False
        return str(value).lower() in ['true', '1', 'yes', 'on']

    def parse_array_field(self, value: str) -> Optional[List[str]]:
        """Parse array field from CSV (expecting JSON-like format)."""
        if not value or value.strip() == '':
            return None
        
        try:
            # Remove outer quotes and brackets, then split by comma
            value = value.strip().strip('"').strip("'")
            if value.startswith('[') and value.endswith(']'):
                value = value[1:-1]
            
            if not value:
                return None
                
            # Split by comma and clean each item
            items = []
            for item in value.split(','):
                item = item.strip().strip('"').strip("'")
                if item:
                    items.append(item)
            
            return items if items else None
            
        except Exception as e:
            self.stats['errors'].append(f"Error parsing array field '{value}': {str(e)}")
            return None

    def check_user_exists(self, email: str, username: str) -> Optional['User']:
        """Check if a user already exists by email or username."""
        try:
            return self.db.query(self.User).filter(
                (self.User.email == email) | (self.User.username == username)
            ).first()
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error checking user '{email}': {str(e)}")
            return None

    def check_profile_exists(self, user_id: int) -> Optional['UserProfile']:
        """Check if a user profile already exists."""
        try:
            return self.db.query(self.UserProfile).filter(
                self.UserProfile.user_id == user_id
            ).first()
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error checking profile for user_id {user_id}: {str(e)}")
            return None

    def create_user(self, user_data: dict) -> Optional['User']:
        """Create a new user from CSV data."""
        try:
            # Extract and validate required fields
            email = user_data.get('email', '').strip()
            username = user_data.get('username', '').strip()
            
            if not email or not username:
                self.stats['errors'].append(f"User missing email or username: {user_data}")
                return None

            # Hash password if provided
            hashed_password = None
            if user_data.get('hashed_password'):
                # If already hashed, use as-is
                hashed_password = user_data['hashed_password']
            elif user_data.get('password'):
                # If plain password, hash it
                hashed_password = self.AuthService.get_password_hash(user_data['password'])

            # Create user with all available data
            user = self.User(
                email=email,
                username=username,
                full_name=user_data.get('full_name', '').strip() or None,
                hashed_password=hashed_password,
                is_active=self.safe_boolean(user_data.get('is_active', True)),
                is_verified=self.safe_boolean(user_data.get('is_verified', True)),
                is_superuser=self.safe_boolean(user_data.get('is_superuser', False)),
                oauth_provider=user_data.get('oauth_provider', '').strip() or None,
                oauth_id=user_data.get('oauth_id', '').strip() or None,
                created_at=self.safe_datetime(user_data.get('created_at')) or datetime.utcnow(),
                updated_at=self.safe_datetime(user_data.get('updated_at')) or datetime.utcnow()
            )

            self.db.add(user)
            self.db.flush()  # Get the ID without committing
            return user

        except (SQLAlchemyError, IntegrityError) as e:
            self.stats['errors'].append(f"Error creating user '{email}': {str(e)}")
            self.db.rollback()
            return None
        except Exception as e:
            self.stats['errors'].append(f"Unexpected error creating user '{email}': {str(e)}")
            self.db.rollback()
            return None

    def create_profile(self, profile_data: dict, user_id: int) -> Optional['UserProfile']:
        """Create a new user profile from CSV data."""
        try:
            # Parse gender enum
            gender_str = profile_data.get('gender', '').strip().lower()
            gender = None
            if gender_str in ['male', 'female', 'other']:
                gender = getattr(self.GenderType, gender_str)
            
            if not gender:
                self.stats['errors'].append(f"Invalid or missing gender for user_id {user_id}: {gender_str}")
                return None

            # Parse cooking skill level enum
            cooking_skill_str = profile_data.get('cooking_skill_level', 'beginner').strip().lower()
            cooking_skill = self.CookingSkillLevelType.beginner  # Default
            if cooking_skill_str in ['beginner', 'intermediate', 'advanced']:
                cooking_skill = getattr(self.CookingSkillLevelType, cooking_skill_str)

            # Parse required numeric fields
            height_cm = self.safe_decimal(profile_data.get('height_cm'))
            weight_kg = self.safe_decimal(profile_data.get('weight_kg'))
            date_of_birth = self.safe_date(profile_data.get('date_of_birth'))

            if not height_cm or not weight_kg or not date_of_birth:
                self.stats['errors'].append(f"Missing required fields for user_id {user_id}: height_cm={height_cm}, weight_kg={weight_kg}, date_of_birth={date_of_birth}")
                return None

            # Create profile with all available data
            profile = self.UserProfile(
                user_id=user_id,
                first_name=self.safe_string(profile_data.get('first_name', ''), 50, "first_name") or None,
                last_name=self.safe_string(profile_data.get('last_name', ''), 50, "last_name") or None,
                gender=gender,
                height_cm=height_cm,
                weight_kg=weight_kg,
                date_of_birth=date_of_birth,
                location_city=self.safe_string(profile_data.get('location_city', ''), 100, "location_city") or None,
                location_country=self.safe_string(profile_data.get('location_country', ''), 100, "location_country") or None,
                latitude=self.safe_decimal(profile_data.get('latitude')),
                longitude=self.safe_decimal(profile_data.get('longitude')),
                profile_image_url=self.safe_string(profile_data.get('profile_image_url', ''), 255, "profile_image_url") or None,
                bio=profile_data.get('bio', '').strip() or None,
                dietary_restrictions=self.parse_array_field(profile_data.get('dietary_restrictions', '')),
                allergies=self.parse_array_field(profile_data.get('allergies', '')),
                medical_conditions=self.parse_array_field(profile_data.get('medical_conditions', '')),
                fitness_goals=self.parse_array_field(profile_data.get('fitness_goals', '')),
                taste_preferences=self.parse_array_field(profile_data.get('taste_preferences', '')),
                cuisine_interests=self.parse_array_field(profile_data.get('cuisine_interests', '')),
                cooking_skill_level=cooking_skill,
                email_notifications_enabled=self.safe_boolean(profile_data.get('email_notifications_enabled', True)),
                push_notifications_enabled=self.safe_boolean(profile_data.get('push_notifications_enabled', True)),
                created_at=self.safe_datetime(profile_data.get('created_at')) or datetime.utcnow(),
                updated_at=self.safe_datetime(profile_data.get('updated_at')) or datetime.utcnow()
            )

            self.db.add(profile)
            self.db.flush()  # Get the ID without committing
            return profile

        except (SQLAlchemyError, IntegrityError) as e:
            self.stats['errors'].append(f"Error creating profile for user_id {user_id}: {str(e)}")
            self.db.rollback()
            return None
        except Exception as e:
            self.stats['errors'].append(f"Unexpected error creating profile for user_id {user_id}: {str(e)}")
            self.db.rollback()
            return None

    def load_users(self, file_path: str) -> bool:
        """Load and process users from CSV file."""
        print(f"Loading users from {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                users_data = list(reader)
        except FileNotFoundError:
            self.stats['errors'].append(f"Users file not found: {file_path}")
            return False
        except Exception as e:
            self.stats['errors'].append(f"Error reading users file: {str(e)}")
            return False

        print(f"Found {len(users_data)} users to process")

        for user_data in users_data:
            self.stats['users_processed'] += 1
            
            if self.stats['users_processed'] % 10 == 0:
                print(f"Processed {self.stats['users_processed']} users...")

            email = user_data.get('email', '').strip()
            username = user_data.get('username', '').strip()
            csv_user_id = user_data.get('id', '').strip()

            if not email or not username or not csv_user_id:
                self.stats['errors'].append(f"User missing required fields: {user_data}")
                continue

            # Check if user already exists
            existing_user = self.check_user_exists(email, username)
            if existing_user:
                self.stats['users_skipped'] += 1
                # Store the mapping for profile creation
                try:
                    self.user_id_mapping[int(csv_user_id)] = existing_user.id
                except ValueError:
                    self.stats['errors'].append(f"Invalid CSV user_id: {csv_user_id}")
                continue

            # Create new user
            new_user = self.create_user(user_data)
            if new_user:
                self.stats['users_created'] += 1
                # Store the mapping for profile creation
                try:
                    self.user_id_mapping[int(csv_user_id)] = new_user.id
                except ValueError:
                    self.stats['errors'].append(f"Invalid CSV user_id: {csv_user_id}")
            else:
                self.stats['errors'].append(f"Failed to create user: {email}")

        # Commit all user changes
        try:
            self.db.commit()
            print(f"Successfully committed {self.stats['users_created']} new users")
            
            # Verify the commit by counting users in database
            actual_user_count = self.db.query(self.User).count()
            print(f"Verification: Database now contains {actual_user_count} total users")
            
            return True
        except SQLAlchemyError as e:
            self.stats['errors'].append(f"Error committing users: {str(e)}")
            self.db.rollback()
            return False

    def load_profiles(self, file_path: str) -> bool:
        """Load and process user profiles from CSV file."""
        print(f"Loading user profiles from {file_path}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                profiles_data = list(reader)
        except FileNotFoundError:
            self.stats['errors'].append(f"Profiles file not found: {file_path}")
            return False
        except Exception as e:
            self.stats['errors'].append(f"Error reading profiles file: {str(e)}")
            return False

        print(f"Found {len(profiles_data)} profiles to process")

        for profile_data in profiles_data:
            self.stats['profiles_processed'] += 1
            
            if self.stats['profiles_processed'] % 10 == 0:
                print(f"Processed {self.stats['profiles_processed']} profiles...")

            csv_user_id = profile_data.get('user_id', '').strip()
            if not csv_user_id:
                self.stats['errors'].append(f"Profile missing user_id: {profile_data}")
                continue

            # Get the actual database user_id from our mapping
            try:
                db_user_id = self.user_id_mapping.get(int(csv_user_id))
            except ValueError:
                self.stats['errors'].append(f"Invalid CSV user_id: {csv_user_id}")
                continue

            if not db_user_id:
                self.stats['errors'].append(f"User not found for profile user_id: {csv_user_id}")
                continue

            # Check if profile already exists
            existing_profile = self.check_profile_exists(db_user_id)
            if existing_profile:
                self.stats['profiles_skipped'] += 1
                print(f"Skipping existing profile for user_id: {db_user_id}")
                continue

            # Create new profile with individual commit
            try:
                new_profile = self.create_profile(profile_data, db_user_id)
                if not new_profile:
                    continue  # Error already logged in create_profile

                # Commit this profile immediately
                try:
                    self.db.commit()
                    self.stats['profiles_created'] += 1
                    
                    if self.stats['profiles_created'] % 5 == 0:  # Progress update every 5 profiles
                        print(f"  ✅ Committed profile for user_id {db_user_id}. Total profiles: {self.stats['profiles_created']}")
                    
                except Exception as commit_error:
                    self.stats['errors'].append(f"Error committing profile for user_id {db_user_id}: {str(commit_error)}")
                    self.db.rollback()
                    continue

            except Exception as e:
                self.stats['errors'].append(f"Unexpected error processing profile for user_id {db_user_id}: {str(e)}")
                self.db.rollback()
                continue

        # Final verification
        try:
            final_profile_count = self.db.query(self.UserProfile).count()
            print(f"\nFinal verification: {final_profile_count} total profiles")
            print(f"Successfully processed {self.stats['profiles_created']} new profiles")
            return True
        except Exception as e:
            self.stats['errors'].append(f"Error in final verification: {str(e)}")
            return False

    def print_summary(self):
        """Print a summary of the seeding operation."""
        print("\n" + "="*60)
        print("USER DATABASE SEEDING SUMMARY")
        print("="*60)
        print(f"Users processed: {self.stats['users_processed']}")
        print(f"Users created: {self.stats['users_created']}")
        print(f"Users skipped (duplicates): {self.stats['users_skipped']}")
        print()
        print(f"Profiles processed: {self.stats['profiles_processed']}")
        print(f"Profiles created: {self.stats['profiles_created']}")
        print(f"Profiles skipped (duplicates): {self.stats['profiles_skipped']}")
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
    print("Starting user database seeding process...")
    
    # Force reload environment variables to ensure we use current settings
    reload_environment()

    # File paths
    users_file = "seed_data/user-data/users_rows.csv"
    profiles_file = "seed_data/user-data/user_profiles_rows.csv"
    
    # Check if files exist
    if not os.path.exists(users_file):
        print(f"Error: Users file not found: {users_file}")
        return False
        
    if not os.path.exists(profiles_file):
        print(f"Error: Profiles file not found: {profiles_file}")
        return False

    # Initialize database connection early to check connectivity and show info
    print("\nInitializing database connection...")
    seeder = UserSeeder()
    
    try:
        # Manually call the initialization that normally happens in __enter__
        from app.db.session import SessionLocal
        from app.models.user import User
        from app.models.user_profile import UserProfile, GenderType, CookingSkillLevelType
        from app.services.auth import AuthService
        
        # Store the imports as class attributes
        seeder.SessionLocal = SessionLocal
        seeder.User = User
        seeder.UserProfile = UserProfile
        seeder.GenderType = GenderType
        seeder.CookingSkillLevelType = CookingSkillLevelType
        seeder.AuthService = AuthService
        
        # Create database session
        seeder.db = SessionLocal()
        
        # Check current database state
        current_users = seeder.db.query(User).count()
        current_profiles = seeder.db.query(UserProfile).count()
        
        print(f"✅ Database connection successful!")
        print(f"📊 Current database state:")
        print(f"   - Users: {current_users}")
        print(f"   - User Profiles: {current_profiles}")
        print(f"📁 Files to process:")
        print(f"   - Users file: {users_file}")
        print(f"   - Profiles file: {profiles_file}")
        
        # Get confirmation from user
        print("\n" + "="*60)
        confirmation = input("🚀 Do you want to continue with user database seeding? (yes/y to continue): ").strip().lower()
        
        if confirmation not in ['yes', 'y']:
            print("❌ Seeding cancelled by user.")
            seeder.db.close()
            return False
            
        print("✅ Proceeding with user database seeding...\n")
        
    except Exception as e:
        print(f"❌ Error initializing database connection: {str(e)}")
        print("Please check your database configuration and try again.")
        if seeder.db:
            seeder.db.close()
        return False

    try:
        # Load users first (required for profiles)
        if not seeder.load_users(users_file):
            print("Failed to load users. Stopping.")
            seeder.print_summary()
            return False

        # Load profiles (depends on users)
        if not seeder.load_profiles(profiles_file):
            print("Failed to load profiles.")
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
        print("\nUser database seeding completed successfully!")
        sys.exit(0)
    else:
        print("\nUser database seeding failed!")
        sys.exit(1) 