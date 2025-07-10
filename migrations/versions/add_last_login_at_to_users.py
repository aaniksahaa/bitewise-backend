"""add last_login_at to users table

Revision ID: add_last_login_at_to_users
Revises: create_health_history_trigger
Create Date: 2024-12-19 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_last_login_at_to_users"
down_revision = "create_health_history_trigger"
branch_labels = None
depends_on = None


def upgrade():
    # Add last_login_at column to users table with explicit SQL for better performance
    connection = op.get_bind()
    
    # Check if column already exists to avoid errors on retry
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'last_login_at'
    """))
    
    if not result.fetchone():
        # Use raw SQL with explicit timeout handling
        connection.execute(sa.text("SET statement_timeout = '300s'"))  # 5 minutes
        connection.execute(sa.text(
            "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITHOUT TIME ZONE"
        ))
        print("✓ Added last_login_at column to users table")
    else:
        print("✓ last_login_at column already exists, skipping")


def downgrade():
    # Remove last_login_at column from users table
    connection = op.get_bind()
    
    # Check if column exists before dropping
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'last_login_at'
    """))
    
    if result.fetchone():
        connection.execute(sa.text("SET statement_timeout = '300s'"))
        connection.execute(sa.text("ALTER TABLE users DROP COLUMN last_login_at"))
        print("✓ Removed last_login_at column from users table")
    else:
        print("✓ last_login_at column doesn't exist, skipping") 