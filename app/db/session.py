"""
Legacy synchronous database session module.

This module is maintained for backward compatibility with existing code
that hasn't been migrated to async yet. It redirects to the async session
module and provides compatibility functions.

DEPRECATED: Use async_session.py instead for all new code.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.db.async_session import get_async_db_manager_sync

logger = logging.getLogger(__name__)

# Issue a deprecation warning
logger.warning(
    "DEPRECATED: Using synchronous database session. "
    "Please migrate to async_session.py for better performance."
)

# Create synchronous engine from the async URL
# This is only for compatibility with existing code
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create synchronous session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    DEPRECATED: Get a synchronous database session.
    
    This function is maintained for backward compatibility.
    New code should use get_async_db from async_session.py instead.
    
    Yields:
        Session: Synchronous database session
    """
    logger.warning(
        "DEPRECATED: Using synchronous get_db(). "
        "Please migrate to get_async_db() for better performance."
    )
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()