"""
Async database monitoring service for connection pool health and performance tracking.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import json

from app.core.config import settings
from app.db.async_session import get_async_db_manager, pool_metrics

logger = logging.getLogger(__name__)

class AsyncDatabaseMonitor:
    """
    Background service for monitoring async database connection pool health and performance.
    """
    
    def __init__(self):
        self.is_running = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.health_check_interval = settings.ASYNC_DB_HEALTH_CHECK_INTERVAL
        self.metrics_reset_interval = settings.ASYNC_DB_METRICS_RESET_INTERVAL
        self.last_metrics_reset = datetime.now(timezone.utc)
        self.health_history = []
        self.max_history_size = 100  # Keep last 100 health checks
    
    async def start_monitoring(self):
        """Start the background monitoring task."""
        if self.is_running:
            logger.warning("Database monitoring is already running")
            return
        
        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started async database monitoring with {self.health_check_interval}s interval")
    
    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped async database monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that runs health checks and collects metrics."""
        while self.is_running:
            try:
                await self._perform_health_check()
                await self._check_metrics_reset()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(min(self.health_check_interval, 60))  # Wait at least 60s on error
    
    async def _perform_health_check(self):
        """Perform a health check and store results."""
        try:
            manager = await get_async_db_manager()
            health_result = await manager.perform_health_check_with_recovery()
            
            # Add timestamp and store in history
            health_result["check_timestamp"] = datetime.now(timezone.utc).isoformat()
            self.health_history.append(health_result)
            
            # Limit history size
            if len(self.health_history) > self.max_history_size:
                self.health_history = self.health_history[-self.max_history_size:]
            
            # Log health status
            status = health_result.get("status", "unknown")
            if status == "unhealthy":
                logger.error(f"Database health check failed: {health_result}")
            elif status == "degraded":
                logger.warning(f"Database health degraded: {health_result}")
            else:
                logger.debug(f"Database health check passed: {status}")
            
            # Log recovery actions if any
            recovery_actions = health_result.get("recovery_actions", [])
            if recovery_actions:
                logger.info(f"Database recovery actions taken: {recovery_actions}")
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            # Store error in history
            error_result = {
                "status": "error",
                "error": str(e),
                "check_timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.health_history.append(error_result)
    
    async def _check_metrics_reset(self):
        """Check if metrics should be reset based on configured interval."""
        now = datetime.now(timezone.utc)
        time_since_reset = (now - self.last_metrics_reset).total_seconds()
        
        if time_since_reset >= self.metrics_reset_interval:
            logger.info("Resetting connection pool metrics")
            pool_metrics.reset()
            self.last_metrics_reset = now
    
    def get_health_history(self, limit: int = 10) -> list:
        """
        Get recent health check history.
        
        Args:
            limit: Maximum number of recent checks to return
            
        Returns:
            list: Recent health check results
        """
        return self.health_history[-limit:] if self.health_history else []
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        Get current monitoring service status.
        
        Returns:
            dict: Monitoring service status and configuration
        """
        return {
            "is_running": self.is_running,
            "health_check_interval": self.health_check_interval,
            "metrics_reset_interval": self.metrics_reset_interval,
            "last_metrics_reset": self.last_metrics_reset.isoformat(),
            "health_history_size": len(self.health_history),
            "max_history_size": self.max_history_size
        }
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring status including current health and metrics.
        
        Returns:
            dict: Complete monitoring status with current health and metrics
        """
        try:
            manager = await get_async_db_manager()
            current_health = await manager.perform_health_check_with_recovery()
            pool_info = await manager.get_detailed_pool_info()
            
            return {
                "monitoring": self.get_monitoring_status(),
                "current_health": current_health,
                "pool_info": pool_info,
                "recent_history": self.get_health_history(5)
            }
        except Exception as e:
            logger.error(f"Error getting comprehensive status: {e}")
            return {
                "monitoring": self.get_monitoring_status(),
                "error": str(e),
                "recent_history": self.get_health_history(5)
            }

# Global monitoring instance
_monitor_instance: Optional[AsyncDatabaseMonitor] = None

def get_database_monitor() -> AsyncDatabaseMonitor:
    """Get or create the global database monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AsyncDatabaseMonitor()
    return _monitor_instance

async def start_database_monitoring():
    """Start database monitoring service."""
    monitor = get_database_monitor()
    await monitor.start_monitoring()

async def stop_database_monitoring():
    """Stop database monitoring service."""
    monitor = get_database_monitor()
    await monitor.stop_monitoring()