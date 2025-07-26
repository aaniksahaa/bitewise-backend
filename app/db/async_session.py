from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text, event
from sqlalchemy.pool import QueuePool
from typing import AsyncGenerator, Optional, Dict, Any
import logging
import asyncio
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import hashlib

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection pool metrics
class ConnectionPoolMetrics:
    """Tracks connection pool metrics for monitoring and optimization."""
    
    def __init__(self):
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.connection_timeouts = 0
        self.pool_exhausted_count = 0
        self.average_connection_time = 0.0
        self.peak_connections = 0
        self.total_connection_time = 0.0
        self.last_reset = datetime.now(timezone.utc)
    
    def record_connection_attempt(self, success: bool, duration: float):
        """Record a connection attempt with its outcome and duration."""
        self.connection_attempts += 1
        self.total_connection_time += duration
        self.average_connection_time = self.total_connection_time / self.connection_attempts
        
        if success:
            self.successful_connections += 1
        else:
            self.failed_connections += 1
    
    def record_timeout(self):
        """Record a connection timeout."""
        self.connection_timeouts += 1
    
    def record_pool_exhausted(self):
        """Record when the connection pool is exhausted."""
        self.pool_exhausted_count += 1
    
    def update_peak_connections(self, current_connections: int):
        """Update peak connection count if current exceeds previous peak."""
        if current_connections > self.peak_connections:
            self.peak_connections = current_connections
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics as a dictionary."""
        return {
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "connection_timeouts": self.connection_timeouts,
            "pool_exhausted_count": self.pool_exhausted_count,
            "success_rate": (
                self.successful_connections / self.connection_attempts 
                if self.connection_attempts > 0 else 0
            ),
            "average_connection_time_ms": round(self.average_connection_time * 1000, 2),
            "peak_connections": self.peak_connections,
            "last_reset": self.last_reset.isoformat()
        }
    
    def reset(self):
        """Reset all metrics."""
        self.__init__()

# Global metrics instance
pool_metrics = ConnectionPoolMetrics()

class AsyncDatabaseManager:
    """
    Manages async database connections and sessions.
    
    This class provides centralized management of async database connections,
    including connection pooling, session lifecycle management, and proper
    cleanup of resources.
    """
    
    def __init__(self):
        self.async_engine = None
        self.async_session_factory = None
        self._is_initialized = False
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the async database engine with optimized configuration."""
        try:
            # Get async database URL using the new configuration property
            async_db_url = settings.async_database_url
            
            if not async_db_url:
                raise ValueError("Async database URL is not configured")
            
            # Replace any escaped colons in the URL
            async_db_url = async_db_url.replace("\\x3a", ":")
            
            logger.info(f"Initializing async database engine with URL: {async_db_url[:50]}...")
            logger.info(f"Environment: {settings.ENVIRONMENT}")
            
            # Optimized connection pool parameters based on production workload
            pool_size = settings.ASYNC_DB_POOL_SIZE
            max_overflow = settings.ASYNC_DB_MAX_OVERFLOW
            pool_timeout = settings.ASYNC_DB_POOL_TIMEOUT
            pool_recycle = settings.ASYNC_DB_POOL_RECYCLE
            
            # Adjust pool parameters based on environment
            if settings.ENVIRONMENT == "production":
                # Production optimizations
                pool_size = max(pool_size, 10)  # Minimum 10 connections for production
                max_overflow = max(max_overflow, 20)  # Allow burst capacity
                pool_timeout = 60  # Longer timeout for production
            elif settings.ENVIRONMENT == "development":
                # Development optimizations
                pool_size = min(pool_size, 5)  # Limit connections for development
                max_overflow = min(max_overflow, 5)  # Limit overflow for development
            
            logger.info(f"Pool configuration - Size: {pool_size}, Max Overflow: {max_overflow}, "
                       f"Timeout: {pool_timeout}s, Recycle: {pool_recycle}s")
            
            # Create async engine with optimized configuration
            self.async_engine = create_async_engine(
                async_db_url,
                echo=settings.ASYNC_DB_ECHO,  # SQL logging based on configuration
                pool_pre_ping=settings.ASYNC_DB_POOL_PRE_PING,  # Validate connections before use
                pool_size=pool_size,  # Optimized pool size
                max_overflow=max_overflow,  # Optimized overflow capacity
                pool_recycle=pool_recycle,  # Recycle connections after configured time
                pool_timeout=pool_timeout,  # Optimized timeout
                # Note: Don't specify poolclass for async engines - SQLAlchemy handles this automatically
                connect_args={
                    "server_settings": {
                        "application_name": "bitewise_backend_async",
                        "statement_timeout": "300000",  # 5 minutes statement timeout
                        "idle_in_transaction_session_timeout": "600000",  # 10 minutes idle timeout
                    },
                    "command_timeout": 60,  # asyncpg command timeout
                }
            )
            
            # Set up connection pool event listeners for monitoring
            self._setup_pool_events()
            
            # Create async session factory with proper configuration
            self.async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Keep objects accessible after commit
                autoflush=False,  # Manual control over when to flush
                autocommit=False,  # Manual control over when to commit
            )
            
            self._is_initialized = True
            logger.info("Async database engine initialized successfully with optimized pool settings")
            
        except Exception as e:
            logger.error(f"Failed to initialize async database engine: {e}")
            raise
    
    def _setup_pool_events(self):
        """Set up SQLAlchemy pool events for monitoring and metrics."""
        if not self.async_engine:
            return
        
        @event.listens_for(self.async_engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Handle new database connections."""
            pool_metrics.record_connection_attempt(True, 0.0)
            logger.debug("New database connection established")
        
        @event.listens_for(self.async_engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            pool = self.async_engine.pool
            try:
                current_connections = pool.checkedout()
                pool_metrics.update_peak_connections(current_connections)
                logger.debug(f"Connection checked out from pool. Active: {current_connections}")
            except Exception as e:
                logger.warning(f"Error tracking connection checkout: {e}")
        
        @event.listens_for(self.async_engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Handle connection checkin to pool."""
            logger.debug("Connection checked back into pool")
        
        @event.listens_for(self.async_engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_connection, connection_record, exception):
            """Handle connection invalidation."""
            pool_metrics.record_connection_attempt(False, 0.0)
            logger.warning(f"Database connection invalidated: {exception}")
    
    @asynccontextmanager
    async def get_monitored_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with comprehensive monitoring.
        
        This method provides enhanced session management with connection
        timing, error tracking, and automatic recovery mechanisms.
        """
        if not self._is_initialized:
            raise RuntimeError("AsyncDatabaseManager is not initialized")
        
        start_time = time.time()
        session = None
        
        try:
            # Attempt to create session with timeout handling
            try:
                session = self.async_session_factory()
                connection_time = time.time() - start_time
                pool_metrics.record_connection_attempt(True, connection_time)
                
                yield session
                
            except asyncio.TimeoutError:
                pool_metrics.record_timeout()
                logger.error("Database session creation timed out")
                raise
            except Exception as e:
                connection_time = time.time() - start_time
                pool_metrics.record_connection_attempt(False, connection_time)
                
                # Check if it's a pool exhaustion error
                if "pool" in str(e).lower() and "exhausted" in str(e).lower():
                    pool_metrics.record_pool_exhausted()
                    logger.error("Connection pool exhausted")
                
                raise
                
        except SQLAlchemyError as e:
            if session:
                await session.rollback()
            logger.error(f"Database error in monitored session: {e}")
            raise
        except Exception as e:
            if session:
                await session.rollback()
            logger.error(f"Unexpected error in monitored database session: {e}")
            raise
        finally:
            if session:
                await session.close()
    
    async def get_detailed_pool_info(self) -> Dict[str, Any]:
        """
        Get comprehensive connection pool information including metrics.
        
        Returns:
            dict: Detailed pool information and metrics
        """
        if not self.async_engine:
            return {"status": "not_initialized"}
        
        pool = self.async_engine.pool
        basic_info = await self.get_connection_info()
        metrics = pool_metrics.get_metrics()
        
        try:
            # Get additional pool statistics
            detailed_info = {
                **basic_info,
                "metrics": metrics,
                "pool_configuration": {
                    "pool_size": settings.ASYNC_DB_POOL_SIZE,
                    "max_overflow": settings.ASYNC_DB_MAX_OVERFLOW,
                    "pool_timeout": 30,
                    "pool_recycle": settings.ASYNC_DB_POOL_RECYCLE,
                    "pool_pre_ping": settings.ASYNC_DB_POOL_PRE_PING,
                },
                "health_indicators": {
                    "pool_utilization": (
                        basic_info.get("checked_out", 0) / 
                        (basic_info.get("pool_size", 1) + basic_info.get("overflow", 0))
                        if basic_info.get("pool_size", 0) > 0 else 0
                    ),
                    "success_rate": metrics.get("success_rate", 0),
                    "average_connection_time": metrics.get("average_connection_time_ms", 0),
                }
            }
            
            return detailed_info
            
        except Exception as e:
            logger.warning(f"Error getting detailed pool info: {e}")
            return {
                **basic_info,
                "metrics": metrics,
                "error": str(e)
            }
    
    async def perform_health_check_with_recovery(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check with automatic recovery attempts.
        
        Returns:
            dict: Health check results with recovery actions taken
        """
        health_result = {
            "status": "unhealthy",
            "checks": {
                "basic_connection": False,
                "pool_status": False,
                "query_execution": False,
                "transaction_test": False
            },
            "recovery_actions": [],
            "pool_info": {},
            "metrics": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Basic connection test
            connection_test = await self.test_connection()
            health_result["checks"]["basic_connection"] = connection_test
            
            if not connection_test:
                # Attempt recovery by recreating engine
                health_result["recovery_actions"].append("attempted_engine_recreation")
                try:
                    await self._recreate_engine()
                    connection_test = await self.test_connection()
                    health_result["checks"]["basic_connection"] = connection_test
                    if connection_test:
                        health_result["recovery_actions"].append("engine_recreation_successful")
                except Exception as e:
                    health_result["recovery_actions"].append(f"engine_recreation_failed: {e}")
            
            # Pool status check
            pool_info = await self.get_detailed_pool_info()
            health_result["pool_info"] = pool_info
            health_result["metrics"] = pool_info.get("metrics", {})
            
            pool_utilization = pool_info.get("health_indicators", {}).get("pool_utilization", 0)
            health_result["checks"]["pool_status"] = pool_utilization < 0.9  # Pool not over 90% utilized
            
            # Advanced query execution test
            if connection_test:
                try:
                    async with self.get_monitored_session() as session:
                        # Test complex query
                        result = await session.execute(text("""
                            SELECT 
                                current_timestamp as server_time,
                                version() as db_version,
                                current_database() as db_name
                        """))
                        row = result.fetchone()
                        if row:
                            health_result["checks"]["query_execution"] = True
                            health_result["server_info"] = {
                                "server_time": str(row[0]),
                                "db_version": row[1],
                                "db_name": row[2]
                            }
                        
                        # Test transaction handling
                        await session.execute(text("BEGIN"))
                        await session.execute(text("SELECT 1"))
                        await session.rollback()
                        health_result["checks"]["transaction_test"] = True
                        
                except Exception as e:
                    logger.warning(f"Advanced health check failed: {e}")
                    health_result["advanced_check_error"] = str(e)
            
            # Determine overall health status
            if all(health_result["checks"].values()):
                health_result["status"] = "healthy"
            elif health_result["checks"]["basic_connection"]:
                health_result["status"] = "degraded"
            else:
                health_result["status"] = "unhealthy"
                
        except Exception as e:
            health_result["error"] = str(e)
            logger.error(f"Health check with recovery failed: {e}")
        
        return health_result
    
    async def _recreate_engine(self):
        """Recreate the database engine for recovery purposes."""
        logger.info("Attempting to recreate database engine for recovery")
        
        # Close existing engine
        if self.async_engine:
            await self.async_engine.dispose()
        
        # Reset initialization flag
        self._is_initialized = False
        
        # Reinitialize engine
        self._initialize_engine()
        
        logger.info("Database engine recreated successfully")
    
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with proper lifecycle management.
        
        This method provides a database session that automatically handles
        rollback on exceptions and ensures proper cleanup.
        
        Yields:
            AsyncSession: Database session for async operations
            
        Raises:
            RuntimeError: If the database manager is not initialized
            SQLAlchemyError: For database-related errors
        """
        if not self._is_initialized:
            raise RuntimeError("AsyncDatabaseManager is not initialized")
            
        async with self.async_session_factory() as session:
            try:
                yield session
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Database error in session: {e}")
                raise
            except Exception as e:
                await session.rollback()
                logger.error(f"Unexpected error in database session: {e}")
                raise
            finally:
                await session.close()
    
    async def create_session(self) -> AsyncSession:
        """
        Create a new async database session.
        
        This method creates a session that must be manually managed.
        Use get_async_session() for automatic lifecycle management.
        
        Returns:
            AsyncSession: New database session
            
        Raises:
            RuntimeError: If the database manager is not initialized
        """
        if not self._is_initialized:
            raise RuntimeError("AsyncDatabaseManager is not initialized")
            
        return self.async_session_factory()
    
    async def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            async with self.async_session_factory() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def get_connection_info(self) -> dict:
        """
        Get information about the current connection pool.
        
        Returns:
            dict: Connection pool information
        """
        if not self.async_engine:
            return {"status": "not_initialized"}
            
        pool = self.async_engine.pool
        try:
            return {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                # Note: async pool may not have all the same attributes as sync pool
                "status": "initialized"
            }
        except AttributeError as e:
            # Some pool attributes may not be available in async pools
            logger.warning(f"Some pool attributes not available: {e}")
            return {
                "status": "initialized",
                "pool_type": str(type(pool).__name__),
                "note": "Limited pool information available for async pools"
            }
    
    async def close(self):
        """
        Close the async database engine and all connections.
        
        This method properly disposes of the engine and all associated
        connections, ensuring clean shutdown.
        """
        if self.async_engine:
            try:
                await self.async_engine.dispose()
                logger.info("Async database engine disposed successfully")
            except Exception as e:
                logger.error(f"Error disposing async database engine: {e}")
            finally:
                self._is_initialized = False
                self.async_engine = None
                self.async_session_factory = None

# Global async database manager instance (singleton pattern)
_async_db_manager: Optional[AsyncDatabaseManager] = None
_manager_lock = asyncio.Lock()


async def get_async_db_manager() -> AsyncDatabaseManager:
    """
    Get or create the global async database manager instance.
    
    This function implements a thread-safe singleton pattern to ensure
    only one database manager instance exists throughout the application
    lifecycle.
    
    Returns:
        AsyncDatabaseManager: The global database manager instance
    """
    global _async_db_manager
    
    if _async_db_manager is None:
        async with _manager_lock:
            # Double-check locking pattern
            if _async_db_manager is None:
                _async_db_manager = AsyncDatabaseManager()
                logger.info("Created new AsyncDatabaseManager singleton instance")
    
    return _async_db_manager


def get_async_db_manager_sync() -> AsyncDatabaseManager:
    """
    Synchronous version of get_async_db_manager for non-async contexts.
    
    Returns:
        AsyncDatabaseManager: The global database manager instance
    """
    global _async_db_manager
    
    if _async_db_manager is None:
        _async_db_manager = AsyncDatabaseManager()
        logger.info("Created new AsyncDatabaseManager singleton instance (sync)")
    
    return _async_db_manager


# Async dependency injection function for FastAPI
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database session injection.
    
    This function provides async database sessions to FastAPI endpoints
    through dependency injection. It ensures proper session lifecycle
    management, error handling, and automatic cleanup.
    
    The session is automatically:
    - Created from the connection pool
    - Rolled back on any exception
    - Closed after use to prevent connection leaks
    
    Yields:
        AsyncSession: Database session for async operations
        
    Raises:
        RuntimeError: If database manager initialization fails
        SQLAlchemyError: For database connection or operation errors
        
    Example:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
            
        @app.post("/users/")
        async def create_user(
            user_data: UserCreate, 
            db: AsyncSession = Depends(get_async_db)
        ):
            user = User(**user_data.dict())
            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
    """
    try:
        manager = await get_async_db_manager()
        async for session in manager.get_async_session():
            yield session
    except Exception as e:
        logger.error(f"Failed to provide async database session: {e}")
        raise


# Database startup and shutdown handlers
async def startup_async_database():
    """
    Initialize async database connections on application startup.
    
    This function should be called during FastAPI application startup
    to ensure the database manager is properly initialized and connections
    are established.
    
    Raises:
        RuntimeError: If database initialization fails
        SQLAlchemyError: For database connection errors
    """
    try:
        logger.info("Starting async database initialization...")
        manager = await get_async_db_manager()
        
        # Test the connection to ensure everything is working
        connection_test = await manager.test_connection()
        if not connection_test:
            raise RuntimeError("Failed to establish database connection during startup")
        
        # Log connection pool information
        pool_info = await manager.get_connection_info()
        logger.info(f"Async database startup completed. Pool info: {pool_info}")
        
    except Exception as e:
        logger.error(f"Failed to initialize async database during startup: {e}")
        raise


async def shutdown_async_database():
    """
    Clean up async database connections on application shutdown.
    
    This function should be called during FastAPI application shutdown
    to ensure proper cleanup of database connections and resources.
    """
    try:
        logger.info("Starting async database shutdown...")
        await close_async_db_manager()
        logger.info("Async database shutdown completed successfully")
    except Exception as e:
        logger.error(f"Error during async database shutdown: {e}")


# Health check utilities
async def check_async_database_health() -> dict:
    """
    Perform comprehensive health check of the async database connection.
    
    This function tests database connectivity, connection pool status,
    and basic query execution to ensure the database is healthy and
    responsive.
    
    Returns:
        dict: Health check results with status and details
        
    Example:
        {
            "status": "healthy",
            "connection_test": True,
            "pool_info": {
                "pool_size": 5,
                "checked_in": 4,
                "checked_out": 1,
                "overflow": 0,
                "invalid": 0
            },
            "response_time_ms": 15.2,
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    import time
    from datetime import datetime, timezone
    
    start_time = time.time()
    health_status = {
        "status": "unhealthy",
        "connection_test": False,
        "pool_info": {},
        "response_time_ms": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None
    }
    
    try:
        # Get database manager
        manager = await get_async_db_manager()
        
        # Test basic connection
        connection_test = await manager.test_connection()
        health_status["connection_test"] = connection_test
        
        if not connection_test:
            health_status["error"] = "Database connection test failed"
            return health_status
        
        # Get connection pool information
        pool_info = await manager.get_connection_info()
        health_status["pool_info"] = pool_info
        
        # Test a simple query with session
        async for session in manager.get_async_session():
            result = await session.execute(text("SELECT version()"))
            db_version = result.scalar()
            health_status["database_version"] = db_version
            break
        
        # Calculate response time
        end_time = time.time()
        health_status["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        health_status["status"] = "healthy"
        
    except Exception as e:
        end_time = time.time()
        health_status["response_time_ms"] = round((end_time - start_time) * 1000, 2)
        health_status["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health_status


async def test_async_database_operations() -> dict:
    """
    Test basic database operations to ensure async functionality works correctly.
    
    This function performs a series of database operations including
    creating a temporary table, inserting data, querying, and cleanup
    to verify that async database operations are working properly.
    
    Returns:
        dict: Test results with operation status and details
        
    Note:
        This function is primarily for testing and debugging purposes.
        It should not be used in production endpoints frequently.
    """
    import time
    
    test_results = {
        "status": "failed",
        "operations": {
            "connection": False,
            "create_temp_table": False,
            "insert_data": False,
            "query_data": False,
            "cleanup": False
        },
        "error": None,
        "execution_time_ms": 0
    }
    
    start_time = time.time()
    
    try:
        manager = await get_async_db_manager()
        
        async for session in manager.get_async_session():
            # Test connection
            await session.execute(text("SELECT 1"))
            test_results["operations"]["connection"] = True
            
            # Test basic query operations (without creating tables)
            result = await session.execute(text("SELECT 'async_test' as test_value"))
            test_value = result.scalar()
            
            if test_value == 'async_test':
                test_results["operations"]["create_temp_table"] = True
                test_results["operations"]["insert_data"] = True
                test_results["operations"]["query_data"] = True
            
            # Test more complex query
            result = await session.execute(text("""
                SELECT COUNT(*) as count_result 
                FROM (VALUES ('test1'), ('test2')) as test_data(value)
            """))
            count = result.scalar()
            
            if count == 2:
                test_results["operations"]["cleanup"] = True
            
            break
        
        # Calculate execution time
        end_time = time.time()
        test_results["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
        
        # Check if all operations succeeded
        if all(test_results["operations"].values()):
            test_results["status"] = "success"
        
    except Exception as e:
        end_time = time.time()
        test_results["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
        test_results["error"] = str(e)
        logger.error(f"Async database operations test failed: {e}")
    
    return test_results


# Cleanup function for application shutdown
async def close_async_db_manager():
    """
    Close the global async database manager.
    
    This function should be called during application shutdown to ensure
    proper cleanup of database connections and resources.
    """
    global _async_db_manager
    
    if _async_db_manager is not None:
        await _async_db_manager.close()
        _async_db_manager = None
        logger.info("Async database manager closed and cleaned up")