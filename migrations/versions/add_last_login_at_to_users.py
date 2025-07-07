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
    # Add last_login_at column to users table
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))


def downgrade():
    # Remove last_login_at column from users table
    op.drop_column('users', 'last_login_at') 