"""
Example usage of async base service classes and error handling utilities.

This demonstrates how to create async services using the new base classes
and how to use the error handling and retry utilities.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.base import AsyncBaseService, AsyncQueryUtils, with_transaction
from app.services.async_error_handler import (
    handle_async_db_errors, 
    retry_async_db_operation,
    async_transaction_rollback
)
from app.models.user import User
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class AsyncUserService(AsyncBaseService[User, UserProfileCreate, UserProfileUpdate]):
    """
    Example async user service extending the base service.
    
    Demonstrates how to create domain-specific services using the async base.
    """
    
    def __init__(self):
        super().__init__(User)
    
    @handle_async_db_errors("get user by email")
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email with automatic error handling."""
        users = await self.get_multi(
            db, 
            filters={"email": email}, 
            limit=1
        )
        return users[0] if users else None
    
    @retry_async_db_operation(max_retries=3, operation_name="create user with retry")
    async def create_with_retry(self, db: AsyncSession, user_data: UserProfileCreate) -> User:
        """Create user with automatic retry on transient errors."""
        return await self.create(db, obj_in=user_data)
    
    async def get_active_users(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users with relationship loading."""
        return await self.get_multi(
            db,
            filters={"is_active": True},
            skip=skip,
            limit=limit,
            order_by="-created_at"
        )
    
    async def bulk_activate_users(self, db: AsyncSession, user_ids: List[str]) -> int:
        """Bulk activate users using transaction management."""
        async with async_transaction_rollback(db):
            updates = [{"id": user_id, "is_active": True} for user_id in user_ids]
            return await AsyncQueryUtils.bulk_update(db, User, updates)
    
    async def create_user_with_profile(
        self, 
        db: AsyncSession, 
        user_data: dict, 
        profile_data: dict
    ) -> User:
        """Create user and profile in a single transaction."""
        async def create_operations(session: AsyncSession):
            # Create user
            user = await self.create(session, obj_in=user_data)
            
            # Create profile (would need profile service)
            # profile = await profile_service.create(session, obj_in={...profile_data, "user_id": user.id})
            
            return user
        
        return await with_transaction(db, create_operations)


# Example usage patterns
async def example_usage():
    """
    Example of how to use the async service classes.
    """
    # This would normally be injected via FastAPI dependency
    # db: AsyncSession = Depends(get_async_db)
    
    user_service = AsyncUserService()
    
    # Basic CRUD operations
    # user = await user_service.get(db, user_id="some-id")
    # users = await user_service.get_multi(db, skip=0, limit=10)
    # new_user = await user_service.create(db, obj_in=user_create_data)
    
    # Service-specific operations with error handling
    # user = await user_service.get_by_email(db, "user@example.com")
    # active_users = await user_service.get_active_users(db)
    
    # Bulk operations with transaction management
    # updated_count = await user_service.bulk_activate_users(db, ["id1", "id2", "id3"])
    
    print("Example service created successfully!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())