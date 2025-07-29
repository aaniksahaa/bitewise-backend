"""
Async test configuration and fixtures for pytest.

This module provides async test fixtures and utilities for testing
async database operations and services.
"""

import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text, event
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.async_session import get_async_db
from app.db.base_class import Base
from app.core.config import settings
from tests.utils_jwt import generate_test_jwt


@pytest.fixture(scope="session")
def async_test_db_url() -> str:
    """Get the async test database URL."""
    # Use SQLite for tests with async support
    return "sqlite+aiosqlite:///./test_async.db"


@pytest.fixture(scope="session")
def async_engine(async_test_db_url):
    """Create an async SQLAlchemy engine for tests."""
    engine = create_async_engine(
        async_test_db_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    yield engine
    # Cleanup
    engine.sync_engine.dispose()
    if os.path.exists("./test_async.db"):
        os.remove("./test_async.db")


@pytest_asyncio.fixture(scope="session")
async def async_tables(async_engine):
    """Create database tables for async tests."""
    # Import all models to ensure they're registered
    from app.models.user import User
    from app.models.user_profile import UserProfile
    from app.models.conversation import Conversation
    from app.models.message import Message
    from app.models.llm_model import LLMModel
    from app.models.dish import Dish
    from app.models.ingredient import Ingredient
    from app.models.dish_ingredient import DishIngredient
    from app.models.intake import Intake
    from app.models.post import Post
    from app.models.comment import Comment
    from app.models.fitness_plan import FitnessPlan
    from app.models.health_history import HealthHistory
    from app.models.menu import Menu
    from app.models.auth import RefreshToken, OTPCode
    
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_db_session(async_engine, async_tables) -> AsyncGenerator[AsyncSession, None]:
    """Create an async SQLAlchemy session for tests."""
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        # Start a transaction
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # Rollback the transaction to clean up
            await transaction.rollback()
            await session.close()


@pytest_asyncio.fixture
async def async_client(async_db_session):
    """Create a FastAPI test client with async database session override."""
    from httpx import AsyncClient
    
    async def override_get_async_db():
        yield async_db_session
        
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clear dependency overrides
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def async_test_user(async_db_session: AsyncSession):
    """Create a test user for async tests."""
    from app.models.user import User
    
    test_user = User(
        email="testuser@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
        is_verified=True
    )
    
    async_db_session.add(test_user)
    await async_db_session.commit()
    await async_db_session.refresh(test_user)
    
    return test_user


@pytest_asyncio.fixture
async def async_auth_header(async_test_user):
    """Return an Authorization header with a valid JWT for the async test user."""
    token = generate_test_jwt(
        user_id=async_test_user.id, 
        email=async_test_user.email
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def async_test_llm_model(async_db_session: AsyncSession):
    """Create a test LLM model for async tests."""
    from app.models.llm_model import LLMModel
    
    llm_model = LLMModel(
        model_name="gpt-4",
        provider_name="openai",
        model_nickname="GPT-4",
        cost_per_million_input_tokens=30.0,
        cost_per_million_output_tokens=60.0,
        is_available=True
    )
    
    async_db_session.add(llm_model)
    await async_db_session.commit()
    await async_db_session.refresh(llm_model)
    
    return llm_model


@pytest_asyncio.fixture
async def async_test_conversation(async_db_session: AsyncSession, async_test_user):
    """Create a test conversation for async tests."""
    from app.models.conversation import Conversation
    
    conversation = Conversation(
        user_id=async_test_user.id,
        title="Test Conversation",
        status="active"
    )
    
    async_db_session.add(conversation)
    await async_db_session.commit()
    await async_db_session.refresh(conversation)
    
    return conversation


@pytest_asyncio.fixture
async def async_test_dish(async_db_session: AsyncSession):
    """Create a test dish for async tests."""
    from app.models.dish import Dish
    
    dish = Dish(
        name="Test Dish",
        description="A test dish for async testing",
        cuisine_type="test",
        calories_per_serving=250,
        protein_per_serving=15.0,
        carbs_per_serving=30.0,
        fat_per_serving=8.0,
        fiber_per_serving=5.0,
        sugar_per_serving=10.0,
        sodium_per_serving=500.0
    )
    
    async_db_session.add(dish)
    await async_db_session.commit()
    await async_db_session.refresh(dish)
    
    return dish


@pytest_asyncio.fixture
async def async_test_intake(async_db_session: AsyncSession, async_test_user, async_test_dish):
    """Create a test intake for async tests."""
    from app.models.intake import Intake
    from datetime import datetime
    
    intake = Intake(
        user_id=async_test_user.id,
        dish_id=async_test_dish.id,
        quantity=1.0,
        meal_type="lunch",
        consumed_at=datetime.utcnow()
    )
    
    async_db_session.add(intake)
    await async_db_session.commit()
    await async_db_session.refresh(intake)
    
    return intake


class AsyncTestDataSeeder:
    """Utility class for seeding test data in async tests."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_test_users(self, count: int = 3):
        """Create multiple test users."""
        from app.models.user import User
        
        users = []
        for i in range(count):
            user = User(
                email=f"testuser{i}@example.com",
                username=f"testuser{i}",
                full_name=f"Test User {i}",
                hashed_password="$2b$12$test_hashed_password",
                is_active=True,
                is_verified=True
            )
            self.session.add(user)
            users.append(user)
        
        await self.session.commit()
        
        # Refresh all users
        for user in users:
            await self.session.refresh(user)
        
        return users
    
    async def create_test_dishes(self, count: int = 5):
        """Create multiple test dishes."""
        from app.models.dish import Dish
        
        dishes = []
        cuisines = ["italian", "chinese", "mexican", "indian", "american"]
        
        for i in range(count):
            dish = Dish(
                name=f"Test Dish {i}",
                description=f"A test dish {i} for async testing",
                cuisine_type=cuisines[i % len(cuisines)],
                calories_per_serving=200 + (i * 50),
                protein_per_serving=10.0 + (i * 2),
                carbs_per_serving=25.0 + (i * 5),
                fat_per_serving=5.0 + (i * 2),
                fiber_per_serving=3.0 + i,
                sugar_per_serving=8.0 + i,
                sodium_per_serving=400.0 + (i * 100)
            )
            self.session.add(dish)
            dishes.append(dish)
        
        await self.session.commit()
        
        # Refresh all dishes
        for dish in dishes:
            await self.session.refresh(dish)
        
        return dishes
    
    async def create_test_intakes(self, user, dishes, count: int = 10):
        """Create multiple test intakes for a user."""
        from app.models.intake import Intake
        from datetime import datetime, timedelta
        import random
        
        intakes = []
        meal_types = ["breakfast", "lunch", "dinner", "snack"]
        
        for i in range(count):
            intake = Intake(
                user_id=user.id,
                dish_id=random.choice(dishes).id,
                quantity=round(random.uniform(0.5, 2.0), 1),
                meal_type=random.choice(meal_types),
                consumed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
            self.session.add(intake)
            intakes.append(intake)
        
        await self.session.commit()
        
        # Refresh all intakes
        for intake in intakes:
            await self.session.refresh(intake)
        
        return intakes
    
    async def create_test_conversations_and_messages(self, user, llm_model, count: int = 3):
        """Create test conversations with messages."""
        from app.models.conversation import Conversation
        from app.models.message import Message
        
        conversations = []
        
        for i in range(count):
            conversation = Conversation(
                user_id=user.id,
                title=f"Test Conversation {i}",
                status="active"
            )
            self.session.add(conversation)
            conversations.append(conversation)
        
        await self.session.commit()
        
        # Refresh conversations
        for conversation in conversations:
            await self.session.refresh(conversation)
        
        # Create messages for each conversation
        all_messages = []
        for conversation in conversations:
            # User message
            user_message = Message(
                conversation_id=conversation.id,
                user_id=user.id,
                content=f"Hello, this is a test message for conversation {conversation.id}",
                is_user_message=True,
                message_type="text",
                status="sent"
            )
            self.session.add(user_message)
            all_messages.append(user_message)
            
            # Assistant message
            assistant_message = Message(
                conversation_id=conversation.id,
                user_id=user.id,
                content=f"Hello! This is a test response for conversation {conversation.id}",
                is_user_message=False,
                llm_model_id=llm_model.id,
                message_type="text",
                status="sent",
                input_tokens=20,
                output_tokens=25
            )
            self.session.add(assistant_message)
            all_messages.append(assistant_message)
        
        await self.session.commit()
        
        # Refresh all messages
        for message in all_messages:
            await self.session.refresh(message)
        
        return conversations, all_messages


@pytest_asyncio.fixture
async def async_test_seeder(async_db_session: AsyncSession):
    """Provide an async test data seeder."""
    return AsyncTestDataSeeder(async_db_session)


# Utility functions for async testing
async def cleanup_test_data(session: AsyncSession, model_class, **filters):
    """Clean up test data for a specific model."""
    from sqlalchemy import select, delete
    
    if filters:
        stmt = delete(model_class).where(
            *[getattr(model_class, key) == value for key, value in filters.items()]
        )
    else:
        stmt = delete(model_class)
    
    await session.execute(stmt)
    await session.commit()


async def count_records(session: AsyncSession, model_class, **filters):
    """Count records in a table with optional filters."""
    from sqlalchemy import select, func
    
    if filters:
        stmt = select(func.count()).select_from(model_class).where(
            *[getattr(model_class, key) == value for key, value in filters.items()]
        )
    else:
        stmt = select(func.count()).select_from(model_class)
    
    result = await session.execute(stmt)
    return result.scalar()


# Async test decorators and utilities
def async_test_with_rollback(func):
    """Decorator to ensure test database operations are rolled back."""
    async def wrapper(*args, **kwargs):
        # This decorator can be used to add additional rollback logic if needed
        return await func(*args, **kwargs)
    return wrapper


class AsyncTestCase:
    """Base class for async test cases with common utilities."""
    
    @staticmethod
    async def assert_record_exists(session: AsyncSession, model_class, **filters):
        """Assert that a record exists in the database."""
        from sqlalchemy import select
        
        stmt = select(model_class).where(
            *[getattr(model_class, key) == value for key, value in filters.items()]
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        assert record is not None, f"Record not found in {model_class.__name__} with filters {filters}"
        return record
    
    @staticmethod
    async def assert_record_count(session: AsyncSession, model_class, expected_count: int, **filters):
        """Assert the number of records in a table."""
        actual_count = await count_records(session, model_class, **filters)
        assert actual_count == expected_count, f"Expected {expected_count} records, found {actual_count}"
    
    @staticmethod
    async def create_and_commit(session: AsyncSession, model_instance):
        """Create a model instance and commit it to the database."""
        session.add(model_instance)
        await session.commit()
        await session.refresh(model_instance)
        return model_instance