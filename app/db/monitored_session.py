"""
Enhanced async database session with integrated monitoring and error tracking.
"""

import asyncio
import logging
import time
import hashlib
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Any, Dict
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.db.async_session import get_async_db_manager

logger = logging.getLogger(__name__)

class MonitoredAsyncSession:
    """
    Wrapper for AsyncSession that provides automatic monitoring and error tracking.
    
    This class wraps the standard AsyncSession to automatically collect:
    - Query execution metrics
    - Error tracking and classification
    - Connection pool utilization
    - Performance monitoring
    """
    
    def __init__(self, session: AsyncSession, session_id: Optional[str] = None):
        self._session = session
        self.session_id = session_id or f"session_{int(time.time() * 1000)}"
        self.created_at = datetime.now(timezone.utc)
        self.query_count = 0
        self.total_execution_time = 0.0
        self.error_count = 0
        
        # Import here to avoid circular imports
        try:
            from app.services.async_metrics import get_metrics_collector
            from app.services.async_error_tracking import get_error_tracker
            self._metrics_collector = get_metrics_collector()
            self._error_tracker = get_error_tracker()
        except ImportError:
            logger.warning("Metrics collector or error tracker not available")
            self._metrics_collector = None
            self._error_tracker = None
    
    async def execute(self, statement, parameters=None, execution_options=None, bind_arguments=None, _parent_execute_state=None, _add_event=None):
        """Execute a statement with monitoring."""
        start_time = time.time()
        success = False
        error_message = None
        rows_affected = None
        
        # Extract query information
        query_str = str(statement)
        query_type = self._extract_query_type(query_str)
        table_name = self._extract_table_name(query_str, query_type)
        query_hash = self._generate_query_hash(query_str, parameters)
        
        try:
            # Call the session execute method with correct signature
            if parameters is not None:
                result = await self._session.execute(statement, parameters)
            else:
                result = await self._session.execute(statement)
            success = True
            
            # Try to get rows affected
            if hasattr(result, 'rowcount'):
                rows_affected = result.rowcount
            
            return result
            
        except Exception as e:
            error_message = str(e)
            self.error_count += 1
            
            # Track the error
            if self._error_tracker:
                self._error_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=error_message,
                    query_type=query_type,
                    table_name=table_name,
                    execution_time=time.time() - start_time,
                    connection_id=self.session_id,
                    context={
                        "query_hash": query_hash,
                        "parameters": str(parameters) if parameters else None
                    }
                )
            
            raise
            
        finally:
            execution_time = time.time() - start_time
            self.query_count += 1
            self.total_execution_time += execution_time
            
            # Record metrics
            if self._metrics_collector:
                self._metrics_collector.record_query(
                    query_hash=query_hash,
                    query_type=query_type,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    rows_affected=rows_affected,
                    table_name=table_name
                )
                
                # Record connection event
                self._metrics_collector.record_connection_event(
                    connection_id=self.session_id,
                    event_type="used",
                    execution_time=execution_time,
                    error=not success
                )
    
    async def commit(self):
        """Commit the transaction with monitoring."""
        start_time = time.time()
        try:
            await self._session.commit()
            
            if self._metrics_collector:
                self._metrics_collector.record_query(
                    query_hash="commit_transaction",
                    query_type="COMMIT",
                    execution_time=time.time() - start_time,
                    success=True
                )
        except Exception as e:
            if self._error_tracker:
                self._error_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    query_type="COMMIT",
                    connection_id=self.session_id
                )
            raise
    
    async def rollback(self):
        """Rollback the transaction with monitoring."""
        start_time = time.time()
        try:
            await self._session.rollback()
            
            if self._metrics_collector:
                self._metrics_collector.record_query(
                    query_hash="rollback_transaction",
                    query_type="ROLLBACK",
                    execution_time=time.time() - start_time,
                    success=True
                )
        except Exception as e:
            if self._error_tracker:
                self._error_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    query_type="ROLLBACK",
                    connection_id=self.session_id
                )
            raise
    
    async def close(self):
        """Close the session with monitoring."""
        try:
            await self._session.close()
            
            # Record connection close event
            if self._metrics_collector:
                self._metrics_collector.record_connection_event(
                    connection_id=self.session_id,
                    event_type="closed"
                )
        except Exception as e:
            if self._error_tracker:
                self._error_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    query_type="CLOSE_SESSION",
                    connection_id=self.session_id
                )
            raise
    
    def _extract_query_type(self, query_str: str) -> str:
        """Extract the query type from SQL statement."""
        query_str = query_str.strip().upper()
        
        if query_str.startswith('SELECT'):
            return 'SELECT'
        elif query_str.startswith('INSERT'):
            return 'INSERT'
        elif query_str.startswith('UPDATE'):
            return 'UPDATE'
        elif query_str.startswith('DELETE'):
            return 'DELETE'
        elif query_str.startswith('CREATE'):
            return 'CREATE'
        elif query_str.startswith('DROP'):
            return 'DROP'
        elif query_str.startswith('ALTER'):
            return 'ALTER'
        elif query_str.startswith('BEGIN'):
            return 'BEGIN'
        elif query_str.startswith('COMMIT'):
            return 'COMMIT'
        elif query_str.startswith('ROLLBACK'):
            return 'ROLLBACK'
        else:
            return 'OTHER'
    
    def _extract_table_name(self, query_str: str, query_type: str) -> Optional[str]:
        """Extract table name from SQL statement."""
        try:
            query_str = query_str.upper()
            
            if query_type == 'SELECT':
                # Look for FROM clause
                if ' FROM ' in query_str:
                    parts = query_str.split(' FROM ')[1].split()
                    if parts:
                        return parts[0].strip('`"[]')
            elif query_type in ['INSERT', 'UPDATE', 'DELETE']:
                # Look for table name after INSERT INTO, UPDATE, or DELETE FROM
                if query_type == 'INSERT' and ' INTO ' in query_str:
                    parts = query_str.split(' INTO ')[1].split()
                elif query_type == 'UPDATE':
                    parts = query_str.split('UPDATE ')[1].split()
                elif query_type == 'DELETE' and ' FROM ' in query_str:
                    parts = query_str.split(' FROM ')[1].split()
                else:
                    return None
                
                if parts:
                    return parts[0].strip('`"[]')
            
            return None
        except Exception:
            return None
    
    def _generate_query_hash(self, query_str: str, parameters: Any) -> str:
        """Generate a hash for the query for tracking purposes."""
        # Normalize the query string
        normalized_query = ' '.join(query_str.split())
        
        # Include parameters in hash if present
        param_str = str(parameters) if parameters else ""
        
        # Create hash
        hash_input = f"{normalized_query}_{param_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for this session."""
        session_duration = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "session_duration_seconds": session_duration,
            "query_count": self.query_count,
            "error_count": self.error_count,
            "total_execution_time": self.total_execution_time,
            "avg_query_time": self.total_execution_time / max(self.query_count, 1),
            "success_rate": (self.query_count - self.error_count) / max(self.query_count, 1)
        }
    
    # Delegate other methods to the underlying session
    def __getattr__(self, name):
        return getattr(self._session, name)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self.close()

@asynccontextmanager
async def get_monitored_async_db() -> AsyncGenerator[MonitoredAsyncSession, None]:
    """
    Get a monitored async database session with comprehensive tracking.
    
    This function provides an enhanced database session that automatically
    tracks metrics, errors, and performance data.
    
    Yields:
        MonitoredAsyncSession: Enhanced database session with monitoring
    """
    manager = await get_async_db_manager()
    session_id = f"monitored_{int(time.time() * 1000)}"
    
    # Record connection creation
    try:
        from app.services.async_metrics import get_metrics_collector
        metrics_collector = get_metrics_collector()
        metrics_collector.record_connection_event(session_id, "created")
    except ImportError:
        pass
    
    # Use the manager's context manager properly
    async with manager.get_monitored_session() as session:
        monitored_session = MonitoredAsyncSession(session, session_id)
        try:
            yield monitored_session
        except SQLAlchemyError as e:
            await monitored_session.rollback()
            logger.error(f"Database error in monitored session {session_id}: {e}")
            raise
        except Exception as e:
            await monitored_session.rollback()
            logger.error(f"Unexpected error in monitored session {session_id}: {e}")
            raise

# Enhanced dependency injection function for FastAPI
async def get_monitored_async_db_dependency() -> AsyncGenerator[MonitoredAsyncSession, None]:
    """
    FastAPI dependency for monitored async database session injection.
    
    This provides the same interface as get_async_db but with enhanced
    monitoring and error tracking capabilities.
    
    Yields:
        MonitoredAsyncSession: Enhanced database session with monitoring
    """
    async with get_monitored_async_db() as session:
        yield session

# Decorator for automatic database operation monitoring
def monitor_db_operation(operation_name: str = "db_operation"):
    """
    Decorator to automatically monitor database operations.
    
    Args:
        operation_name: Name of the operation for tracking purposes
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_message = None
            
            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_message = str(e)
                
                # Track the error
                try:
                    from app.services.async_error_tracking import get_error_tracker
                    error_tracker = get_error_tracker()
                    error_tracker.track_error(
                        error_type=type(e).__name__,
                        error_message=error_message,
                        context={
                            "operation": operation_name,
                            "function": func.__name__,
                            "execution_time": time.time() - start_time
                        }
                    )
                except ImportError:
                    pass
                
                raise
            finally:
                execution_time = time.time() - start_time
                
                # Record performance metrics
                try:
                    from app.services.async_metrics import get_metrics_collector
                    metrics_collector = get_metrics_collector()
                    
                    if execution_time > 1.0:  # Track slow operations
                        metrics_collector.record_query(
                            query_hash=f"{operation_name}_{func.__name__}",
                            query_type="OPERATION",
                            execution_time=execution_time,
                            success=success,
                            error_message=error_message
                        )
                except ImportError:
                    pass
        
        return wrapper
    return decorator