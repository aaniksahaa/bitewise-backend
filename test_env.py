#!/usr/bin/env python3
"""
Test script to verify environment switching works correctly.
"""

import os
from dotenv import load_dotenv

def test_environment_switching():
    print("Testing environment switching...")
    
    # Initial load
    load_dotenv()
    print(f"Initial ENVIRONMENT: {os.getenv('ENVIRONMENT', 'not set')}")
    
    # Set environment variable
    os.environ['ENVIRONMENT'] = 'production'
    print(f"After setting in code: {os.getenv('ENVIRONMENT', 'not set')}")
    
    # Reload from file (should override with file value)
    load_dotenv(override=True)
    print(f"After reload from .env: {os.getenv('ENVIRONMENT', 'not set')}")
    
    # Test database connection
    try:
        from app.db.session import SessionLocal
        from app.core.config import settings
        
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Test connection
        db = SessionLocal()
        result = db.execute("SELECT 1").fetchone()
        db.close()
        print("✓ Database connection successful!")
        
    except Exception as e:
        print(f"✗ Database connection failed: {e}")

if __name__ == "__main__":
    test_environment_switching() 