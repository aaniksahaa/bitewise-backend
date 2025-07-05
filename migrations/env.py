import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

# Add the app directory to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the SQLAlchemy models
from app.core.config import settings
from app.db.base_class import Base
import app.models  # noqa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    if settings.ENVIRONMENT == "development":
        return settings.LOCAL_DATABASE_URL
    return settings.DATABASE_URL

def create_version_table_if_needed(connection):
    """Create custom alembic_version table with longer character limit if it doesn't exist, 
    or modify it if it exists with wrong column size"""
    # Check if table exists
    inspector = connection.dialect.get_table_names(connection)
    if 'alembic_version' not in inspector:
        # Create the table with longer version_num column
        connection.execute(text("""
            CREATE TABLE alembic_version (
                version_num VARCHAR(100) NOT NULL PRIMARY KEY
            )
        """))
    else:
        # Check if column size is correct
        result = connection.execute(text("""
            SELECT character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'alembic_version' 
            AND column_name = 'version_num'
        """))
        current_length = result.fetchone()
        if current_length and current_length[0] < 100:
            # Alter the column to have longer length
            connection.execute(text("""
                ALTER TABLE alembic_version 
                ALTER COLUMN version_num TYPE VARCHAR(100)
            """))
            connection.commit()

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Create custom version table if needed
        create_version_table_if_needed(connection)
        
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 