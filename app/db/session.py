from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

print("\n")

print("--------------------------------")
print("CONFIGURATION")
print("--------------------------------")

print("ENVIRONMENT =", settings.ENVIRONMENT)

if settings.ENVIRONMENT == "development":
    print("Using LOCAL DATABASE URL")
    db_url = settings.LOCAL_DATABASE_URL
else:
    print("Using PRODUCTION DATABASE URL")
    db_url = settings.DATABASE_URL

# Replace any escaped colons in the URL
if db_url:
    db_url = db_url.replace("\\x3a", ":")

print("DB_URL =", db_url)

print("\n")

# engine = create_engine(db_url, pool_pre_ping=True)
engine = create_async_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


# # Dependency to get DB session
# def get_db():
#     """
#     Dependency for database session.
    
#     Yields:
#         Session: Database session
#     """
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close() 

# Async version of get_db
async def get_db():
    async with AsyncSession(engine) as session:
        yield session

