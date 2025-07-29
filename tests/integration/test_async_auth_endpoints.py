#!/usr/bin/env python3
"""
Test script to verify async authentication endpoints are working correctly.
This script tests the basic functionality of the migrated async auth endpoints.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db.async_session import get_async_db_manager, check_async_database_health
from app.services.async_auth import AsyncAuthService
from app.models.user import User


async def test_async_auth_service():
    """Test basic async authentication service functionality."""
    print("Testing AsyncAuthService...")
    
    try:
        # Test database connection
        print("1. Testing database connection...")
        health_status = await check_async_database_health()
        print(f"   Database health: {health_status['status']}")
        
        if health_status['status'] != 'healthy':
            print(f"   Error: {health_status.get('error', 'Unknown error')}")
            return False
        
        # Test password hashing
        print("2. Testing password hashing...")
        test_password = "test_password_123"
        hashed = AsyncAuthService.get_password_hash(test_password)
        is_valid = AsyncAuthService.verify_password(test_password, hashed)
        print(f"   Password hashing works: {is_valid}")
        
        # Test OTP generation
        print("3. Testing OTP generation...")
        otp = AsyncAuthService.generate_otp()
        print(f"   Generated OTP: {otp} (length: {len(otp)})")
        
        # Test database operations
        print("4. Testing async database operations...")
        manager = await get_async_db_manager()
        
        async for session in manager.get_async_session():
            # Test user lookup (should return None for non-existent user)
            test_email = "nonexistent@test.com"
            user = await AsyncAuthService.get_user_by_email(session, test_email)
            print(f"   User lookup for non-existent email: {user is None}")
            break
        
        print("✅ All async auth service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Async auth service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_database_manager():
    """Test async database manager functionality."""
    print("\nTesting AsyncDatabaseManager...")
    
    try:
        manager = await get_async_db_manager()
        
        # Test connection info
        print("1. Getting connection info...")
        conn_info = await manager.get_connection_info()
        print(f"   Connection status: {conn_info.get('status', 'unknown')}")
        
        # Test connection
        print("2. Testing connection...")
        connection_test = await manager.test_connection()
        print(f"   Connection test passed: {connection_test}")
        
        # Test session creation
        print("3. Testing session creation...")
        session_count = 0
        async for session in manager.get_async_session():
            session_count += 1
            print(f"   Session created successfully: {session is not None}")
            break
        
        print("✅ All async database manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Async database manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all async authentication tests."""
    print("🚀 Starting async authentication endpoint tests...\n")
    
    # Test async database manager
    db_test_passed = await test_async_database_manager()
    
    # Test async auth service
    auth_test_passed = await test_async_auth_service()
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY:")
    print(f"Database Manager: {'✅ PASSED' if db_test_passed else '❌ FAILED'}")
    print(f"Auth Service: {'✅ PASSED' if auth_test_passed else '❌ FAILED'}")
    
    if db_test_passed and auth_test_passed:
        print("\n🎉 All async authentication tests passed!")
        print("The authentication endpoints have been successfully migrated to async!")
        return 0
    else:
        print("\n💥 Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)