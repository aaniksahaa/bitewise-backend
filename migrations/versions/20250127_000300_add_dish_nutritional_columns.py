"""add nutritional columns to dishes table

Revision ID: 20250127_000300_add_dish_nutritional_columns
Revises: add_intakes_fitness_posts_comments_conversations_messages
Create Date: 2025-01-27 00:03:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250127_000300_add_dish_nutritional_columns'
down_revision = 'add_intakes_fitness_posts_comments_conversations_messages'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing vitamin and mineral columns to dishes table
    op.add_column('dishes', sa.Column('zinc_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('magnesium_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_a_mcg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b1_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b2_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b3_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b5_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b6_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b9_mcg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_b12_mcg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_c_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_d_mcg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_e_mg', sa.DECIMAL(10, 2)))
    op.add_column('dishes', sa.Column('vit_k_mcg', sa.DECIMAL(10, 2)))


def downgrade():
    # Remove the added vitamin and mineral columns
    op.drop_column('dishes', 'vit_k_mcg')
    op.drop_column('dishes', 'vit_e_mg')
    op.drop_column('dishes', 'vit_d_mcg')
    op.drop_column('dishes', 'vit_c_mg')
    op.drop_column('dishes', 'vit_b12_mcg')
    op.drop_column('dishes', 'vit_b9_mcg')
    op.drop_column('dishes', 'vit_b6_mg')
    op.drop_column('dishes', 'vit_b5_mg')
    op.drop_column('dishes', 'vit_b3_mg')
    op.drop_column('dishes', 'vit_b2_mg')
    op.drop_column('dishes', 'vit_b1_mg')
    op.drop_column('dishes', 'vit_a_mcg')
    op.drop_column('dishes', 'magnesium_mg')
    op.drop_column('dishes', 'zinc_mg') 