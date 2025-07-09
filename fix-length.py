#!/usr/bin/env python3
"""
Fix Alembic Version Table Character Length

This script fixes the common issue where alembic_version table has VARCHAR(32)
but revision IDs are longer than 32 characters.

Usage: python fix_length.py
"""

import os
import sys

# Add the app directory to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.session import SessionLocal
from sqlalchemy import text

def fix_alembic_version_length():
    """Fix alembic_version table to support longer revision IDs"""
    
    db = SessionLocal()
    
    try:
        print("🔧 Fixing alembic_version table character length...")
        print(f"📍 Database: {settings.LOCAL_DATABASE_URL}")
        print()
        
        # Check if table exists
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'alembic_version'
        """))
        table_exists = result.fetchone()
        
        if table_exists:
            print("📋 alembic_version table exists - checking column length...")
            
            # Check current column length
            result = db.execute(text("""
                SELECT character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = 'alembic_version' 
                AND column_name = 'version_num'
            """))
            current_length = result.fetchone()
            
            if current_length and current_length[0] < 100:
                print(f"⚠️  Current length: VARCHAR({current_length[0]})")
                print("🔄 Altering column to VARCHAR(100)...")
                
                db.execute(text("""
                    ALTER TABLE alembic_version 
                    ALTER COLUMN version_num TYPE VARCHAR(100)
                """))
                db.commit()
                print("✅ Successfully altered alembic_version table!")
                
            else:
                print("✅ Column already has sufficient length (VARCHAR(100) or more)")
                
        else:
            print("📋 alembic_version table doesn't exist - creating with VARCHAR(100)...")
            
            db.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(100) NOT NULL PRIMARY KEY
                )
            """))
            db.commit()
            print("✅ Successfully created alembic_version table!")
            
        print()
        print("🎉 Fix completed! You can now run: alembic upgrade head")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()
        
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("         ALEMBIC VERSION TABLE LENGTH FIX")
    print("=" * 60)
    print()
    
    success = fix_alembic_version_length()
    
    print()
    print("=" * 60)
    
    if success:
        print("✅ Fix completed successfully!")
        print("💡 Next steps:")
        print("   1. Run: alembic upgrade head")
        print("   2. Run your seed scripts if needed")
    else:
        print("❌ Fix failed - check the error above")
        sys.exit(1) 