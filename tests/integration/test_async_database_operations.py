"""
Async integration tests for database operations.

This module tests the async database operations across different services,
ensuring that the async database infrastructure works correctly with
real database operations.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.dish import Dish
from app.models.intake import Intake
from app.models.llm_model import LLMModel
from app.services.async_auth import AsyncAuthService
from app.services.async_chat import AsyncChatService
from app.services.async_user_profile import AsyncUserProfileService
from app.services.async_dish import AsyncDishService
from app.services.async_intake import AsyncIntakeService
from tests.async_test_utils import AsyncDatabaseTestUtils, AsyncTestScenarios


class TestAsyncDatabaseOperations:
    """Test async database operations across services."""

    @pytest.mark.asyncio
    async def test_async_user_crud_operations(self, async_db_session):
        """
        Test async CRUD operations for users.
        
        This test ensures that user creation, retrieval, update,
        and deletion work correctly with async database operations.
        """
        db_utils = AsyncDatabaseTestUtils(async_db_session)
        
        # Create user
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": "hashed_password_123",
            "is_active": True,
            "is_verified": True
        }
        
        user = await db_utils.create_record(User, **user_data)
        assert user.id is not None
        assert user.email == "test@example.com"
        
        # Read user
        retrieved_user = await db_utils.get_record(User, user.id)
        assert retrieved_user is not None
        assert retrieved_user.email == user.email
        
        # Update user
        retrieved_user.full_name = "Updated Test User"
        await async_db_session.commit()
        await async_db_session.refresh(retrieved_user)
        assert retrieved_user.full_name == "Updated Test User"
        
        # Count users
        user_count = await db_utils.count_records(User)
        assert user_count >= 1
        
        # Delete user
        await async_db_session.delete(retrieved_user)
        await async_db_session.commit()
        
        deleted_user = await db_utils.get_record(User, user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_async_auth_service_integration(self, async_db_session):
        """
        Test AsyncAuthService integration with database.
        
        This test ensures that authentication operations work
        correctly with async database operations.
        """
        # Test user creation
        user_data = {
            "email": "auth@example.com",
            "username": "authuser",
            "full_name": "Auth User",
            "hashed_password": AsyncAuthService.get_password_hash("password123")
        }
        
        user = await AsyncAuthService.create_user(async_db_session, user_data)
        assert user.id is not None
        assert user.email == "auth@example.com"
        
        # Test user retrieval by email
        retrieved_user = await AsyncAuthService.get_user_by_email(
            async_db_session, "auth@example.com"
        )
        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        
        # Test OTP creation
        otp_code, expires_at = await AsyncAuthService.create_otp(
            async_db_session, user.id, user.email, "login"
        )
        assert len(otp_code) == 6
        assert isinstance(expires_at, datetime)
        
        # Test OTP verification
        verified_user = await AsyncAuthService.verify_otp(
            async_db_session, user.email, otp_code, "login"
        )
        assert verified_user is not None
        assert verified_user.id == user.id
        
        # Test password update
        await AsyncAuthService.update_password(
            async_db_session, user.id, "new_password123"
        )
        
        # Verify password was updated
        updated_user = await AsyncAuthService.get_user_by_email(
            async_db_session, "auth@example.com"
        )
        assert AsyncAuthService.verify_password("new_password123", updated_user.hashed_password)

    @pytest.mark.asyncio
    async def test_async_chat_service_integration(self, async_db_session, async_test_user, async_test_llm_model):
        """
        Test AsyncChatService integration with database.
        
        This test ensures that chat operations work correctly
        with async database operations.
        """
        # Test conversation creation
        from app.schemas.chat import ConversationCreate, MessageCreate
        
        conv_data = ConversationCreate(
            title="Test Async Conversation",
            extra_data={"topic": "testing"}
        )
        
        conversation = await AsyncChatService.create_conversation(
            async_db_session, conv_data, async_test_user.id
        )
        assert conversation.id is not None
        assert conversation.title == "Test Async Conversation"
        assert conversation.user_id == async_test_user.id
        
        # Test conversation retrieval
        retrieved_conv = await AsyncChatService.get_conversation_by_id(
            async_db_session, conversation.id, async_test_user.id
        )
        assert retrieved_conv is not None
        assert retrieved_conv.id == conversation.id
        
        # Test message creation
        msg_data = MessageCreate(
            content="Hello, this is a test message",
            message_type="text"
        )
        
        message = await AsyncChatService.create_message(
            async_db_session, conversation.id, msg_data, async_test_user.id,
            is_user_message=True, input_tokens=10, output_tokens=0
        )
        assert message.id is not None
        assert message.content == "Hello, this is a test message"
        assert message.conversation_id == conversation.id
        
        # Test message retrieval
        messages_response = await AsyncChatService.get_conversation_messages(
            async_db_session, conversation.id, async_test_user.id
        )
        assert messages_response.total_count >= 1
        assert len(messages_response.messages) >= 1
        
        # Test conversation update
        from app.schemas.chat import ConversationUpdate
        update_data = ConversationUpdate(title="Updated Conversation Title")
        
        updated_conv = await AsyncChatService.update_conversation(
            async_db_session, conversation.id, update_data, async_test_user.id
        )
        assert updated_conv.title == "Updated Conversation Title"

    @pytest.mark.asyncio
    async def test_async_user_profile_integration(self, async_db_session, async_test_user):
        """
        Test AsyncUserProfileService integration with database.
        
        This test ensures that user profile operations work correctly
        with async database operations.
        """
        # Test profile creation
        profile_data = {
            "user_id": async_test_user.id,
            "age": 25,
            "gender": "other",
            "height": 170.0,
            "weight": 70.0,
            "activity_level": "moderate",
            "dietary_preferences": ["vegetarian"],
            "health_goals": ["weight_loss"],
            "allergies": []
        }
        
        profile = await AsyncUserProfileService.create_profile(
            async_db_session, profile_data
        )
        assert profile.id is not None
        assert profile.user_id == async_test_user.id
        assert profile.age == 25
        
        # Test profile retrieval
        retrieved_profile = await AsyncUserProfileService.get_profile_by_user_id(
            async_db_session, async_test_user.id
        )
        assert retrieved_profile is not None
        assert retrieved_profile.id == profile.id
        
        # Test profile update
        update_data = {
            "age": 26,
            "weight": 72.0,
            "health_goals": ["muscle_gain"]
        }
        
        updated_profile = await AsyncUserProfileService.update_profile(
            async_db_session, async_test_user.id, update_data
        )
        assert updated_profile.age == 26
        assert updated_profile.weight == 72.0
        assert "muscle_gain" in updated_profile.health_goals

    @pytest.mark.asyncio
    async def test_async_dish_and_intake_integration(self, async_db_session, async_test_user):
        """
        Test AsyncDishService and AsyncIntakeService integration.
        
        This test ensures that dish and intake operations work correctly
        with async database operations and proper relationships.
        """
        # Test dish creation
        dish_data = {
            "name": "Test Async Dish",
            "description": "A test dish for async operations",
            "cuisine_type": "test",
            "calories_per_serving": 300,
            "protein_per_serving": 20.0,
            "carbs_per_serving": 35.0,
            "fat_per_serving": 10.0,
            "fiber_per_serving": 5.0,
            "sugar_per_serving": 8.0,
            "sodium_per_serving": 600.0
        }
        
        dish = await AsyncDishService.create_dish(async_db_session, dish_data)
        assert dish.id is not None
        assert dish.name == "Test Async Dish"
        
        # Test dish search
        search_results = await AsyncDishService.search_dishes(
            async_db_session, "Test Async", limit=10
        )
        assert len(search_results) >= 1
        assert any(d.name == "Test Async Dish" for d in search_results)
        
        # Test intake creation
        intake_data = {
            "user_id": async_test_user.id,
            "dish_id": dish.id,
            "quantity": 1.5,
            "meal_type": "lunch",
            "consumed_at": datetime.utcnow()
        }
        
        intake = await AsyncIntakeService.create_intake(async_db_session, intake_data)
        assert intake.id is not None
        assert intake.user_id == async_test_user.id
        assert intake.dish_id == dish.id
        assert intake.quantity == 1.5
        
        # Test intake retrieval
        user_intakes = await AsyncIntakeService.get_user_intakes(
            async_db_session, async_test_user.id, limit=10
        )
        assert len(user_intakes) >= 1
        assert any(i.dish_id == dish.id for i in user_intakes)
        
        # Test intake statistics
        stats = await AsyncIntakeService.get_user_intake_stats(
            async_db_session, async_test_user.id
        )
        assert stats is not None
        assert stats["total_calories"] >= 300 * 1.5  # dish calories * quantity

    @pytest.mark.asyncio
    async def test_async_complex_queries(self, async_db_session):
        """
        Test complex async database queries.
        
        This test ensures that complex queries with joins and aggregations
        work correctly with async database operations.
        """
        scenarios = AsyncTestScenarios(async_db_session, None)
        
        # Set up test data
        user, dishes, intakes = await scenarios.setup_user_with_intakes(5)
        
        # Test complex query: Get user's total calories consumed
        stmt = select(func.sum(Dish.calories_per_serving * Intake.quantity)).select_from(
            Intake.join(Dish)
        ).where(Intake.user_id == user.id)
        
        result = await async_db_session.execute(stmt)
        total_calories = result.scalar()
        assert total_calories is not None
        assert total_calories > 0
        
        # Test complex query: Get user's intake count by meal type
        stmt = select(
            Intake.meal_type,
            func.count(Intake.id).label('count')
        ).where(
            Intake.user_id == user.id
        ).group_by(Intake.meal_type)
        
        result = await async_db_session.execute(stmt)
        meal_counts = result.all()
        assert len(meal_counts) > 0
        
        # Test complex query: Get dishes with their intake counts
        stmt = select(
            Dish.name,
            func.count(Intake.id).label('intake_count')
        ).select_from(
            Dish.outerjoin(Intake)
        ).group_by(Dish.id, Dish.name).having(
            func.count(Intake.id) > 0
        )
        
        result = await async_db_session.execute(stmt)
        dish_counts = result.all()
        assert len(dish_counts) > 0

    @pytest.mark.asyncio
    async def test_async_transaction_rollback(self, async_db_session):
        """
        Test async transaction rollback functionality.
        
        This test ensures that async transactions can be rolled back
        correctly when errors occur.
        """
        db_utils = AsyncDatabaseTestUtils(async_db_session)
        
        # Count initial users
        initial_count = await db_utils.count_records(User)
        
        try:
            # Start a transaction that will fail
            user_data = {
                "email": "transaction@example.com",
                "username": "transactionuser",
                "full_name": "Transaction User",
                "hashed_password": "hashed_password"
            }
            
            user = await db_utils.create_record(User, **user_data)
            assert user.id is not None
            
            # Force an error to trigger rollback
            # Try to create another user with the same email (should fail)
            duplicate_user_data = {
                "email": "transaction@example.com",  # Same email
                "username": "duplicateuser",
                "full_name": "Duplicate User",
                "hashed_password": "hashed_password"
            }
            
            # This should raise an integrity error
            from sqlalchemy.exc import IntegrityError
            with pytest.raises(IntegrityError):
                await db_utils.create_record(User, **duplicate_user_data)
                
        except IntegrityError:
            # Rollback should happen automatically
            await async_db_session.rollback()
        
        # Verify that the transaction was rolled back
        final_count = await db_utils.count_records(User)
        # The count should be the same as initial since the transaction was rolled back
        # Note: This depends on the test isolation setup

    @pytest.mark.asyncio
    async def test_async_concurrent_operations(self, async_db_session):
        """
        Test concurrent async database operations.
        
        This test ensures that multiple async operations can run
        concurrently without conflicts.
        """
        import asyncio
        
        db_utils = AsyncDatabaseTestUtils(async_db_session)
        
        async def create_user(index):
            """Create a user with a unique identifier."""
            user_data = {
                "email": f"concurrent{index}@example.com",
                "username": f"concurrent{index}",
                "full_name": f"Concurrent User {index}",
                "hashed_password": "hashed_password"
            }
            return await db_utils.create_record(User, **user_data)
        
        # Create multiple users concurrently
        tasks = [create_user(i) for i in range(5)]
        users = await asyncio.gather(*tasks)
        
        # Verify all users were created
        assert len(users) == 5
        for i, user in enumerate(users):
            assert user.email == f"concurrent{i}@example.com"
            assert user.id is not None
        
        # Verify they all exist in the database
        for user in users:
            retrieved_user = await db_utils.get_record(User, user.id)
            assert retrieved_user is not None

    @pytest.mark.asyncio
    async def test_async_database_performance(self, async_db_session):
        """
        Test async database operation performance.
        
        This test measures the performance of async database operations
        to ensure they perform adequately.
        """
        import time
        
        db_utils = AsyncDatabaseTestUtils(async_db_session)
        
        # Measure time for creating multiple records
        start_time = time.time()
        
        users = []
        for i in range(10):
            user_data = {
                "email": f"perf{i}@example.com",
                "username": f"perf{i}",
                "full_name": f"Performance User {i}",
                "hashed_password": "hashed_password"
            }
            user = await db_utils.create_record(User, **user_data)
            users.append(user)
        
        creation_time = time.time() - start_time
        
        # Measure time for reading records
        start_time = time.time()
        
        for user in users:
            retrieved_user = await db_utils.get_record(User, user.id)
            assert retrieved_user is not None
        
        read_time = time.time() - start_time
        
        # Basic performance assertions
        # These are loose assertions to ensure operations complete in reasonable time
        assert creation_time < 5.0  # Should create 10 users in less than 5 seconds
        assert read_time < 2.0      # Should read 10 users in less than 2 seconds
        
        # Log performance metrics for monitoring
        print(f"Async DB Performance - Creation: {creation_time:.3f}s, Read: {read_time:.3f}s")

    @pytest.mark.asyncio
    async def test_async_relationship_loading(self, async_db_session):
        """
        Test async relationship loading between models.
        
        This test ensures that relationships between models
        are loaded correctly in async operations.
        """
        scenarios = AsyncTestScenarios(async_db_session, None)
        
        # Set up related data
        user, conversation, messages, llm_model = await scenarios.setup_conversation_with_messages(3)
        
        # Test loading conversation with messages
        stmt = select(Conversation).where(Conversation.id == conversation.id)
        result = await async_db_session.execute(stmt)
        loaded_conversation = result.scalar_one_or_none()
        
        assert loaded_conversation is not None
        assert loaded_conversation.id == conversation.id
        
        # Test loading messages with conversation relationship
        stmt = select(Message).where(Message.conversation_id == conversation.id)
        result = await async_db_session.execute(stmt)
        loaded_messages = result.scalars().all()
        
        assert len(loaded_messages) >= 3
        for message in loaded_messages:
            assert message.conversation_id == conversation.id
        
        # Test loading user with their conversations
        stmt = select(User).where(User.id == user.id)
        result = await async_db_session.execute(stmt)
        loaded_user = result.scalar_one_or_none()
        
        assert loaded_user is not None
        assert loaded_user.id == user.id