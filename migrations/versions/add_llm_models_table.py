"""add llm models table

Revision ID: add_llm_models
Revises: create_auth_tables
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_llm_models'
down_revision = 'create_auth_tables'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'llm_models',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('provider_name', sa.String(length=100), nullable=False),
        sa.Column('model_nickname', sa.String(length=100), nullable=True),
        sa.Column('cost_per_million_input_tokens', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('cost_per_million_output_tokens', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('is_available', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name', 'provider_name', name='uix_model_provider')
    )
    op.create_index(op.f('ix_llm_models_id'), 'llm_models', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_llm_models_id'), table_name='llm_models')
    op.drop_table('llm_models') 