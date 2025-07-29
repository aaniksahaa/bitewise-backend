"""fix_unique_constraints_restored

Revision ID: 8000c754e962
Revises: e44dc97dd68c
Create Date: 2025-07-27 00:12:18.951164

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '8000c754e962'
down_revision = 'e44dc97dd68c'
branch_labels = None
depends_on = None


def upgrade():
    # ### Manually corrected - CREATE constraints to match current database state ###
    # These constraints were restored via Supabase migrations and should exist
    # Use conditional logic to avoid errors if constraints already exist
    
    # Check and create constraints conditionally
    connection = op.get_bind()
    
    # Users email constraint
    result = connection.execute(text(
        "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'users_email_key' AND table_name = 'users'"
    )).fetchone()
    if not result:
        op.create_unique_constraint('users_email_key', 'users', ['email'])
    
    # Users username constraint  
    result = connection.execute(text(
        "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'users_username_key' AND table_name = 'users'"
    )).fetchone()
    if not result:
        op.create_unique_constraint('users_username_key', 'users', ['username'])
    
    # Refresh tokens constraint
    result = connection.execute(text(
        "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'refresh_tokens_token_key' AND table_name = 'refresh_tokens'"
    )).fetchone()
    if not result:
        op.create_unique_constraint('refresh_tokens_token_key', 'refresh_tokens', ['token'])
    
    # Password reset requests constraint
    result = connection.execute(text(
        "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'password_reset_requests_request_id_key' AND table_name = 'password_reset_requests'"
    )).fetchone()
    if not result:
        op.create_unique_constraint('password_reset_requests_request_id_key', 'password_reset_requests', ['request_id'])
    # ### end corrected commands ###


def downgrade():
    # ### Drop constraints if rolling back ###
    op.drop_constraint('password_reset_requests_request_id_key', 'password_reset_requests', type_='unique')
    op.drop_constraint('refresh_tokens_token_key', 'refresh_tokens', type_='unique')
    op.drop_constraint('users_username_key', 'users', type_='unique')
    op.drop_constraint('users_email_key', 'users', type_='unique')
    # ### end commands ### 