#!/bin/bash
set -e

echo "Starting Bitewise API..."

# Wait for database to be ready (skip for external databases like Supabase)
if [[ "$DATABASE_URL" == *"supabase"* ]]; then
    echo "Using external Supabase database, skipping connection wait..."
else
    echo "Waiting for database to be ready..."
    while ! pg_isready -h "${DATABASE_HOST:-db}" -p "${DATABASE_PORT:-5432}" -U "${DATABASE_USER:-bitewise}" > /dev/null 2>&1; do
        echo "Waiting for database..."
        sleep 2
    done
    echo "Database is ready!"
fi

# Run database migrations
# echo "Running database migrations..."
# if [ "$ENVIRONMENT" = "development" ]; then
#     alembic upgrade head || echo "Migration failed or no migrations to run"
# else
#     alembic upgrade head
# fi

# Seed data if needed (optional)
# if [ "$SEED_DATA" = "true" ]; then
#     echo "Seeding database..."
#     python seed_data/seed_llm_models.py || echo "Seeding failed or already done"
# fi

echo "Starting FastAPI application..."
exec "$@" 