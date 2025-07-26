"""
Base service classes and utilities for async database operations.

This module provides common CRUD operations, query utilities, and transaction
management for async database operations across all services.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
import logging

from app.models.base import Base

# Type variables for generic base service
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

logger = logging.getLogger(__name__)


class AsyncBaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base async service class providing common CRUD operations and utilities.
    
    This class provides a foundation for all async service classes with:
    - Standard CRUD operations (Create, Read, Update, Delete)
    - Query utilities and helpers
    - Transaction management utilities
    - Error handling patterns
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize the base service with a SQLAlchemy model.
        
        Args:
            model: The SQLAlchemy model class this service operates on
        """
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """
        Get a single record by ID.
        
        Args:
            db: Async database session
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        try:
            stmt = select(self.model).where(self.model.id == id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {self.model.__name__} by id {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while retrieving {self.model.__name__}"
            )
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get multiple records with optional filtering, pagination, and ordering.
        
        Args:
            db: Async database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            filters: Dictionary of field:value pairs for filtering
            order_by: Field name to order by (prefix with '-' for descending)
            
        Returns:
            List of model instances
        """
        try:
            stmt = select(self.model)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            stmt = stmt.where(getattr(self.model, field).in_(value))
                        else:
                            stmt = stmt.where(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by:
                if order_by.startswith('-'):
                    field_name = order_by[1:]
                    if hasattr(self.model, field_name):
                        stmt = stmt.order_by(getattr(self.model, field_name).desc())
                else:
                    if hasattr(self.model, order_by):
                        stmt = stmt.order_by(getattr(self.model, order_by))
            
            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)
            
            result = await db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while retrieving {self.model.__name__} records"
            )
    
    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Async database session
            obj_in: Pydantic schema with creation data
            
        Returns:
            Created model instance
        """
        try:
            obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
            db_obj = self.model(**obj_in_data)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while creating {self.model.__name__}"
            )
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        db_obj: ModelType, 
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update an existing record.
        
        Args:
            db: Async database session
            db_obj: Existing model instance to update
            obj_in: Pydantic schema or dict with update data
            
        Returns:
            Updated model instance
        """
        try:
            obj_data = obj_in.dict(exclude_unset=True) if hasattr(obj_in, 'dict') else obj_in
            
            for field, value in obj_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            await db.commit()
            await db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while updating {self.model.__name__}"
            )
    
    async def delete(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        """
        Delete a record by ID.
        
        Args:
            db: Async database session
            id: Primary key value
            
        Returns:
            Deleted model instance or None if not found
        """
        try:
            obj = await self.get(db, id)
            if obj:
                await db.delete(obj)
                await db.commit()
                return obj
            return None
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while deleting {self.model.__name__}"
            )
    
    async def count(
        self, 
        db: AsyncSession, 
        *, 
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.
        
        Args:
            db: Async database session
            filters: Dictionary of field:value pairs for filtering
            
        Returns:
            Number of matching records
        """
        try:
            stmt = select(func.count(self.model.id))
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            stmt = stmt.where(getattr(self.model, field).in_(value))
                        else:
                            stmt = stmt.where(getattr(self.model, field) == value)
            
            result = await db.execute(stmt)
            return result.scalar()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while counting {self.model.__name__} records"
            )
    
    async def exists(self, db: AsyncSession, *, id: Any) -> bool:
        """
        Check if a record exists by ID.
        
        Args:
            db: Async database session
            id: Primary key value
            
        Returns:
            True if record exists, False otherwise
        """
        try:
            stmt = select(func.count(self.model.id)).where(self.model.id == id)
            result = await db.execute(stmt)
            count = result.scalar()
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while checking {self.model.__name__} existence"
            )


class AsyncQueryUtils:
    """
    Utility class providing common async query patterns and helpers.
    """
    
    @staticmethod
    async def get_or_404(db: AsyncSession, model: Type[ModelType], id: Any) -> ModelType:
        """
        Get a record by ID or raise 404 if not found.
        
        Args:
            db: Async database session
            model: SQLAlchemy model class
            id: Primary key value
            
        Returns:
            Model instance
            
        Raises:
            HTTPException: 404 if record not found
        """
        try:
            stmt = select(model).where(model.id == id)
            result = await db.execute(stmt)
            obj = result.scalar_one_or_none()
            
            if not obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{model.__name__} not found"
                )
            
            return obj
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} by id {id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while retrieving {model.__name__}"
            )
    
    @staticmethod
    async def get_with_relationships(
        db: AsyncSession, 
        model: Type[ModelType], 
        id: Any, 
        relationships: List[str]
    ) -> Optional[ModelType]:
        """
        Get a record with eagerly loaded relationships.
        
        Args:
            db: Async database session
            model: SQLAlchemy model class
            id: Primary key value
            relationships: List of relationship names to load
            
        Returns:
            Model instance with loaded relationships or None
        """
        try:
            stmt = select(model).where(model.id == id)
            
            # Add relationship loading
            for rel in relationships:
                if hasattr(model, rel):
                    stmt = stmt.options(selectinload(getattr(model, rel)))
            
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting {model.__name__} with relationships: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while retrieving {model.__name__} with relationships"
            )
    
    @staticmethod
    async def bulk_create(
        db: AsyncSession, 
        model: Type[ModelType], 
        objects: List[Dict[str, Any]]
    ) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            db: Async database session
            model: SQLAlchemy model class
            objects: List of dictionaries with creation data
            
        Returns:
            List of created model instances
        """
        try:
            db_objects = [model(**obj_data) for obj_data in objects]
            db.add_all(db_objects)
            await db.commit()
            
            # Refresh all objects to get generated IDs
            for obj in db_objects:
                await db.refresh(obj)
            
            return db_objects
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error bulk creating {model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while bulk creating {model.__name__} records"
            )
    
    @staticmethod
    async def bulk_update(
        db: AsyncSession, 
        model: Type[ModelType], 
        updates: List[Dict[str, Any]]
    ) -> int:
        """
        Update multiple records in a single transaction.
        
        Args:
            db: Async database session
            model: SQLAlchemy model class
            updates: List of dictionaries with 'id' and update data
            
        Returns:
            Number of updated records
        """
        try:
            updated_count = 0
            
            for update_data in updates:
                if 'id' not in update_data:
                    continue
                
                record_id = update_data.pop('id')
                stmt = update(model).where(model.id == record_id).values(**update_data)
                result = await db.execute(stmt)
                updated_count += result.rowcount
            
            await db.commit()
            return updated_count
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error bulk updating {model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while bulk updating {model.__name__} records"
            )
    
    @staticmethod
    def build_filter_conditions(model: Type[ModelType], filters: Dict[str, Any]):
        """
        Build SQLAlchemy filter conditions from a dictionary.
        
        Args:
            model: SQLAlchemy model class
            filters: Dictionary of filter conditions
            
        Returns:
            List of SQLAlchemy filter conditions
        """
        conditions = []
        
        for field, value in filters.items():
            if not hasattr(model, field):
                continue
            
            field_attr = getattr(model, field)
            
            if isinstance(value, dict):
                # Handle complex filters like {'gte': 10, 'lte': 20}
                for op, op_value in value.items():
                    if op == 'gte':
                        conditions.append(field_attr >= op_value)
                    elif op == 'lte':
                        conditions.append(field_attr <= op_value)
                    elif op == 'gt':
                        conditions.append(field_attr > op_value)
                    elif op == 'lt':
                        conditions.append(field_attr < op_value)
                    elif op == 'ne':
                        conditions.append(field_attr != op_value)
                    elif op == 'like':
                        conditions.append(field_attr.like(f"%{op_value}%"))
                    elif op == 'ilike':
                        conditions.append(field_attr.ilike(f"%{op_value}%"))
                    elif op == 'in':
                        conditions.append(field_attr.in_(op_value))
                    elif op == 'not_in':
                        conditions.append(~field_attr.in_(op_value))
            elif isinstance(value, list):
                conditions.append(field_attr.in_(value))
            else:
                conditions.append(field_attr == value)
        
        return conditions


class AsyncTransactionManager:
    """
    Utility class for managing async database transactions.
    
    Provides context managers and utilities for handling complex transactions,
    rollbacks, and nested transaction scenarios.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize transaction manager with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def __aenter__(self):
        """Enter async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager with automatic rollback on exception."""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
    
    async def commit(self):
        """Commit the current transaction."""
        try:
            await self.db.commit()
        except SQLAlchemyError as e:
            logger.error(f"Error committing transaction: {e}")
            await self.rollback()
            raise
    
    async def rollback(self):
        """Rollback the current transaction."""
        try:
            await self.db.rollback()
        except SQLAlchemyError as e:
            logger.error(f"Error rolling back transaction: {e}")
            raise
    
    async def execute_in_transaction(self, operations: List[callable]) -> List[Any]:
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: List of async callable operations
            
        Returns:
            List of operation results
            
        Raises:
            Exception: If any operation fails, all operations are rolled back
        """
        results = []
        
        try:
            for operation in operations:
                result = await operation(self.db)
                results.append(result)
            
            await self.commit()
            return results
        except Exception as e:
            await self.rollback()
            logger.error(f"Transaction failed, rolled back: {e}")
            raise
    
    async def safe_execute(self, operation: callable, *args, **kwargs) -> Any:
        """
        Execute an operation with automatic transaction management.
        
        Args:
            operation: Async callable to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation result
            
        Raises:
            Exception: If operation fails after rollback
        """
        try:
            result = await operation(self.db, *args, **kwargs)
            await self.commit()
            return result
        except Exception as e:
            await self.rollback()
            logger.error(f"Operation failed, rolled back: {e}")
            raise


# Utility functions for common transaction patterns
async def with_transaction(db: AsyncSession, operation: callable, *args, **kwargs) -> Any:
    """
    Execute an operation within a transaction context.
    
    Args:
        db: Async database session
        operation: Async callable to execute
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Operation result
    """
    async with AsyncTransactionManager(db) as tx:
        return await operation(db, *args, **kwargs)


async def batch_operations(db: AsyncSession, operations: List[callable]) -> List[Any]:
    """
    Execute multiple operations in a single transaction.
    
    Args:
        db: Async database session
        operations: List of async callable operations
        
    Returns:
        List of operation results
    """
    async with AsyncTransactionManager(db) as tx:
        return await tx.execute_in_transaction(operations)