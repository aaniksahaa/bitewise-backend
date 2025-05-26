"""add user_profiles table

Revision ID: add_user_profiles_table
Revises: add_llm_models
Create Date: 2024-05-26 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

# revision identifiers, used by Alembic.
revision = 'add_user_profiles_table'
down_revision = 'add_llm_models'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('first_name', sa.String(length=50)),
        sa.Column('last_name', sa.String(length=50)),
        sa.Column('gender', sa.String(length=20)),  # Simple string instead of enum for now
        sa.Column('date_of_birth', sa.Date()),
        sa.Column('location_city', sa.String(length=100)),
        sa.Column('location_country', sa.String(length=100)),
        sa.Column('latitude', sa.Numeric(9, 6)),
        sa.Column('longitude', sa.Numeric(9, 6)),
        sa.Column('profile_image_url', sa.String(length=255)),
        sa.Column('bio', sa.Text()),
        sa.Column('dietary_restrictions', psql.ARRAY(sa.Text)),
        sa.Column('allergies', psql.ARRAY(sa.Text)),
        sa.Column('medical_conditions', psql.ARRAY(sa.Text)),
        sa.Column('fitness_goals', psql.ARRAY(sa.Text)),
        sa.Column('taste_preferences', psql.ARRAY(sa.Text)),
        sa.Column('cuisine_interests', psql.ARRAY(sa.Text)),
        sa.Column('cooking_skill_level', sa.String(length=20), server_default='beginner'),  # Simple string instead of enum for now
        sa.Column('email_notifications_enabled', sa.Boolean(), server_default=sa.text('TRUE')),
        sa.Column('push_notifications_enabled', sa.Boolean(), server_default=sa.text('TRUE')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

def downgrade():
    op.drop_table('user_profiles') 