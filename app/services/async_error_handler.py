"""
Async error handling utilities for database operations.

This module provides comprehensive error handling patterns, retry logic,
and connection management utilities for async database operations.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Type, Union, Dict
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    SQLAlchemyError, 
    IntegrityError, 
    OperationalError, 
    DisconnectionError,
    TimeoutError as SQLTimeoutError,
    StatementError,
    DataError,
    DatabaseError
)
from fastapi import HTTPException, status
import asyncpg

logger = logging.getLogger(__name__)


class AsyncDatabaseError(Exception):
    """Base exception for async database operations."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class AsyncConnectionError(AsyncDatabaseError):
    """Exception for database connection issues."""
    pass


class AsyncTransactionError(AsyncDatabaseError):
    """Exception for transaction-related issues."""
    pass


class AsyncRetryableError(AsyncDatabaseError):
    """Exception for errors that can be retried."""
    pass


class AsyncErrorHandler:
    """
    Comprehensive async error handler for database operations.
    
    Provides error classification, logging, and appropriate HTTP responses
    for different types of database errors.
    """
    
    # Mapping of SQLAlchemy errors to HTTP status codes and messages
    ERROR_MAPPINGS = {
        IntegrityError: {
            'status_code': status.HTTP_409_CONFLICT,
            'detail': 'Data integrity constraint violation',
            'retryable': False
        },
        OperationalError: {
            'status_code': status.HTTP_503_SERVICE_UNAVAILABLE,
            'detail': 'Database operation failed',
            'retryable': True
        },
        DisconnectionError: {
            'status_code': status.HTTP_503_SERVICE_UNAVAILABLE,
            'detail': 'Database connection lost',
            'retryable': True
        },
        SQLTimeoutError: {
            'status_code': status.HTTP_504_GATEWAY_TIMEOUT,
            'detail': 'Database operation timed out',
            'retryable': True
        },
        StatementError: {
            'status_code': status.HTTP_400_BAD_REQUEST,
            'detail': 'Invalid database query',
            'retryable': False
        },
        DataError: {
            'status_code': status.HTTP_400_BAD_REQUEST,
            'detail': 'Invalid data format',
            'retryable': False
        },
        DatabaseError: {
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'detail': 'Database error occurred',
            'retryable': False
        }
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> Dict[str, Any]:
        """
        Classify a database error and return appropriate response information.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Dictionary with status_code, detail, and retryable flag
        """
        error_type = type(error)
        
        # Check for specific SQLAlchemy errors
        for exc_type, mapping in cls.ERROR_MAPPINGS.items():
            if isinstance(error, exc_type):
                return mapping.copy()
        
        # Check for asyncpg specific errors
        if isinstance(error, asyncpg.PostgresError):
            return cls._handle_postgres_error(error)
        
        # Default to internal server error
        return {
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'detail': 'An unexpected database error occurred',
            'retryable': False
        }
    
    @classmethod
    def _handle_postgres_error(cls, error: asyncpg.PostgresError) -> Dict[str, Any]:
        """
        Handle PostgreSQL-specific errors from asyncpg.
        
        Args:
            error: PostgreSQL error from asyncpg
            
        Returns:
            Dictionary with error classification
        """
        # Connection errors
        if isinstance(error, (asyncpg.ConnectionDoesNotExistError, 
                             asyncpg.ConnectionFailureError)):
            return {
                'status_code': status.HTTP_503_SERVICE_UNAVAILABLE,
                'detail': 'Database connection failed',
                'retryable': True
            }
        
        # Constraint violations
        if isinstance(error, asyncpg.UniqueViolationError):
            return {
                'status_code': status.HTTP_409_CONFLICT,
                'detail': 'Unique constraint violation',
                'retryable': False
            }
        
        if isinstance(error, asyncpg.ForeignKeyViolationError):
            return {
                'status_code': status.HTTP_409_CONFLICT,
                'detail': 'Foreign key constraint violation',
                'retryable': False
            }
        
        if isinstance(error, asyncpg.CheckViolationError):
            return {
                'status_code': status.HTTP_400_BAD_REQUEST,
                'detail': 'Data validation constraint violation',
                'retryable': False
            }
        
        # Syntax and data errors
        if isinstance(error, asyncpg.SyntaxOrAccessError):
            return {
                'status_code': status.HTTP_400_BAD_REQUEST,
                'detail': 'Invalid query syntax or access denied',
                'retryable': False
            }
        
        # Default PostgreSQL error
        return {
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
            'detail': f'PostgreSQL error: {error.sqlstate}',
            'retryable': False
        }
    
    @classmethod
    def handle_error(cls, error: Exception, operation_name: str = "database operation") -> HTTPException:
        """
        Handle a database error and return appropriate HTTPException.
        
        Args:
            error: The exception that occurred
            operation_name: Name of the operation for logging
            
        Returns:
            HTTPException with appropriate status code and message
        """
        error_info = cls.classify_error(error)
        
        # Log the error with appropriate level
        if error_info['retryable']:
            logger.warning(f"Retryable error in {operation_name}: {error}")
        else:
            logger.error(f"Non-retryable error in {operation_name}: {error}")
        
        return HTTPException(
            status_code=error_info['status_code'],
            detail=error_info['detail']
        )
    
    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """
        Check if an error is retryable.
        
        Args:
            error: The exception to check
            
        Returns:
            True if the error can be retried, False otherwise
        """
        error_info = cls.classify_error(error)
        return error_info.get('retryable', False)


class AsyncRetryManager:
    """
    Retry manager for async database operations.
    
    Provides configurable retry logic with exponential backoff
    for transient database errors.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay
    
    async def execute_with_retry(
        self,
        operation: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Async callable to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                # Check if error is retryable
                if not AsyncErrorHandler.is_retryable(e):
                    logger.error(f"Non-retryable error on attempt {attempt + 1}: {e}")
                    raise
                
                # If this was the last attempt, raise the error
                if attempt == self.max_retries:
                    logger.error(f"All retry attempts failed. Last error: {e}")
                    raise
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        if last_error:
            raise last_error


# Decorator for automatic error handling
def handle_async_db_errors(operation_name: str = "database operation"):
    """
    Decorator for automatic async database error handling.
    
    Args:
        operation_name: Name of the operation for logging
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SQLAlchemyError as e:
                raise AsyncErrorHandler.handle_error(e, operation_name)
            except asyncpg.PostgresError as e:
                raise AsyncErrorHandler.handle_error(e, operation_name)
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred"
                )
        return wrapper
    return decorator


# Decorator for automatic retry with error handling
def retry_async_db_operation(
    max_retries: int = 3,
    base_delay: float = 1.0,
    operation_name: str = "database operation"
):
    """
    Decorator for automatic retry with error handling.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries
        operation_name: Name of the operation for logging
        
    Returns:
        Decorated function with retry and error handling
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_manager = AsyncRetryManager(max_retries=max_retries, base_delay=base_delay)
            
            try:
                return await retry_manager.execute_with_retry(func, *args, **kwargs)
            except SQLAlchemyError as e:
                raise AsyncErrorHandler.handle_error(e, operation_name)
            except asyncpg.PostgresError as e:
                raise AsyncErrorHandler.handle_error(e, operation_name)
            except Exception as e:
                logger.error(f"Unexpected error in {operation_name}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred"
                )
        return wrapper
    return decorator


@asynccontextmanager
async def async_transaction_rollback(db: AsyncSession):
    """
    Context manager for automatic transaction rollback on error.
    
    Args:
        db: Async database session
        
    Yields:
        Database session
        
    Usage:
        async with async_transaction_rollback(db) as session:
            # Perform database operations
            # Automatic rollback on exception
    """
    try:
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}")
        raise


class AsyncConnectionRetryManager:
    """
    Manager for handling database connection retries and recovery.
    """
    
    def __init__(self, max_connection_retries: int = 5, connection_retry_delay: float = 2.0):
        """
        Initialize connection retry manager.
        
        Args:
            max_connection_retries: Maximum connection retry attempts
            connection_retry_delay: Delay between connection retries
        """
        self.max_connection_retries = max_connection_retries
        self.connection_retry_delay = connection_retry_delay
    
    async def ensure_connection(self, db: AsyncSession) -> bool:
        """
        Ensure database connection is healthy, retry if needed.
        
        Args:
            db: Async database session
            
        Returns:
            True if connection is healthy, False otherwise
        """
        for attempt in range(self.max_connection_retries):
            try:
                # Simple query to test connection
                await db.execute("SELECT 1")
                return True
            except (DisconnectionError, OperationalError, asyncpg.ConnectionFailureError) as e:
                logger.warning(f"Connection test failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_connection_retries - 1:
                    await asyncio.sleep(self.connection_retry_delay)
                    continue
                else:
                    logger.error("All connection retry attempts failed")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error during connection test: {e}")
                return False
        
        return False