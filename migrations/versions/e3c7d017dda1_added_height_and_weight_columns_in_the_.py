"""Added height and weight columns in the user_profiles table and made gender and date_of_birth fields required.

Revision ID: e3c7d017dda1
Revises: 78ef8b3b864f
Create Date: 2025-05-27 14:26:41.225377

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e3c7d017dda1'
down_revision = '78ef8b3b864f'
branch_labels = None
depends_on = None


def upgrade():
    # Add height_cm and weight_kg columns
    op.add_column('user_profiles', sa.Column('height_cm', sa.DECIMAL(6, 2), nullable=False))
    op.add_column('user_profiles', sa.Column('weight_kg', sa.DECIMAL(6, 2), nullable=False))
    
    # Make gender and date_of_birth required
    op.alter_column('user_profiles', 'gender',
                    existing_type=postgresql.ENUM('male', 'female', 'other', name='gender_type'),
                    nullable=False)
    op.alter_column('user_profiles', 'date_of_birth',
                    existing_type=sa.DATE(),
                    nullable=False)


def downgrade():
    # Make gender and date_of_birth optional again
    op.alter_column('user_profiles', 'gender',
                    existing_type=postgresql.ENUM('male', 'female', 'other', name='gender_type'),
                    nullable=True)
    op.alter_column('user_profiles', 'date_of_birth',
                    existing_type=sa.DATE(),
                    nullable=True)
    
    # Remove height_cm and weight_kg columns
    op.drop_column('user_profiles', 'weight_kg')
    op.drop_column('user_profiles', 'height_cm') 