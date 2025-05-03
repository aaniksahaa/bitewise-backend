import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.models.base import Base


@pytest.fixture(scope="session")
def test_db_url():
    """Get the test database URL."""
    return "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create a SQLAlchemy engine for tests."""
    engine = create_engine(
        test_db_url, 
        # For SQLite: connect_args={"check_same_thread": False}
    )
    yield engine
    # Cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables for testing."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine, tables):
    """Create a SQLAlchemy session for tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    # Rollback the transaction and close the connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Create a FastAPI test client."""
    def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    # Clear dependency overrides
    app.dependency_overrides = {} 