#!/usr/bin/env python3
"""
Verification script to ensure the async-only migration is complete and working.
"""

import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_application_startup():
    """Verify that the application can start successfully."""
    print("🔍 Verifying Application Startup")
    print("=" * 50)
    
    try:
        # Test main app import
        from app.main import app
        print("✅ FastAPI application imports successfully")
        
        # Test monitoring services
        from app.services.async_metrics import get_metrics_collector
        from app.services.async_error_tracking import get_error_tracker
        from app.services.async_monitoring import get_database_monitor
        print("✅ Monitoring services import successfully")
        
        # Test health endpoints
        from app.api.endpoints.health import (
            health_check,
            database_health_check,
            comprehensive_database_metrics
        )
        print("✅ Health endpoints import successfully")
        
        # Test agent service
        from app.services.agent import AgentService
        print("✅ Agent service imports successfully")
        
        # Test async database manager
        from app.db.async_session import get_async_db_manager
        manager = await get_async_db_manager()
        print("✅ Async database manager initializes successfully")
        
        # Test basic health check
        health_result = await health_check()
        print(f"✅ Basic health check: {health_result.get('status')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Application startup verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_monitoring_functionality():
    """Verify that monitoring functionality is working."""
    print("\n🔍 Verifying Monitoring Functionality")
    print("=" * 50)
    
    try:
        # Initialize monitoring components
        from app.services.async_metrics import get_metrics_collector
        from app.services.async_error_tracking import get_error_tracker
        from app.db.monitored_session import get_monitored_async_db
        from sqlalchemy import text
        
        metrics_collector = get_metrics_collector()
        error_tracker = get_error_tracker()
        print("✅ Monitoring components initialized")
        
        # Test monitored database session
        async with get_monitored_async_db() as session:
            result = await session.execute(text("SELECT 1 as test"))
            value = result.scalar()
            print(f"✅ Monitored database session works: {value}")
        
        # Check metrics collection
        query_stats = metrics_collector.get_query_performance_stats(5)
        print(f"✅ Metrics collection working: {query_stats.get('total_queries', 0)} queries tracked")
        
        # Check error tracking
        error_summary = error_tracker.get_error_summary(5)
        print(f"✅ Error tracking working: {error_summary.get('total_errors', 0)} errors tracked")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring functionality verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_health_endpoints():
    """Verify that health endpoints are working."""
    print("\n🔍 Verifying Health Endpoints")
    print("=" * 50)
    
    try:
        from app.api.endpoints.health import (
            health_check,
            database_health_check,
            comprehensive_database_metrics,
            database_error_summary,
            active_database_alerts
        )
        
        # Test basic health check
        health = await health_check()
        print(f"✅ Basic health check: {health.get('status')}")
        
        # Test database health check
        db_health = await database_health_check()
        print(f"✅ Database health check: {db_health.get('connection_test')}")
        
        # Test comprehensive metrics
        metrics = await comprehensive_database_metrics()
        print("✅ Comprehensive metrics endpoint working")
        
        # Test error summary
        errors = await database_error_summary(time_window=5)
        print(f"✅ Error summary endpoint: {errors.get('total_errors', 0)} errors")
        
        # Test active alerts
        alerts = await active_database_alerts()
        print(f"✅ Active alerts endpoint: {alerts.get('count', 0)} alerts")
        
        return True
        
    except Exception as e:
        print(f"❌ Health endpoints verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all verification tests."""
    print("🚀 Async-Only Migration Verification")
    print("=" * 80)
    
    # Test 1: Application startup
    startup_success = await verify_application_startup()
    
    # Test 2: Monitoring functionality
    monitoring_success = await verify_monitoring_functionality()
    
    # Test 3: Health endpoints
    health_success = await verify_health_endpoints()
    
    # Summary
    print("\n📋 Verification Summary")
    print("=" * 40)
    print(f"Application Startup: {'✅ PASS' if startup_success else '❌ FAIL'}")
    print(f"Monitoring Functionality: {'✅ PASS' if monitoring_success else '❌ FAIL'}")
    print(f"Health Endpoints: {'✅ PASS' if health_success else '❌ FAIL'}")
    
    overall_success = startup_success and monitoring_success and health_success
    print(f"\nOverall Result: {'🎉 ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Async-only migration is complete and working correctly!")
        print("✅ Application can start successfully")
        print("✅ Monitoring and observability is fully functional")
        print("✅ Health endpoints are operational")
        print("✅ Database connections are working properly")
    else:
        print("\n❌ Some issues were found that need to be addressed")
    
    return overall_success

if __name__ == "__main__":
    # Run the verification
    success = asyncio.run(main())
    exit(0 if success else 1)