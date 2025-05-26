"""add ingredients, dishes, and dish_ingredients tables

Revision ID: add_ingredients_and_dishes_tables
Revises: add_user_profiles_table
Create Date: 2024-05-26 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

# revision identifiers, used by Alembic.
revision = 'add_ingredients_and_dishes_tables'
down_revision = 'add_user_profiles_table'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'ingredients',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), unique=True, nullable=False),
        sa.Column('serving_size', sa.Numeric(10, 2), nullable=False),
        sa.Column('calories', sa.Numeric(10, 2)),
        sa.Column('protein_g', sa.Numeric(10, 2)),
        sa.Column('carbs_g', sa.Numeric(10, 2)),
        sa.Column('fats_g', sa.Numeric(10, 2)),
        sa.Column('sat_fats_g', sa.Numeric(10, 2)),
        sa.Column('unsat_fats_g', sa.Numeric(10, 2)),
        sa.Column('trans_fats_g', sa.Numeric(10, 2)),
        sa.Column('fiber_g', sa.Numeric(10, 2)),
        sa.Column('sugar_g', sa.Numeric(10, 2)),
        sa.Column('calcium_mg', sa.Numeric(10, 2)),
        sa.Column('iron_mg', sa.Numeric(10, 2)),
        sa.Column('potassium_mg', sa.Numeric(10, 2)),
        sa.Column('sodium_mg', sa.Numeric(10, 2)),
        sa.Column('zinc_mg', sa.Numeric(10, 2)),
        sa.Column('magnesium_mg', sa.Numeric(10, 2)),
        sa.Column('vit_a_mcg', sa.Numeric(10, 2)),
        sa.Column('vit_b1_mg', sa.Numeric(10, 2)),
        sa.Column('vit_b2_mg', sa.Numeric(10, 2)),
        sa.Column('vit_b3_mg', sa.Numeric(10, 2)),
        sa.Column('vit_b5_mg', sa.Numeric(10, 2)),
        sa.Column('vit_b6_mg', sa.Numeric(10, 2)),
        sa.Column('vit_b9_mcg', sa.Numeric(10, 2)),
        sa.Column('vit_b12_mcg', sa.Numeric(10, 2)),
        sa.Column('vit_c_mg', sa.Numeric(10, 2)),
        sa.Column('vit_d_mcg', sa.Numeric(10, 2)),
        sa.Column('vit_e_mg', sa.Numeric(10, 2)),
        sa.Column('vit_k_mcg', sa.Numeric(10, 2)),
        sa.Column('image_url', sa.String(length=255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'dishes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('cuisine', sa.String(length=50)),
        sa.Column('created_by_user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('cooking_steps', psql.ARRAY(sa.Text)),
        sa.Column('prep_time_minutes', sa.Integer()),
        sa.Column('cook_time_minutes', sa.Integer()),
        sa.Column('image_urls', psql.ARRAY(sa.String(length=255))),
        sa.Column('servings', sa.Integer()),
        sa.Column('calories', sa.Numeric(10, 2)),
        sa.Column('protein_g', sa.Numeric(10, 2)),
        sa.Column('carbs_g', sa.Numeric(10, 2)),
        sa.Column('fats_g', sa.Numeric(10, 2)),
        sa.Column('sat_fats_g', sa.Numeric(10, 2)),
        sa.Column('unsat_fats_g', sa.Numeric(10, 2)),
        sa.Column('trans_fats_g', sa.Numeric(10, 2)),
        sa.Column('fiber_g', sa.Numeric(10, 2)),
        sa.Column('sugar_g', sa.Numeric(10, 2)),
        sa.Column('calcium_mg', sa.Numeric(10, 2)),
        sa.Column('iron_mg', sa.Numeric(10, 2)),
        sa.Column('potassium_mg', sa.Numeric(10, 2)),
        sa.Column('sodium_mg', sa.Numeric(10, 2)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'dish_ingredients',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('dish_id', sa.BigInteger(), sa.ForeignKey('dishes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ingredient_id', sa.BigInteger(), sa.ForeignKey('ingredients.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.UniqueConstraint('dish_id', 'ingredient_id', name='uix_dish_ingredient'),
    )

def downgrade():
    op.drop_table('dish_ingredients')
    op.drop_table('dishes')
    op.drop_table('ingredients') 