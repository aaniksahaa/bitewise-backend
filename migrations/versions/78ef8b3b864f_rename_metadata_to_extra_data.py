"""rename_metadata_to_extra_data

Revision ID: 78ef8b3b864f
Revises: 20250127_000400_add_menus_and_menu_dishes_tables
Create Date: 2025-05-27 03:00:40.868942

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '78ef8b3b864f'
down_revision = '20250127_000400_add_menus_and_menu_dishes_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Rename metadata column to extra_data in conversations table
    op.alter_column('conversations', 'metadata', new_column_name='extra_data')
    
    # Rename metadata column to extra_data in messages table
    op.alter_column('messages', 'metadata', new_column_name='extra_data')


def downgrade():
    # Rename extra_data column back to metadata in conversations table
    op.alter_column('conversations', 'extra_data', new_column_name='metadata')
    
    # Rename extra_data column back to metadata in messages table
    op.alter_column('messages', 'extra_data', new_column_name='metadata') 