"""Create health_history table and trigger for tracking height/weight changes.

Revision ID: create_health_history_trigger
Revises: e3c7d017dda1
Create Date: 2024-03-19 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "create_health_history_trigger"
down_revision = "e3c7d017dda1"
branch_labels = None
depends_on = None


def upgrade():
    # Create health_history table
    op.create_table(
        "health_history",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("height_cm", sa.DECIMAL(6, 2), nullable=True),
        sa.Column("weight_kg", sa.DECIMAL(6, 2), nullable=True),
        sa.Column(
            "change_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.user_id"],
            ondelete="CASCADE",
            name="fk_user_profile",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create trigger function
    op.execute(
        """
    CREATE OR REPLACE FUNCTION log_profile_health_changes()
    RETURNS TRIGGER AS $$
    BEGIN
        IF OLD.height_cm IS DISTINCT FROM NEW.height_cm OR OLD.weight_kg IS DISTINCT FROM NEW.weight_kg THEN
            INSERT INTO health_history (user_id, height_cm, weight_kg, change_timestamp)
            VALUES (OLD.user_id, OLD.height_cm, OLD.weight_kg, CURRENT_TIMESTAMP);
        END IF;
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """
    )

    # Create trigger
    op.execute(
        """
    CREATE TRIGGER profile_health_update_trigger
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION log_profile_health_changes();
    """
    )


def downgrade():
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS profile_health_update_trigger ON user_profiles;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS log_profile_health_changes();")

    # Drop health_history table
    op.drop_table("health_history")
