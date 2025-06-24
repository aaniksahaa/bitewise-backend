#!/usr/bin/env python3
"""
Test script for Google OAuth authentication endpoints.
This script tests the Google authentication flow configuration.
"""

import sys
import os
import requests
from urllib.parse import urlparse, parse_qs

# Add the app directory to the Python path
sys.path.append('.')

from app.core.config import settings

def test_google_oauth_config():
    """Test Google OAuth configuration."""
    print("🔧 Testing Google OAuth Configuration...")
    
    # Check if required environment variables are set
    if not settings.GOOGLE_CLIENT_ID:
        print("❌ GOOGLE_CLIENT_ID is not set in environment variables")
        return False
    
    if not settings.GOOGLE_CLIENT_SECRET:
        print("❌ GOOGLE_CLIENT_SECRET is not set in environment variables")
        return False
    
    if not settings.GOOGLE_CALLBACK_URL:
        print("❌ GOOGLE_CALLBACK_URL is not set in environment variables")
        return False
    
    print(f"✅ Google Client ID: {settings.GOOGLE_CLIENT_ID[:10]}...")
    print(f"✅ Google Client Secret: {settings.GOOGLE_CLIENT_SECRET[:10]}...")
    print(f"✅ Google Callback URL: {settings.GOOGLE_CALLBACK_URL}")
    
    return True

def test_google_login_endpoint():
    """Test the Google login endpoint availability."""
    print("\n🔗 Testing Google Login Endpoint...")
    
    # Assuming the server is running on localhost:8000
    base_url = "http://localhost:8000"
    login_url = f"{base_url}{settings.API_V1_PREFIX}/auth/google/login"
    
    try:
        # Test if the endpoint is accessible (should redirect to Google)
        response = requests.get(login_url, allow_redirects=False)
        
        if response.status_code == 307:  # Temporary redirect to Google
            redirect_url = response.headers.get('location', '')
            if 'accounts.google.com' in redirect_url:
                print(f"✅ Google login endpoint working - redirects to Google")
                print(f"   Redirect URL: {redirect_url[:100]}...")
                return True
            else:
                print(f"❌ Google login endpoint redirects to unexpected URL: {redirect_url}")
                return False
        else:
            print(f"❌ Google login endpoint returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Could not connect to server. Make sure the server is running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error testing Google login endpoint: {str(e)}")
        return False

def test_auth_service_methods():
    """Test AuthService methods used in Google OAuth."""
    print("\n🛠️  Testing AuthService Methods...")
    
    try:
        from app.services.auth import AuthService
        from app.db.session import SessionLocal
        
        # Test username generation
        with SessionLocal() as db:
            test_username = AuthService.generate_unique_username(db, "testuser")
            print(f"✅ Username generation working: {test_username}")
        
        # Test token generation
        test_token = AuthService.create_access_token(user_id=1)
        if test_token:
            print(f"✅ Access token generation working")
        else:
            print(f"❌ Access token generation failed")
            
        return True
    except Exception as e:
        print(f"❌ Error testing AuthService methods: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🧪 Google OAuth Authentication Test Suite")
    print("=" * 50)
    
    tests = [
        test_google_oauth_config,
        test_auth_service_methods,
        test_google_login_endpoint,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {str(e)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google OAuth is configured correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 