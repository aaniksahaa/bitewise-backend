#!/usr/bin/env python3
"""
Simplified test script for Google OAuth configuration.
This script tests only the configuration without database models.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append('.')

def test_google_oauth_config():
    """Test Google OAuth configuration."""
    print("🔧 Testing Google OAuth Configuration...")
    
    try:
        from app.core.config import settings
        
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
        print(f"✅ Environment: {settings.ENVIRONMENT}")
        
        return True
    except Exception as e:
        print(f"❌ Error loading settings: {str(e)}")
        return False

def test_fastapi_sso_import():
    """Test FastAPI SSO library import."""
    print("\n📦 Testing FastAPI SSO Import...")
    
    try:
        from fastapi_sso.sso.google import GoogleSSO
        print("✅ FastAPI SSO library imported successfully")
        
        # Test GoogleSSO initialization
        from app.core.config import settings
        google_sso = GoogleSSO(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_CALLBACK_URL,
            allow_insecure_http=settings.ENVIRONMENT == "development",
        )
        
        print("✅ GoogleSSO instance created successfully")
        return True
    except Exception as e:
        print(f"❌ Error with FastAPI SSO: {str(e)}")
        return False

def test_auth_service_basic():
    """Test basic AuthService methods without database."""
    print("\n🛠️  Testing AuthService Basic Methods...")
    
    try:
        from app.services.auth import AuthService
        
        # Test password hashing
        password = "test_password"
        hashed = AuthService.get_password_hash(password)
        if AuthService.verify_password(password, hashed):
            print("✅ Password hashing and verification working")
        else:
            print("❌ Password verification failed")
            return False
        
        # Test OTP generation
        otp = AuthService.generate_otp()
        if len(otp) == 6 and otp.isdigit():
            print(f"✅ OTP generation working: {otp}")
        else:
            print(f"❌ OTP generation failed: {otp}")
            return False
        
        # Test token generation
        test_token = AuthService.create_access_token(user_id=1)
        if test_token:
            print(f"✅ Access token generation working")
        else:
            print(f"❌ Access token generation failed")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Error testing AuthService methods: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🧪 Simplified Google OAuth Test Suite")
    print("=" * 50)
    
    tests = [
        test_google_oauth_config,
        test_fastapi_sso_import,
        test_auth_service_basic,
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
        print("🎉 All basic tests passed! Google OAuth configuration is correct.")
        print("\n📋 Next Steps:")
        print("1. Start the server: python run.py")
        print("2. Visit: http://localhost:8000/api/v1/auth/google/login")
        print("3. Test the full OAuth flow")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 