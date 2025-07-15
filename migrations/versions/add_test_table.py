"""Create authentication tables

Revision ID: add_test_table

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_test_table'
down_revision = 'add_last_login_at_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    
    
def downgrade() -> None:
    op.drop_table('tests')