import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base_class import Base
from tests.utils_jwt import generate_test_jwt

@pytest.fixture(scope="session")
def test_db_url():
    """Get the test database URL."""
    return "sqlite:///./test.db"

@pytest.fixture(scope="session")
def engine(test_db_url):
    """Create a SQLAlchemy engine for tests."""
    engine = create_engine(
        test_db_url, 
        connect_args={"check_same_thread": False}
    )
    yield engine
    # Cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture(scope="session")
def tables(engine):
    """Create only the necessary database tables for testing."""
    # Import only the models we need for chat tests
    from app.models.user import User
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.llm_model import LLMModel
    
    # Create only the tables we need, with explicit SQL for SQLite compatibility
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Create users table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR UNIQUE NOT NULL,
                username VARCHAR UNIQUE NOT NULL,
                full_name VARCHAR,
                hashed_password VARCHAR,
                is_active BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                is_superuser BOOLEAN DEFAULT 0,
                oauth_provider VARCHAR,
                oauth_id VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login_at DATETIME
            )
        """))
        
        # Create conversations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title VARCHAR(255),
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                CHECK (status IN ('active', 'archived', 'deleted'))
            )
        """))
        
        # Create messages table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_user_message BOOLEAN NOT NULL,
                llm_model_id INTEGER,
                input_tokens INTEGER,
                output_tokens INTEGER,
                parent_message_id INTEGER,
                message_type VARCHAR(50) NOT NULL DEFAULT 'text',
                attachments TEXT,
                reactions TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'sent',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (llm_model_id) REFERENCES llm_models (id) ON DELETE SET NULL,
                FOREIGN KEY (parent_message_id) REFERENCES messages (id) ON DELETE SET NULL,
                CHECK (message_type IN ('text', 'image', 'file', 'system')),
                CHECK (status IN ('sent', 'delivered', 'read', 'edited', 'deleted'))
            )
        """))
        
        # Create llm_models table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS llm_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name VARCHAR(100) NOT NULL,
                provider_name VARCHAR(100) NOT NULL,
                model_nickname VARCHAR(100),
                cost_per_million_input_tokens DECIMAL(10, 4) NOT NULL,
                cost_per_million_output_tokens DECIMAL(10, 4) NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (model_name, provider_name)
            )
        """))
        
        conn.commit()
    
    yield
    
    # Clean up
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS messages"))
        conn.execute(text("DROP TABLE IF EXISTS conversations"))
        conn.execute(text("DROP TABLE IF EXISTS llm_models"))
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.commit()

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

@pytest.fixture
def auth_header(db_session):
    """Return an Authorization header with a valid JWT for the test user."""
    from app.models.user import User
    
    # Create a test user in the database (don't specify ID, let it auto-increment)
    test_user = User(
        email="testuser@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        is_verified=True
    )
    db_session.add(test_user)
    db_session.commit()
    
    # Generate JWT token for the test user
    token = generate_test_jwt(user_id=test_user.id, email="testuser@example.com")
    return {"Authorization": f"Bearer {token}"}
