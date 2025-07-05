# Local Database Setup Guide

This guide will help you set up a new local PostgreSQL database, run Alembic migrations, and seed it with data.

## Prerequisites

- PostgreSQL installed and running locally
- DBeaver (or another database client) for database management
- Python environment with all dependencies installed

## Step 1: Create New Database in DBeaver

1. **Open DBeaver** and connect to your local PostgreSQL server
2. **Create a new database:**
   - Right-click on your PostgreSQL connection listed on left like 'bitewise_dev'
   - select Databases, then right click -> create new db
   - Enter database name (e.g., `bitewise_test`)
   - Click "OK"

## Step 2: Update Environment Configuration

### Option A: Create New Environment File
Create a new `.env` file in your project root:

```bash
# Copy your existing .env file
cp .env .env
```

Then edit `.env` and update the database URL:
```env
ENVIRONMENT=development
LOCAL_DATABASE_URL=postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_test
```

### Option B: Temporarily Update Existing .env
Edit your existing `.env` file and change the database name:
```env
LOCAL_DATABASE_URL=postgresql://bitewise:BITEWISE321@localhost:5432/bitewise_test
```

## Step 3: Install Dependencies (if not already done)

```bash
# Install all Python dependencies
pip install -r requirements.txt
```

## Step 4: Run Database Migrations

### Method 1: Using Alembic directly
```bash
# Run all migrations to set up the complete schema
alembic upgrade head
```

### Method 2: Using Make command (if you have Docker setup)
```bash
# If using Docker
make migrate
```

### Verify Migration Success
Check that all tables were created:
```bash
# Connect to your database and verify tables exist
psql -h localhost -U bitewise -d bitewise_test -c "\dt"
```

Expected tables after migration:
- `users`
- `user_profiles`
- `otps`
- `refresh_tokens`
- `password_reset_requests`
- `llm_models`
- `ingredients`
- `dishes`
- `dish_ingredients`
- `intakes`
- `fitness_plans`
- `posts`
- `comments`
- `conversations`
- `messages`
- `alembic_version`

## Step 5: Seed Database with Initial Data

### 5.1 Seed LLM Models (Basic seed data)
```bash
# Seed LLM models table
python seed_data/seed_llm_models.py
```

### 5.2 Seed Ingredients and Dishes (Main data)
```bash
# Seed ingredients and dishes from JSON files
python seed_dish_ingreds.py
```

### 5.3 Seed Users and User Profiles (Optional)
```bash
# Seed users and user profiles from CSV files
python seed_users.py
```

## Step 6: Verify Database Setup

### Check Database Connection
```bash
# Test database connection
python -c "
from app.db.session import SessionLocal
from app.models.user import User
from app.models.ingredient import Ingredient
from app.models.dish import Dish
from app.models.llm_model import LLMModel

db = SessionLocal()
try:
    print('Database connection successful!')
    print(f'Users: {db.query(User).count()}')
    print(f'Ingredients: {db.query(Ingredient).count()}')
    print(f'Dishes: {db.query(Dish).count()}')
    print(f'LLM Models: {db.query(LLMModel).count()}')
finally:
    db.close()
"
```

### Check in DBeaver
1. Refresh your database connection in DBeaver
2. Navigate to your new database
3. Check that all tables exist and contain data

## Step 7: Test Your Application

```bash
# Start the FastAPI application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/api/v1/docs` to test the API endpoints.

## Troubleshooting

### Common Issues and Solutions

**1. Database Connection Error**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql
# or
pg_isready -h localhost -p 5432 -U bitewise
```

**2. Permission Denied**
```bash
# Make sure the bitewise user has proper permissions
psql -h localhost -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE bitewise_test TO bitewise;"
```

**3. Migration Fails**
```bash
# Check current migration status
alembic current

# If needed, reset migrations (WARNING: This will drop all data)
alembic downgrade base
alembic upgrade head
```

**4. Seeding Fails**
```bash
# Check if seed data files exist
ls -la seed_data/
ls -la seed_data/final/
ls -la seed_data/user-data/

# Run seed scripts with more verbose output
python seed_dish_ingreds.py --verbose
```

**5. Environment Variables Not Loading**
```bash
# Verify environment variables are set
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('ENVIRONMENT:', os.getenv('ENVIRONMENT'))
print('LOCAL_DATABASE_URL:', os.getenv('LOCAL_DATABASE_URL'))
"
```

## Quick Setup Commands (All-in-One)

```bash
# 1. Create database (do this in DBeaver first)
# 2. Update .env file with new database name
# 3. Run all setup commands
alembic upgrade head
python seed_data/seed_llm_models.py
python seed_dish_ingreds.py
python seed_users.py  # optional
```

## Reverting Changes

If you want to go back to your original database:

```bash
# 1. Update .env file back to original database name
# 2. Or delete the test database in DBeaver
# 3. Your original database remains unchanged
```

## Notes

- The original database (`bitewise_dev`) remains untouched
- All seed scripts include duplicate checking, so running them multiple times is safe
- The seeding process will show progress and summary statistics
- Make sure to backup important data before making changes
- Use different database names for different testing scenarios

## Database Schema Overview

After successful setup, your database will have:
- **Authentication system**: Users, OTPs, refresh tokens, password resets
- **User profiles**: Extended user information with preferences
- **Content system**: Ingredients, dishes, and their relationships
- **Social features**: Posts, comments, conversations, messages
- **Fitness tracking**: Intakes, fitness plans
- **AI integration**: LLM models configuration

Your database is now ready for development and testing! 