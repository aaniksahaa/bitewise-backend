from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

if settings.ENVIRONMENT == "development":
    db_url = settings.LOCAL_DATABASE_URL
else:
    db_url = settings.DATABASE_URL

# Replace any escaped colons in the URL
if db_url:
    db_url = db_url.replace("\\x3a", ":")

print(db_url)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get DB session
def get_db():
    """
    Dependency for database session.
    
    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 