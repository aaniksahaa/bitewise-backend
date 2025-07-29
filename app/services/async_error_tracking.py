"""
Advanced async database error tracking and alerting system.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of database alerts."""
    CONNECTION_FAILURE = "connection_failure"
    POOL_EXHAUSTION = "pool_exhaustion"
    SLOW_QUERY = "slow_query"
    HIGH_ERROR_RATE = "high_error_rate"
    TRANSACTION_TIMEOUT = "transaction_timeout"
    DEADLOCK = "deadlock"
    DISK_SPACE = "disk_space"
    PERFORMANCE_DEGRADATION = "performance_degradation"

@dataclass
class DatabaseError:
    """Represents a database error with context."""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    query_type: Optional[str] = None
    table_name: Optional[str] = None
    execution_time: Optional[float] = None
    connection_id: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    """Represents a system alert."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class AsyncErrorTracker:
    """
    Advanced error tracking system for async database operations.
    
    Features:
    - Real-time error detection and classification
    - Pattern recognition for recurring issues
    - Automatic alert generation based on thresholds
    - Error trend analysis and reporting
    """
    
    def __init__(self, max_error_history: int = 1000, max_alert_history: int = 500):
        self.max_error_history = max_error_history
        self.max_alert_history = max_alert_history
        
        # Error storage
        self.error_history: deque = deque(maxlen=max_error_history)
        self.error_patterns: Dict[str, List[DatabaseError]] = defaultdict(list)
        self.error_counts_by_type: Dict[str, int] = defaultdict(int)
        
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=max_alert_history)
        self.alert_cooldowns: Dict[str, datetime] = {}  # Prevent alert spam
        
        # Error rate tracking
        self.error_rate_windows: Dict[int, deque] = {
            5: deque(maxlen=300),    # 5-minute window (5-second intervals)
            15: deque(maxlen=180),   # 15-minute window (5-second intervals)
            60: deque(maxlen=720),   # 1-hour window (5-second intervals)
        }
        self.error_rate_timestamps: Dict[int, deque] = {
            5: deque(maxlen=300),
            15: deque(maxlen=180),
            60: deque(maxlen=720),
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "error_rate_5min": 0.1,      # 10% error rate in 5 minutes
            "error_rate_15min": 0.05,    # 5% error rate in 15 minutes
            "error_rate_1hour": 0.02,    # 2% error rate in 1 hour
            "slow_query_threshold": 2.0,  # 2 seconds
            "connection_timeout": 30.0,   # 30 seconds
            "pool_utilization": 0.9,      # 90% pool utilization
            "consecutive_failures": 5,    # 5 consecutive failures
        }
        
        # Alert cooldown periods (in seconds)
        self.alert_cooldowns_config = {
            AlertType.CONNECTION_FAILURE: 300,      # 5 minutes
            AlertType.POOL_EXHAUSTION: 600,         # 10 minutes
            AlertType.SLOW_QUERY: 900,              # 15 minutes
            AlertType.HIGH_ERROR_RATE: 300,         # 5 minutes
            AlertType.TRANSACTION_TIMEOUT: 300,     # 5 minutes
            AlertType.DEADLOCK: 180,                # 3 minutes
            AlertType.PERFORMANCE_DEGRADATION: 1800, # 30 minutes
        }
        
        # Notification handlers
        self.notification_handlers: List[Callable] = []
        
    def track_error(self, error_type: str, error_message: str, **kwargs) -> str:
        """
        Track a database error with full context.
        
        Args:
            error_type: Type of error (e.g., 'ConnectionError', 'QueryTimeout')
            error_message: Detailed error message
            **kwargs: Additional context (query_type, table_name, etc.)
            
        Returns:
            str: Unique error ID for tracking
        """
        timestamp = datetime.now(timezone.utc)
        error_id = f"{error_type}_{timestamp.timestamp()}_{hash(error_message) % 10000}"
        
        error = DatabaseError(
            error_id=error_id,
            timestamp=timestamp,
            error_type=error_type,
            error_message=error_message,
            query_type=kwargs.get('query_type'),
            table_name=kwargs.get('table_name'),
            execution_time=kwargs.get('execution_time'),
            connection_id=kwargs.get('connection_id'),
            stack_trace=kwargs.get('stack_trace'),
            context=kwargs.get('context', {})
        )
        
        # Store error
        self.error_history.append(error)
        self.error_patterns[error_type].append(error)
        self.error_counts_by_type[error_type] += 1
        
        # Update error rate tracking
        self._update_error_rates(timestamp)
        
        # Check for alert conditions
        asyncio.create_task(self._check_alert_conditions(error))
        
        logger.error(f"Database error tracked: {error_type} - {error_message}")
        return error_id
    
    def track_performance_issue(self, operation: str, execution_time: float, **kwargs):
        """Track performance-related issues."""
        if execution_time > self.alert_thresholds["slow_query_threshold"]:
            self.track_error(
                error_type="SlowQuery",
                error_message=f"{operation} took {execution_time:.3f}s (threshold: {self.alert_thresholds['slow_query_threshold']}s)",
                execution_time=execution_time,
                **kwargs
            )
    
    def track_connection_issue(self, issue_type: str, details: str, **kwargs):
        """Track connection-related issues."""
        error_types = {
            "timeout": "ConnectionTimeout",
            "pool_exhausted": "PoolExhaustion",
            "connection_failed": "ConnectionFailure",
            "connection_lost": "ConnectionLost"
        }
        
        error_type = error_types.get(issue_type, "ConnectionIssue")
        self.track_error(
            error_type=error_type,
            error_message=details,
            **kwargs
        )
    
    async def _check_alert_conditions(self, error: DatabaseError):
        """Check if the error triggers any alert conditions."""
        alerts_to_create = []
        
        # Check for high error rates
        for window_minutes in [5, 15, 60]:
            error_rate = self._calculate_error_rate(window_minutes)
            threshold_key = f"error_rate_{window_minutes}min"
            
            if error_rate > self.alert_thresholds.get(threshold_key, 1.0):
                alerts_to_create.append(self._create_error_rate_alert(window_minutes, error_rate))
        
        # Check for specific error patterns
        if error.error_type == "ConnectionFailure":
            alerts_to_create.append(self._create_connection_failure_alert(error))
        elif error.error_type == "PoolExhaustion":
            alerts_to_create.append(self._create_pool_exhaustion_alert(error))
        elif error.error_type == "SlowQuery":
            alerts_to_create.append(self._create_slow_query_alert(error))
        elif "deadlock" in error.error_message.lower():
            alerts_to_create.append(self._create_deadlock_alert(error))
        
        # Check for consecutive failures
        recent_errors = [e for e in list(self.error_history)[-10:] if e.error_type == error.error_type]
        if len(recent_errors) >= self.alert_thresholds["consecutive_failures"]:
            alerts_to_create.append(self._create_consecutive_failure_alert(error, len(recent_errors)))
        
        # Create and process alerts
        for alert in alerts_to_create:
            if alert:
                await self._process_alert(alert)
    
    def _create_error_rate_alert(self, window_minutes: int, error_rate: float) -> Optional[Alert]:
        """Create an alert for high error rate."""
        alert_key = f"high_error_rate_{window_minutes}min"
        
        if self._is_alert_in_cooldown(alert_key):
            return None
        
        return Alert(
            alert_id=f"error_rate_{window_minutes}_{datetime.now(timezone.utc).timestamp()}",
            alert_type=AlertType.HIGH_ERROR_RATE,
            severity=AlertSeverity.HIGH if error_rate > 0.1 else AlertSeverity.MEDIUM,
            title=f"High Error Rate Detected ({window_minutes} min window)",
            message=f"Database error rate is {error_rate:.2%} over the last {window_minutes} minutes, "
                   f"exceeding threshold of {self.alert_thresholds.get(f'error_rate_{window_minutes}min', 0):.2%}",
            timestamp=datetime.now(timezone.utc),
            metadata={"window_minutes": window_minutes, "error_rate": error_rate}
        )
    
    def _create_connection_failure_alert(self, error: DatabaseError) -> Alert:
        """Create an alert for connection failures."""
        return Alert(
            alert_id=f"conn_failure_{error.error_id}",
            alert_type=AlertType.CONNECTION_FAILURE,
            severity=AlertSeverity.CRITICAL,
            title="Database Connection Failure",
            message=f"Database connection failed: {error.error_message}",
            timestamp=error.timestamp,
            metadata={"error_id": error.error_id, "connection_id": error.connection_id}
        )
    
    def _create_pool_exhaustion_alert(self, error: DatabaseError) -> Alert:
        """Create an alert for connection pool exhaustion."""
        return Alert(
            alert_id=f"pool_exhausted_{error.error_id}",
            alert_type=AlertType.POOL_EXHAUSTION,
            severity=AlertSeverity.HIGH,
            title="Connection Pool Exhausted",
            message=f"Database connection pool is exhausted: {error.error_message}",
            timestamp=error.timestamp,
            metadata={"error_id": error.error_id}
        )
    
    def _create_slow_query_alert(self, error: DatabaseError) -> Optional[Alert]:
        """Create an alert for slow queries."""
        alert_key = "slow_query"
        
        if self._is_alert_in_cooldown(alert_key):
            return None
        
        return Alert(
            alert_id=f"slow_query_{error.error_id}",
            alert_type=AlertType.SLOW_QUERY,
            severity=AlertSeverity.MEDIUM,
            title="Slow Query Detected",
            message=f"Slow database query detected: {error.error_message}",
            timestamp=error.timestamp,
            metadata={
                "error_id": error.error_id,
                "execution_time": error.execution_time,
                "query_type": error.query_type,
                "table_name": error.table_name
            }
        )
    
    def _create_deadlock_alert(self, error: DatabaseError) -> Alert:
        """Create an alert for database deadlocks."""
        return Alert(
            alert_id=f"deadlock_{error.error_id}",
            alert_type=AlertType.DEADLOCK,
            severity=AlertSeverity.HIGH,
            title="Database Deadlock Detected",
            message=f"Database deadlock occurred: {error.error_message}",
            timestamp=error.timestamp,
            metadata={"error_id": error.error_id, "table_name": error.table_name}
        )
    
    def _create_consecutive_failure_alert(self, error: DatabaseError, failure_count: int) -> Alert:
        """Create an alert for consecutive failures."""
        return Alert(
            alert_id=f"consecutive_failures_{error.error_type}_{datetime.now(timezone.utc).timestamp()}",
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            severity=AlertSeverity.HIGH,
            title=f"Consecutive {error.error_type} Failures",
            message=f"Detected {failure_count} consecutive {error.error_type} failures",
            timestamp=error.timestamp,
            metadata={"error_type": error.error_type, "failure_count": failure_count}
        )
    
    async def _process_alert(self, alert: Alert):
        """Process and handle an alert."""
        # Store alert
        self.active_alerts[alert.alert_id] = alert
        self.alert_history.append(alert)
        
        # Set cooldown
        cooldown_key = f"{alert.alert_type.value}_{alert.metadata.get('window_minutes', '')}"
        cooldown_duration = self.alert_cooldowns_config.get(alert.alert_type, 300)
        self.alert_cooldowns[cooldown_key] = datetime.now(timezone.utc) + timedelta(seconds=cooldown_duration)
        
        # Log alert
        logger.warning(f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message}")
        
        # Send notifications
        await self._send_notifications(alert)
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications through configured channels."""
        for handler in self.notification_handlers:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"Failed to send alert notification: {e}")
    
    def _is_alert_in_cooldown(self, alert_key: str) -> bool:
        """Check if an alert type is in cooldown period."""
        if alert_key not in self.alert_cooldowns:
            return False
        
        return datetime.now(timezone.utc) < self.alert_cooldowns[alert_key]
    
    def _update_error_rates(self, timestamp: datetime):
        """Update error rate tracking windows."""
        for window_minutes in self.error_rate_windows.keys():
            self.error_rate_windows[window_minutes].append(1)  # Error occurred
            self.error_rate_timestamps[window_minutes].append(timestamp)
    
    def _calculate_error_rate(self, window_minutes: int) -> float:
        """Calculate error rate for a given time window."""
        if window_minutes not in self.error_rate_windows:
            return 0.0
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # Count errors in time window
        error_count = 0
        total_operations = 0
        
        timestamps = list(self.error_rate_timestamps[window_minutes])
        for i, timestamp in enumerate(timestamps):
            if timestamp >= cutoff_time:
                error_count += self.error_rate_windows[window_minutes][i]
                total_operations += 1  # Simplified - in real implementation, track total operations
        
        return error_count / max(total_operations, 1)
    
    def resolve_alert(self, alert_id: str, resolution_note: str = "") -> bool:
        """Mark an alert as resolved."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            alert.metadata["resolution_note"] = resolution_note
            
            del self.active_alerts[alert_id]
            logger.info(f"Alert resolved: {alert_id} - {resolution_note}")
            return True
        
        return False
    
    def get_error_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive error summary for a time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        if not recent_errors:
            return {"message": "No errors in time window", "time_window_minutes": time_window_minutes}
        
        # Group errors by type
        errors_by_type = defaultdict(list)
        for error in recent_errors:
            errors_by_type[error.error_type].append(error)
        
        # Calculate error patterns
        error_patterns = {}
        for error_type, errors in errors_by_type.items():
            error_patterns[error_type] = {
                "count": len(errors),
                "first_occurrence": min(e.timestamp for e in errors).isoformat(),
                "last_occurrence": max(e.timestamp for e in errors).isoformat(),
                "avg_execution_time": sum(e.execution_time for e in errors if e.execution_time) / len([e for e in errors if e.execution_time]) if any(e.execution_time for e in errors) else None,
                "affected_tables": list(set(e.table_name for e in errors if e.table_name)),
                "most_common_message": max(set(e.error_message for e in errors), key=lambda x: sum(1 for e in errors if e.error_message == x))
            }
        
        return {
            "time_window_minutes": time_window_minutes,
            "total_errors": len(recent_errors),
            "unique_error_types": len(errors_by_type),
            "error_rate": len(recent_errors) / time_window_minutes,
            "error_patterns": error_patterns,
            "active_alerts": len(self.active_alerts),
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "timestamp": e.timestamp.isoformat(),
                    "error_type": e.error_type,
                    "error_message": e.error_message[:200],  # Truncate long messages
                    "query_type": e.query_type,
                    "table_name": e.table_name,
                    "execution_time": e.execution_time
                }
                for e in recent_errors[-10:]  # Last 10 errors
            ]
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "metadata": alert.metadata
            }
            for alert in self.active_alerts.values()
        ]
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alert history."""
        alerts = list(self.alert_history)[-limit:]
        return [
            {
                "alert_id": alert.alert_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "metadata": alert.metadata
            }
            for alert in alerts
        ]
    
    def add_notification_handler(self, handler: Callable):
        """Add a notification handler for alerts."""
        self.notification_handlers.append(handler)
    
    def reset_error_tracking(self):
        """Reset all error tracking data."""
        self.error_history.clear()
        self.error_patterns.clear()
        self.error_counts_by_type.clear()
        self.active_alerts.clear()
        self.alert_history.clear()
        self.alert_cooldowns.clear()
        
        for window in self.error_rate_windows.values():
            window.clear()
        for timestamps in self.error_rate_timestamps.values():
            timestamps.clear()
        
        logger.info("Error tracking data has been reset")

# Global error tracker instance
_error_tracker: Optional[AsyncErrorTracker] = None

def get_error_tracker() -> AsyncErrorTracker:
    """Get or create the global error tracker instance."""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = AsyncErrorTracker()
    return _error_tracker

# Notification handlers
async def log_alert_handler(alert: Alert):
    """Simple log-based alert handler."""
    severity_emoji = {
        AlertSeverity.LOW: "ℹ️",
        AlertSeverity.MEDIUM: "⚠️",
        AlertSeverity.HIGH: "🚨",
        AlertSeverity.CRITICAL: "🔥"
    }
    
    emoji = severity_emoji.get(alert.severity, "❓")
    logger.warning(f"{emoji} ALERT: {alert.title} - {alert.message}")

async def email_alert_handler(alert: Alert):
    """Email-based alert handler (placeholder - requires SMTP configuration)."""
    # This would require proper SMTP configuration
    # For now, just log that an email would be sent
    if alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]:
        logger.info(f"EMAIL ALERT would be sent: {alert.title}")

# Decorator for automatic error tracking
def track_database_errors(operation_name: str = "database_operation"):
    """Decorator to automatically track database errors."""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_tracker = get_error_tracker()
                error_tracker.track_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    operation=operation_name,
                    function_name=func.__name__,
                    stack_trace=str(e.__traceback__) if hasattr(e, '__traceback__') else None
                )
                raise
        
        return wrapper
    return decorator