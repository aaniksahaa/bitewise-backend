"""add menus and menu_dishes tables

Revision ID: 20250127_000400_add_menus_and_menu_dishes_tables
Revises: 20250127_000300_add_dish_nutritional_columns
Create Date: 2025-01-27 00:04:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250127_000400_add_menus_and_menu_dishes_tables'
down_revision = '20250127_000300_add_dish_nutritional_columns'
branch_labels = None
depends_on = None


def upgrade():
    # Create menus table
    op.create_table('menus',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('occasion', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create menu_dishes table
    op.create_table('menu_dishes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('menu_id', sa.BigInteger(), nullable=False),
        sa.Column('dish_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['dish_id'], ['dishes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['menu_id'], ['menus.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('menu_id', 'dish_id', name='uix_menu_dish')
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table('menu_dishes')
    op.drop_table('menus') 