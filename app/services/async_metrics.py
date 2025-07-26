"""
Enhanced async database metrics collection and performance tracking.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json
import statistics

from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Metrics for individual database queries."""
    query_hash: str
    query_type: str  # SELECT, INSERT, UPDATE, DELETE, etc.
    execution_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    rows_affected: Optional[int] = None
    table_name: Optional[str] = None

@dataclass
class ConnectionMetrics:
    """Metrics for database connections."""
    connection_id: str
    created_at: datetime
    last_used: datetime
    total_queries: int = 0
    total_execution_time: float = 0.0
    errors: int = 0
    is_active: bool = True

class AsyncDatabaseMetricsCollector:
    """
    Advanced metrics collector for async database operations.
    
    Collects detailed performance metrics including:
    - Query execution times and patterns
    - Connection pool utilization over time
    - Error rates and types
    - Performance trends and anomalies
    """
    
    def __init__(self, max_query_history: int = 1000, max_connection_history: int = 100):
        self.max_query_history = max_query_history
        self.max_connection_history = max_connection_history
        
        # Query metrics storage
        self.query_history: deque = deque(maxlen=max_query_history)
        self.query_stats_by_type: Dict[str, List[float]] = defaultdict(list)
        self.slow_queries: deque = deque(maxlen=100)  # Keep last 100 slow queries
        self.slow_query_threshold = 1.0  # 1 second threshold
        
        # Connection metrics
        self.connection_history: deque = deque(maxlen=max_connection_history)
        self.active_connections: Dict[str, ConnectionMetrics] = {}
        
        # Pool utilization tracking
        self.pool_utilization_history: deque = deque(maxlen=288)  # 24 hours at 5-minute intervals
        self.pool_utilization_timestamps: deque = deque(maxlen=288)
        
        # Error tracking
        self.error_history: deque = deque(maxlen=500)
        self.error_counts_by_type: Dict[str, int] = defaultdict(int)
        
        # Performance alerts
        self.alert_thresholds = {
            "slow_query_threshold": 1.0,  # seconds
            "high_error_rate_threshold": 0.05,  # 5% error rate
            "high_pool_utilization_threshold": 0.8,  # 80% pool utilization
            "connection_timeout_threshold": 30.0,  # seconds
        }
        
        # Metrics aggregation
        self.last_aggregation = datetime.now(timezone.utc)
        self.aggregated_metrics: Dict[str, Any] = {}
        
    def record_query(self, query_hash: str, query_type: str, execution_time: float, 
                    success: bool, error_message: Optional[str] = None,
                    rows_affected: Optional[int] = None, table_name: Optional[str] = None):
        """Record metrics for a database query."""
        timestamp = datetime.now(timezone.utc)
        
        query_metric = QueryMetrics(
            query_hash=query_hash,
            query_type=query_type,
            execution_time=execution_time,
            timestamp=timestamp,
            success=success,
            error_message=error_message,
            rows_affected=rows_affected,
            table_name=table_name
        )
        
        self.query_history.append(query_metric)
        
        # Track by query type
        self.query_stats_by_type[query_type].append(execution_time)
        
        # Track slow queries
        if execution_time > self.slow_query_threshold:
            self.slow_queries.append(query_metric)
            logger.warning(f"Slow query detected: {query_type} took {execution_time:.3f}s")
        
        # Track errors
        if not success and error_message:
            self.error_history.append({
                "timestamp": timestamp,
                "query_type": query_type,
                "error_message": error_message,
                "execution_time": execution_time,
                "table_name": table_name
            })
            self.error_counts_by_type[query_type] += 1
    
    def record_connection_event(self, connection_id: str, event_type: str, **kwargs):
        """Record connection-related events."""
        timestamp = datetime.now(timezone.utc)
        
        if event_type == "created":
            self.active_connections[connection_id] = ConnectionMetrics(
                connection_id=connection_id,
                created_at=timestamp,
                last_used=timestamp
            )
        elif event_type == "used" and connection_id in self.active_connections:
            conn = self.active_connections[connection_id]
            conn.last_used = timestamp
            conn.total_queries += 1
            conn.total_execution_time += kwargs.get("execution_time", 0.0)
            if kwargs.get("error", False):
                conn.errors += 1
        elif event_type == "closed" and connection_id in self.active_connections:
            conn = self.active_connections[connection_id]
            conn.is_active = False
            self.connection_history.append(conn)
            del self.active_connections[connection_id]
    
    def record_pool_utilization(self, pool_size: int, checked_out: int, overflow: int):
        """Record connection pool utilization metrics."""
        timestamp = datetime.now(timezone.utc)
        total_capacity = pool_size + overflow
        utilization = checked_out / total_capacity if total_capacity > 0 else 0
        
        self.pool_utilization_history.append(utilization)
        self.pool_utilization_timestamps.append(timestamp)
        
        # Alert on high utilization
        if utilization > self.alert_thresholds["high_pool_utilization_threshold"]:
            logger.warning(f"High pool utilization: {utilization:.2%} ({checked_out}/{total_capacity})")
    
    def get_query_performance_stats(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get query performance statistics for a time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        recent_queries = [q for q in self.query_history if q.timestamp >= cutoff_time]
        
        if not recent_queries:
            return {"message": "No queries in time window", "time_window_minutes": time_window_minutes}
        
        # Calculate statistics by query type
        stats_by_type = {}
        for query_type in set(q.query_type for q in recent_queries):
            type_queries = [q for q in recent_queries if q.query_type == query_type]
            execution_times = [q.execution_time for q in type_queries]
            
            stats_by_type[query_type] = {
                "count": len(type_queries),
                "avg_execution_time": statistics.mean(execution_times),
                "median_execution_time": statistics.median(execution_times),
                "max_execution_time": max(execution_times),
                "min_execution_time": min(execution_times),
                "success_rate": sum(1 for q in type_queries if q.success) / len(type_queries),
                "total_execution_time": sum(execution_times)
            }
        
        # Overall statistics
        all_execution_times = [q.execution_time for q in recent_queries]
        total_queries = len(recent_queries)
        successful_queries = sum(1 for q in recent_queries if q.success)
        
        return {
            "time_window_minutes": time_window_minutes,
            "total_queries": total_queries,
            "successful_queries": successful_queries,
            "error_rate": (total_queries - successful_queries) / total_queries if total_queries > 0 else 0,
            "avg_execution_time": statistics.mean(all_execution_times),
            "median_execution_time": statistics.median(all_execution_times),
            "95th_percentile": statistics.quantiles(all_execution_times, n=20)[18] if len(all_execution_times) >= 20 else max(all_execution_times),
            "queries_per_minute": total_queries / time_window_minutes,
            "stats_by_type": stats_by_type,
            "slow_queries_count": len([q for q in recent_queries if q.execution_time > self.slow_query_threshold])
        }
    
    def get_connection_pool_trends(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get connection pool utilization trends."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        
        # Filter utilization data by time window
        recent_data = []
        recent_timestamps = []
        
        for i, timestamp in enumerate(self.pool_utilization_timestamps):
            if timestamp >= cutoff_time and i < len(self.pool_utilization_history):
                recent_data.append(self.pool_utilization_history[i])
                recent_timestamps.append(timestamp)
        
        if not recent_data:
            return {"message": "No pool utilization data in time window"}
        
        return {
            "time_window_minutes": time_window_minutes,
            "data_points": len(recent_data),
            "avg_utilization": statistics.mean(recent_data),
            "max_utilization": max(recent_data),
            "min_utilization": min(recent_data),
            "current_utilization": recent_data[-1] if recent_data else 0,
            "utilization_trend": self._calculate_trend(recent_data),
            "high_utilization_periods": len([u for u in recent_data if u > self.alert_thresholds["high_pool_utilization_threshold"]]),
            "utilization_history": [
                {"timestamp": ts.isoformat(), "utilization": util}
                for ts, util in zip(recent_timestamps[-20:], recent_data[-20:])  # Last 20 data points
            ]
        }
    
    def get_error_analysis(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get detailed error analysis."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        recent_errors = [e for e in self.error_history if e["timestamp"] >= cutoff_time]
        
        if not recent_errors:
            return {"message": "No errors in time window", "time_window_minutes": time_window_minutes}
        
        # Group errors by type and message
        errors_by_type = defaultdict(list)
        errors_by_message = defaultdict(int)
        
        for error in recent_errors:
            errors_by_type[error["query_type"]].append(error)
            errors_by_message[error["error_message"]] += 1
        
        return {
            "time_window_minutes": time_window_minutes,
            "total_errors": len(recent_errors),
            "errors_per_minute": len(recent_errors) / time_window_minutes,
            "errors_by_type": {
                query_type: {
                    "count": len(errors),
                    "avg_execution_time": statistics.mean([e["execution_time"] for e in errors]),
                    "most_common_error": max(set(e["error_message"] for e in errors), 
                                           key=lambda x: sum(1 for e in errors if e["error_message"] == x))
                }
                for query_type, errors in errors_by_type.items()
            },
            "most_common_errors": dict(sorted(errors_by_message.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_errors": [
                {
                    "timestamp": e["timestamp"].isoformat(),
                    "query_type": e["query_type"],
                    "error_message": e["error_message"][:200],  # Truncate long messages
                    "execution_time": e["execution_time"]
                }
                for e in recent_errors[-10:]  # Last 10 errors
            ]
        }
    
    def get_slow_query_analysis(self) -> Dict[str, Any]:
        """Get analysis of slow queries."""
        if not self.slow_queries:
            return {"message": "No slow queries recorded"}
        
        slow_queries_list = list(self.slow_queries)
        
        # Group by query type
        by_type = defaultdict(list)
        for query in slow_queries_list:
            by_type[query.query_type].append(query)
        
        return {
            "total_slow_queries": len(slow_queries_list),
            "slow_query_threshold": self.slow_query_threshold,
            "slowest_query": {
                "execution_time": max(q.execution_time for q in slow_queries_list),
                "query_type": max(slow_queries_list, key=lambda q: q.execution_time).query_type,
                "timestamp": max(slow_queries_list, key=lambda q: q.execution_time).timestamp.isoformat()
            },
            "by_type": {
                query_type: {
                    "count": len(queries),
                    "avg_execution_time": statistics.mean([q.execution_time for q in queries]),
                    "max_execution_time": max(q.execution_time for q in queries)
                }
                for query_type, queries in by_type.items()
            },
            "recent_slow_queries": [
                {
                    "query_type": q.query_type,
                    "execution_time": q.execution_time,
                    "timestamp": q.timestamp.isoformat(),
                    "table_name": q.table_name,
                    "success": q.success
                }
                for q in slow_queries_list[-10:]  # Last 10 slow queries
            ]
        }
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "query_performance": self.get_query_performance_stats(60),
            "pool_trends": self.get_connection_pool_trends(60),
            "error_analysis": self.get_error_analysis(60),
            "slow_query_analysis": self.get_slow_query_analysis(),
            "active_connections": len(self.active_connections),
            "total_connection_history": len(self.connection_history),
            "metrics_collection_status": {
                "query_history_size": len(self.query_history),
                "error_history_size": len(self.error_history),
                "pool_utilization_data_points": len(self.pool_utilization_history),
                "last_aggregation": self.last_aggregation.isoformat()
            }
        }
    
    def _calculate_trend(self, data: List[float]) -> str:
        """Calculate trend direction for a series of data points."""
        if len(data) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        x = list(range(len(data)))
        n = len(data)
        sum_x = sum(x)
        sum_y = sum(data)
        sum_xy = sum(x[i] * data[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    
    def reset_metrics(self):
        """Reset all collected metrics."""
        self.query_history.clear()
        self.query_stats_by_type.clear()
        self.slow_queries.clear()
        self.connection_history.clear()
        self.active_connections.clear()
        self.pool_utilization_history.clear()
        self.pool_utilization_timestamps.clear()
        self.error_history.clear()
        self.error_counts_by_type.clear()
        self.last_aggregation = datetime.now(timezone.utc)
        logger.info("All database metrics have been reset")

# Global metrics collector instance
_metrics_collector: Optional[AsyncDatabaseMetricsCollector] = None

def get_metrics_collector() -> AsyncDatabaseMetricsCollector:
    """Get or create the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AsyncDatabaseMetricsCollector()
    return _metrics_collector

# Decorator for automatic query metrics collection
def track_query_metrics(query_type: str = "UNKNOWN", table_name: Optional[str] = None):
    """Decorator to automatically track query execution metrics."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            error_message = None
            rows_affected = None
            
            try:
                result = await func(*args, **kwargs)
                success = True
                
                # Try to extract rows affected from result
                if hasattr(result, 'rowcount'):
                    rows_affected = result.rowcount
                
                return result
            except Exception as e:
                error_message = str(e)
                raise
            finally:
                execution_time = time.time() - start_time
                query_hash = f"{func.__name__}_{hash(str(args) + str(kwargs)) % 10000}"
                
                collector = get_metrics_collector()
                collector.record_query(
                    query_hash=query_hash,
                    query_type=query_type,
                    execution_time=execution_time,
                    success=success,
                    error_message=error_message,
                    rows_affected=rows_affected,
                    table_name=table_name
                )
        
        return wrapper
    return decorator