"""
Async test utilities and helper functions.

This module provides utility functions and classes for async testing,
including database operations, API testing, and common test patterns.
"""

import asyncio
from typing import Dict, Any, List, Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import DeclarativeBase
from httpx import AsyncClient
import pytest

T = TypeVar('T', bound=DeclarativeBase)


class AsyncDatabaseTestUtils:
    """Utility class for async database testing operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_record(self, model_class: Type[T], **kwargs) -> T:
        """Create a record in the database and return it."""
        record = model_class(**kwargs)
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
    
    async def get_record(self, model_class: Type[T], record_id: int) -> Optional[T]:
        """Get a record by ID."""
        return await self.session.get(model_class, record_id)
    
    async def get_record_by_field(self, model_class: Type[T], field_name: str, value: Any) -> Optional[T]:
        """Get a record by a specific field value."""
        stmt = select(model_class).where(getattr(model_class, field_name) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def count_records(self, model_class: Type[T], **filters) -> int:
        """Count records in a table with optional filters."""
        if filters:
            stmt = select(func.count()).select_from(model_class).where(
                *[getattr(model_class, key) == value for key, value in filters.items()]
            )
        else:
            stmt = select(func.count()).select_from(model_class)
        
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def delete_records(self, model_class: Type[T], **filters):
        """Delete records from a table with optional filters."""
        if filters:
            stmt = delete(model_class).where(
                *[getattr(model_class, key) == value for key, value in filters.items()]
            )
        else:
            stmt = delete(model_class)
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def assert_record_exists(self, model_class: Type[T], **filters) -> T:
        """Assert that a record exists and return it."""
        stmt = select(model_class).where(
            *[getattr(model_class, key) == value for key, value in filters.items()]
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        assert record is not None, f"Record not found in {model_class.__name__} with filters {filters}"
        return record
    
    async def assert_record_count(self, model_class: Type[T], expected_count: int, **filters):
        """Assert the number of records in a table."""
        actual_count = await self.count_records(model_class, **filters)
        assert actual_count == expected_count, f"Expected {expected_count} records, found {actual_count}"
    
    async def assert_record_not_exists(self, model_class: Type[T], **filters):
        """Assert that a record does not exist."""
        stmt = select(model_class).where(
            *[getattr(model_class, key) == value for key, value in filters.items()]
        )
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        assert record is None, f"Record unexpectedly found in {model_class.__name__} with filters {filters}"


class AsyncAPITestUtils:
    """Utility class for async API testing."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
    
    async def post_json(self, url: str, data: Dict[Any, Any], headers: Optional[Dict[str, str]] = None):
        """Make a POST request with JSON data."""
        return await self.client.post(url, json=data, headers=headers or {})
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None):
        """Make a GET request."""
        return await self.client.get(url, params=params or {}, headers=headers or {})
    
    async def put_json(self, url: str, data: Dict[Any, Any], headers: Optional[Dict[str, str]] = None):
        """Make a PUT request with JSON data."""
        return await self.client.put(url, json=data, headers=headers or {})
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None):
        """Make a DELETE request."""
        return await self.client.delete(url, headers=headers or {})
    
    async def assert_status_code(self, response, expected_status: int):
        """Assert response status code."""
        assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
    
    async def assert_json_response(self, response, expected_keys: List[str]):
        """Assert that response is JSON and contains expected keys."""
        assert response.headers.get("content-type", "").startswith("application/json")
        json_data = response.json()
        for key in expected_keys:
            assert key in json_data, f"Expected key '{key}' not found in response: {json_data}"
        return json_data
    
    async def assert_error_response(self, response, expected_status: int, expected_detail: Optional[str] = None):
        """Assert error response format."""
        await self.assert_status_code(response, expected_status)
        json_data = await self.assert_json_response(response, ["detail"])
        if expected_detail:
            assert expected_detail in json_data["detail"], f"Expected detail '{expected_detail}' not found in '{json_data['detail']}'"
        return json_data


class AsyncTestDataFactory:
    """Factory class for creating test data."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.db_utils = AsyncDatabaseTestUtils(session)
    
    async def create_user(self, **overrides) -> 'User':
        """Create a test user with default values."""
        from app.models.user import User
        
        defaults = {
            "email": "testuser@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": "$2b$12$test_hashed_password",
            "is_active": True,
            "is_verified": True
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(User, **defaults)
    
    async def create_user_profile(self, user_id: int, **overrides) -> 'UserProfile':
        """Create a test user profile."""
        from app.models.user_profile import UserProfile
        
        defaults = {
            "user_id": user_id,
            "age": 25,
            "gender": "other",
            "height": 170.0,
            "weight": 70.0,
            "activity_level": "moderate",
            "dietary_preferences": ["vegetarian"],
            "health_goals": ["weight_loss"],
            "allergies": []
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(UserProfile, **defaults)
    
    async def create_dish(self, **overrides) -> 'Dish':
        """Create a test dish."""
        from app.models.dish import Dish
        
        defaults = {
            "name": "Test Dish",
            "description": "A test dish",
            "cuisine_type": "test",
            "calories_per_serving": 250,
            "protein_per_serving": 15.0,
            "carbs_per_serving": 30.0,
            "fat_per_serving": 8.0,
            "fiber_per_serving": 5.0,
            "sugar_per_serving": 10.0,
            "sodium_per_serving": 500.0
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(Dish, **defaults)
    
    async def create_intake(self, user_id: int, dish_id: int, **overrides) -> 'Intake':
        """Create a test intake."""
        from app.models.intake import Intake
        from datetime import datetime
        
        defaults = {
            "user_id": user_id,
            "dish_id": dish_id,
            "quantity": 1.0,
            "meal_type": "lunch",
            "consumed_at": datetime.utcnow()
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(Intake, **defaults)
    
    async def create_conversation(self, user_id: int, **overrides) -> 'Conversation':
        """Create a test conversation."""
        from app.models.conversation import Conversation
        
        defaults = {
            "user_id": user_id,
            "title": "Test Conversation",
            "status": "active"
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(Conversation, **defaults)
    
    async def create_message(self, conversation_id: int, user_id: int, **overrides) -> 'Message':
        """Create a test message."""
        from app.models.message import Message
        
        defaults = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "content": "Test message",
            "is_user_message": True,
            "message_type": "text",
            "status": "sent"
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(Message, **defaults)
    
    async def create_llm_model(self, **overrides) -> 'LLMModel':
        """Create a test LLM model."""
        from app.models.llm_model import LLMModel
        
        defaults = {
            "model_name": "gpt-4",
            "provider_name": "openai",
            "model_nickname": "GPT-4",
            "cost_per_million_input_tokens": 30.0,
            "cost_per_million_output_tokens": 60.0,
            "is_available": True
        }
        defaults.update(overrides)
        
        return await self.db_utils.create_record(LLMModel, **defaults)


class AsyncTestScenarios:
    """Common test scenarios for async testing."""
    
    def __init__(self, session: AsyncSession, client: AsyncClient):
        self.session = session
        self.client = client
        self.db_utils = AsyncDatabaseTestUtils(session)
        self.api_utils = AsyncAPITestUtils(client)
        self.factory = AsyncTestDataFactory(session)
    
    async def setup_user_with_profile(self, email: str = "test@example.com") -> tuple:
        """Set up a user with profile for testing."""
        user = await self.factory.create_user(email=email, username=email.split('@')[0])
        profile = await self.factory.create_user_profile(user.id)
        return user, profile
    
    async def setup_user_with_intakes(self, intake_count: int = 5) -> tuple:
        """Set up a user with dishes and intakes for testing."""
        user = await self.factory.create_user()
        dishes = []
        intakes = []
        
        for i in range(intake_count):
            dish = await self.factory.create_dish(name=f"Test Dish {i}")
            dishes.append(dish)
            
            intake = await self.factory.create_intake(user.id, dish.id)
            intakes.append(intake)
        
        return user, dishes, intakes
    
    async def setup_conversation_with_messages(self, message_count: int = 3) -> tuple:
        """Set up a conversation with messages for testing."""
        user = await self.factory.create_user()
        llm_model = await self.factory.create_llm_model()
        conversation = await self.factory.create_conversation(user.id)
        
        messages = []
        for i in range(message_count):
            # User message
            user_message = await self.factory.create_message(
                conversation.id, 
                user.id, 
                content=f"User message {i}",
                is_user_message=True
            )
            messages.append(user_message)
            
            # Assistant message
            assistant_message = await self.factory.create_message(
                conversation.id, 
                user.id, 
                content=f"Assistant response {i}",
                is_user_message=False,
                llm_model_id=llm_model.id
            )
            messages.append(assistant_message)
        
        return user, conversation, messages, llm_model
    
    async def test_crud_operations(self, model_class: Type[T], create_data: Dict[str, Any], update_data: Dict[str, Any]):
        """Test basic CRUD operations for a model."""
        # Create
        record = await self.db_utils.create_record(model_class, **create_data)
        assert record.id is not None
        
        # Read
        retrieved_record = await self.db_utils.get_record(model_class, record.id)
        assert retrieved_record is not None
        assert retrieved_record.id == record.id
        
        # Update
        for key, value in update_data.items():
            setattr(retrieved_record, key, value)
        await self.session.commit()
        await self.session.refresh(retrieved_record)
        
        for key, value in update_data.items():
            assert getattr(retrieved_record, key) == value
        
        # Delete
        await self.session.delete(retrieved_record)
        await self.session.commit()
        
        deleted_record = await self.db_utils.get_record(model_class, record.id)
        assert deleted_record is None
        
        return record


# Async test decorators
def async_test_timeout(seconds: int = 30):
    """Decorator to add timeout to async tests."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
        return wrapper
    return decorator


def async_test_retry(max_retries: int = 3, delay: float = 0.1):
    """Decorator to retry async tests on failure."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                    continue
            raise last_exception
        return wrapper
    return decorator


# Performance testing utilities
class AsyncPerformanceTestUtils:
    """Utilities for performance testing of async operations."""
    
    @staticmethod
    async def measure_async_operation(operation, *args, **kwargs):
        """Measure the execution time of an async operation."""
        import time
        start_time = time.time()
        result = await operation(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    async def run_concurrent_operations(operation, operation_args_list: List[tuple], max_concurrent: int = 10):
        """Run multiple async operations concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def run_with_semaphore(args):
            async with semaphore:
                return await operation(*args)
        
        tasks = [run_with_semaphore(args) for args in operation_args_list]
        return await asyncio.gather(*tasks)
    
    @staticmethod
    async def benchmark_database_operations(session: AsyncSession, model_class: Type[T], operation_count: int = 100):
        """Benchmark database operations for a model."""
        db_utils = AsyncDatabaseTestUtils(session)
        
        # Benchmark create operations
        create_start = asyncio.get_event_loop().time()
        created_records = []
        for i in range(operation_count):
            record = await db_utils.create_record(model_class, name=f"Benchmark Record {i}")
            created_records.append(record)
        create_time = asyncio.get_event_loop().time() - create_start
        
        # Benchmark read operations
        read_start = asyncio.get_event_loop().time()
        for record in created_records:
            await db_utils.get_record(model_class, record.id)
        read_time = asyncio.get_event_loop().time() - read_start
        
        # Benchmark delete operations
        delete_start = asyncio.get_event_loop().time()
        for record in created_records:
            await session.delete(record)
        await session.commit()
        delete_time = asyncio.get_event_loop().time() - delete_start
        
        return {
            "create_time": create_time,
            "read_time": read_time,
            "delete_time": delete_time,
            "operations_count": operation_count,
            "avg_create_time": create_time / operation_count,
            "avg_read_time": read_time / operation_count,
            "avg_delete_time": delete_time / operation_count
        }


# Mock utilities for async testing
class AsyncMockUtils:
    """Utilities for mocking in async tests."""
    
    @staticmethod
    def create_async_mock(return_value=None, side_effect=None):
        """Create an async mock function."""
        async def async_mock(*args, **kwargs):
            if side_effect:
                if callable(side_effect):
                    return await side_effect(*args, **kwargs) if asyncio.iscoroutinefunction(side_effect) else side_effect(*args, **kwargs)
                else:
                    raise side_effect
            return return_value
        return async_mock
    
    @staticmethod
    def patch_async_method(obj, method_name: str, return_value=None, side_effect=None):
        """Patch an async method on an object."""
        original_method = getattr(obj, method_name)
        mock_method = AsyncMockUtils.create_async_mock(return_value, side_effect)
        setattr(obj, method_name, mock_method)
        return original_method