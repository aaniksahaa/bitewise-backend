from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from app.db.async_session import (
    get_async_db_manager, 
    check_async_database_health,
    pool_metrics
)
from app.services.async_monitoring import get_database_monitor
from app.services.async_metrics import get_metrics_collector
from app.services.async_error_tracking import get_error_tracker

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Basic health status
    """
    try:
        manager = await get_async_db_manager()
        connection_test = await manager.test_connection()
        
        return {
            "status": "healthy" if connection_test else "unhealthy",
            "database": "connected" if connection_test else "disconnected",
            "service": "bitewise-backend"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@router.get("/health/database", response_model=Dict[str, Any])
async def database_health_check():
    """
    Comprehensive database health check with connection pool information.
    
    Returns:
        dict: Detailed database health status including pool metrics
    """
    try:
        health_status = await check_async_database_health()
        return health_status
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")

@router.get("/health/database/detailed", response_model=Dict[str, Any])
async def detailed_database_health():
    """
    Detailed database health check with recovery attempts and comprehensive metrics.
    
    Returns:
        dict: Comprehensive health status with recovery actions and detailed metrics
    """
    try:
        manager = await get_async_db_manager()
        health_result = await manager.perform_health_check_with_recovery()
        return health_result
    except Exception as e:
        logger.error(f"Detailed database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Detailed health check failed: {str(e)}")

@router.get("/health/database/pool", response_model=Dict[str, Any])
async def connection_pool_status():
    """
    Get current connection pool status and metrics.
    
    Returns:
        dict: Connection pool information and performance metrics
    """
    try:
        manager = await get_async_db_manager()
        pool_info = await manager.get_detailed_pool_info()
        return pool_info
    except Exception as e:
        logger.error(f"Pool status check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Pool status check failed: {str(e)}")

@router.get("/health/database/metrics", response_model=Dict[str, Any])
async def connection_pool_metrics():
    """
    Get connection pool performance metrics.
    
    Returns:
        dict: Performance metrics for connection pool monitoring
    """
    try:
        metrics = pool_metrics.get_metrics()
        return {
            "metrics": metrics,
            "status": "healthy" if metrics.get("success_rate", 0) > 0.95 else "degraded"
        }
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Metrics retrieval failed: {str(e)}")

@router.post("/health/database/metrics/reset")
async def reset_connection_pool_metrics():
    """
    Reset connection pool metrics.
    
    Returns:
        dict: Confirmation of metrics reset
    """
    try:
        pool_metrics.reset()
        return {
            "status": "success",
            "message": "Connection pool metrics have been reset",
            "reset_timestamp": pool_metrics.last_reset.isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Metrics reset failed: {str(e)}")

@router.get("/health/database/monitoring", response_model=Dict[str, Any])
async def database_monitoring_status():
    """
    Get database monitoring service status and recent health history.
    
    Returns:
        dict: Monitoring service status and health history
    """
    try:
        monitor = get_database_monitor()
        status = await monitor.get_comprehensive_status()
        return status
    except Exception as e:
        logger.error(f"Monitoring status check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Monitoring status check failed: {str(e)}")

@router.get("/health/database/history", response_model=Dict[str, Any])
async def database_health_history():
    """
    Get recent database health check history.
    
    Returns:
        dict: Recent health check results
    """
    try:
        monitor = get_database_monitor()
        history = monitor.get_health_history(20)  # Get last 20 checks
        return {
            "history": history,
            "count": len(history),
            "monitoring_status": monitor.get_monitoring_status()
        }
    except Exception as e:
        logger.error(f"Health history retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health history retrieval failed: {str(e)}")

@router.post("/health/database/monitoring/start")
async def start_database_monitoring():
    """
    Start the database monitoring service.
    
    Returns:
        dict: Confirmation of monitoring service start
    """
    try:
        monitor = get_database_monitor()
        await monitor.start_monitoring()
        return {
            "status": "success",
            "message": "Database monitoring service started",
            "monitoring_status": monitor.get_monitoring_status()
        }
    except Exception as e:
        logger.error(f"Failed to start monitoring service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")

@router.post("/health/database/monitoring/stop")
async def stop_database_monitoring():
    """
    Stop the database monitoring service.
    
    Returns:
        dict: Confirmation of monitoring service stop
    """
    try:
        monitor = get_database_monitor()
        await monitor.stop_monitoring()
        return {
            "status": "success",
            "message": "Database monitoring service stopped",
            "monitoring_status": monitor.get_monitoring_status()
        }
    except Exception as e:
        logger.error(f"Failed to stop monitoring service: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")

# Enhanced metrics endpoints
@router.get("/health/database/metrics/comprehensive", response_model=Dict[str, Any])
async def comprehensive_database_metrics():
    """
    Get comprehensive database performance metrics including query performance,
    connection pool trends, error analysis, and slow query analysis.
    
    Returns:
        dict: Comprehensive performance metrics and analysis
    """
    try:
        collector = get_metrics_collector()
        metrics = collector.get_comprehensive_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Comprehensive metrics retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Comprehensive metrics failed: {str(e)}")

@router.get("/health/database/metrics/query-performance", response_model=Dict[str, Any])
async def query_performance_metrics(time_window: int = Query(60, description="Time window in minutes")):
    """
    Get detailed query performance statistics for a specified time window.
    
    Args:
        time_window: Time window in minutes (default: 60)
        
    Returns:
        dict: Query performance statistics including execution times, success rates, and query type breakdown
    """
    try:
        collector = get_metrics_collector()
        stats = collector.get_query_performance_stats(time_window)
        return stats
    except Exception as e:
        logger.error(f"Query performance metrics retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Query performance metrics failed: {str(e)}")

@router.get("/health/database/metrics/pool-trends", response_model=Dict[str, Any])
async def pool_utilization_trends(time_window: int = Query(60, description="Time window in minutes")):
    """
    Get connection pool utilization trends and analysis.
    
    Args:
        time_window: Time window in minutes (default: 60)
        
    Returns:
        dict: Pool utilization trends, patterns, and historical data
    """
    try:
        collector = get_metrics_collector()
        trends = collector.get_connection_pool_trends(time_window)
        return trends
    except Exception as e:
        logger.error(f"Pool trends retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Pool trends failed: {str(e)}")

@router.get("/health/database/metrics/slow-queries", response_model=Dict[str, Any])
async def slow_query_analysis():
    """
    Get detailed analysis of slow database queries.
    
    Returns:
        dict: Slow query analysis including patterns, affected tables, and performance impact
    """
    try:
        collector = get_metrics_collector()
        analysis = collector.get_slow_query_analysis()
        return analysis
    except Exception as e:
        logger.error(f"Slow query analysis failed: {e}")
        raise HTTPException(status_code=503, detail=f"Slow query analysis failed: {str(e)}")

@router.post("/health/database/metrics/comprehensive/reset")
async def reset_comprehensive_metrics():
    """
    Reset all comprehensive database metrics.
    
    Returns:
        dict: Confirmation of metrics reset
    """
    try:
        collector = get_metrics_collector()
        collector.reset_metrics()
        return {
            "status": "success",
            "message": "All comprehensive database metrics have been reset",
            "reset_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Comprehensive metrics reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comprehensive metrics reset failed: {str(e)}")

# Error tracking and alerting endpoints
@router.get("/health/database/errors", response_model=Dict[str, Any])
async def database_error_summary(time_window: int = Query(60, description="Time window in minutes")):
    """
    Get comprehensive database error summary and analysis.
    
    Args:
        time_window: Time window in minutes (default: 60)
        
    Returns:
        dict: Error summary including patterns, rates, and recent errors
    """
    try:
        error_tracker = get_error_tracker()
        summary = error_tracker.get_error_summary(time_window)
        return summary
    except Exception as e:
        logger.error(f"Error summary retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Error summary failed: {str(e)}")

@router.get("/health/database/alerts", response_model=Dict[str, Any])
async def active_database_alerts():
    """
    Get all active database alerts.
    
    Returns:
        dict: List of active alerts with details and metadata
    """
    try:
        error_tracker = get_error_tracker()
        alerts = error_tracker.get_active_alerts()
        return {
            "active_alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Active alerts retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Active alerts retrieval failed: {str(e)}")

@router.get("/health/database/alerts/history", response_model=Dict[str, Any])
async def database_alert_history(limit: int = Query(50, description="Maximum number of alerts to return")):
    """
    Get database alert history.
    
    Args:
        limit: Maximum number of alerts to return (default: 50)
        
    Returns:
        dict: Historical alerts with resolution status and metadata
    """
    try:
        error_tracker = get_error_tracker()
        history = error_tracker.get_alert_history(limit)
        return {
            "alert_history": history,
            "count": len(history),
            "limit": limit,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Alert history retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Alert history retrieval failed: {str(e)}")

@router.post("/health/database/alerts/{alert_id}/resolve")
async def resolve_database_alert(alert_id: str, resolution_note: Optional[str] = None):
    """
    Resolve a specific database alert.
    
    Args:
        alert_id: ID of the alert to resolve
        resolution_note: Optional note about the resolution
        
    Returns:
        dict: Confirmation of alert resolution
    """
    try:
        error_tracker = get_error_tracker()
        resolved = error_tracker.resolve_alert(alert_id, resolution_note or "Manually resolved via API")
        
        if resolved:
            return {
                "status": "success",
                "message": f"Alert {alert_id} has been resolved",
                "alert_id": alert_id,
                "resolution_note": resolution_note,
                "resolved_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or already resolved")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Alert resolution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Alert resolution failed: {str(e)}")

@router.post("/health/database/errors/reset")
async def reset_error_tracking():
    """
    Reset all error tracking data and alerts.
    
    Returns:
        dict: Confirmation of error tracking reset
    """
    try:
        error_tracker = get_error_tracker()
        error_tracker.reset_error_tracking()
        return {
            "status": "success",
            "message": "All error tracking data and alerts have been reset",
            "reset_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error tracking reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error tracking reset failed: {str(e)}")

# Performance monitoring endpoint
@router.get("/health/database/performance", response_model=Dict[str, Any])
async def database_performance_overview():
    """
    Get comprehensive database performance overview combining metrics, errors, and health status.
    
    Returns:
        dict: Complete performance overview with recommendations
    """
    try:
        # Get data from all monitoring components
        manager = await get_async_db_manager()
        health_status = await manager.perform_health_check_with_recovery()
        
        collector = get_metrics_collector()
        metrics = collector.get_comprehensive_metrics()
        
        error_tracker = get_error_tracker()
        error_summary = error_tracker.get_error_summary(60)
        active_alerts = error_tracker.get_active_alerts()
        
        # Calculate performance score
        performance_score = _calculate_performance_score(health_status, metrics, error_summary)
        
        # Generate recommendations
        recommendations = _generate_performance_recommendations(health_status, metrics, error_summary, active_alerts)
        
        return {
            "performance_score": performance_score,
            "health_status": health_status.get("status", "unknown"),
            "metrics_summary": {
                "total_queries_last_hour": metrics.get("query_performance", {}).get("total_queries", 0),
                "avg_query_time": metrics.get("query_performance", {}).get("avg_execution_time", 0),
                "error_rate": metrics.get("query_performance", {}).get("error_rate", 0),
                "pool_utilization": health_status.get("pool_info", {}).get("health_indicators", {}).get("pool_utilization", 0)
            },
            "error_summary": {
                "total_errors_last_hour": error_summary.get("total_errors", 0),
                "error_rate": error_summary.get("error_rate", 0),
                "active_alerts": len(active_alerts)
            },
            "recommendations": recommendations,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Performance overview failed: {e}")
        raise HTTPException(status_code=503, detail=f"Performance overview failed: {str(e)}")

def _calculate_performance_score(health_status: Dict, metrics: Dict, error_summary: Dict) -> int:
    """Calculate a performance score from 0-100 based on various metrics."""
    score = 100
    
    # Health status impact
    if health_status.get("status") == "unhealthy":
        score -= 50
    elif health_status.get("status") == "degraded":
        score -= 25
    
    # Error rate impact
    error_rate = metrics.get("query_performance", {}).get("error_rate", 0)
    if error_rate > 0.1:  # > 10% error rate
        score -= 30
    elif error_rate > 0.05:  # > 5% error rate
        score -= 15
    elif error_rate > 0.01:  # > 1% error rate
        score -= 5
    
    # Pool utilization impact
    pool_util = health_status.get("pool_info", {}).get("health_indicators", {}).get("pool_utilization", 0)
    if pool_util > 0.9:  # > 90% utilization
        score -= 20
    elif pool_util > 0.8:  # > 80% utilization
        score -= 10
    
    # Query performance impact
    avg_query_time = metrics.get("query_performance", {}).get("avg_execution_time", 0)
    if avg_query_time > 2.0:  # > 2 seconds average
        score -= 20
    elif avg_query_time > 1.0:  # > 1 second average
        score -= 10
    
    return max(0, min(100, score))

def _generate_performance_recommendations(health_status: Dict, metrics: Dict, error_summary: Dict, active_alerts: List) -> List[str]:
    """Generate performance recommendations based on current metrics."""
    recommendations = []
    
    # Health-based recommendations
    if health_status.get("status") == "unhealthy":
        recommendations.append("Database is unhealthy - investigate connection issues immediately")
    elif health_status.get("status") == "degraded":
        recommendations.append("Database performance is degraded - monitor closely")
    
    # Error rate recommendations
    error_rate = metrics.get("query_performance", {}).get("error_rate", 0)
    if error_rate > 0.05:
        recommendations.append(f"High error rate ({error_rate:.2%}) - review recent errors and fix underlying issues")
    
    # Pool utilization recommendations
    pool_util = health_status.get("pool_info", {}).get("health_indicators", {}).get("pool_utilization", 0)
    if pool_util > 0.8:
        recommendations.append(f"High pool utilization ({pool_util:.1%}) - consider increasing pool size")
    
    # Query performance recommendations
    avg_query_time = metrics.get("query_performance", {}).get("avg_execution_time", 0)
    if avg_query_time > 1.0:
        recommendations.append(f"Slow average query time ({avg_query_time:.3f}s) - optimize slow queries")
    
    # Slow query recommendations
    slow_queries = metrics.get("slow_query_analysis", {}).get("total_slow_queries", 0)
    if slow_queries > 0:
        recommendations.append(f"Found {slow_queries} slow queries - review and optimize")
    
    # Alert-based recommendations
    if active_alerts:
        recommendations.append(f"{len(active_alerts)} active alerts require attention")
    
    # Default recommendation if everything looks good
    if not recommendations:
        recommendations.append("Database performance looks good - continue monitoring")
    
    return recommendations