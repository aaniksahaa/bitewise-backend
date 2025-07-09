#!/usr/bin/env python3
"""
Alembic Database Check Script
============================

This script checks:
1. Which database URL Alembic will connect to
2. Current Alembic revision status
3. Database accessibility
4. Migration history summary

Run this before any Alembic operations to ensure safety.
"""

import os
import sys
import subprocess
from datetime import datetime
from typing import Optional, Tuple

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.core.config import settings
    from app.db.session import SessionLocal
    from sqlalchemy import text
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're in the correct directory and have installed dependencies")
    sys.exit(1)

# Load environment variables
load_dotenv()

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{Colors.OKBLUE}{Colors.BOLD}🔍 {title}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'-'*50}{Colors.ENDC}")

def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")

def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")

def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.OKCYAN}ℹ️  {message}{Colors.ENDC}")

def get_database_info() -> Tuple[str, str, str]:
    """Get database connection information"""
    environment = settings.ENVIRONMENT
    
    if environment == "development":
        db_url = settings.LOCAL_DATABASE_URL
        db_type = "LOCAL"
    else:
        db_url = settings.DATABASE_URL
        db_type = "PRODUCTION"
    
    # Extract database name from URL
    try:
        db_name = db_url.split('/')[-1]
        if '?' in db_name:
            db_name = db_name.split('?')[0]
    except:
        db_name = "unknown"
    
    return environment, db_url, db_name, db_type

def test_database_connection(db_url: str) -> Tuple[bool, Optional[str]]:
    """Test database connection"""
    try:
        db = SessionLocal()
        result = db.execute(text('SELECT version()'))
        version = result.fetchone()[0]
        db.close()
        return True, version
    except Exception as e:
        return False, str(e)

def run_alembic_command(command: str) -> Tuple[bool, str]:
    """Run an Alembic command and return result"""
    try:
        result = subprocess.run(
            ['alembic'] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip() if e.stderr else e.stdout.strip()
    except Exception as e:
        return False, str(e)

def get_alembic_current() -> Tuple[bool, str]:
    """Get current Alembic revision"""
    return run_alembic_command("current")

def get_alembic_history() -> Tuple[bool, str]:
    """Get Alembic migration history"""
    return run_alembic_command("history")

def get_alembic_heads() -> Tuple[bool, str]:
    """Get Alembic head revisions"""
    return run_alembic_command("heads")

def analyze_database_safety(db_name: str, environment: str) -> str:
    """Analyze database safety level"""
    if environment.lower() == "production":
        return "DANGER"
    elif "test" in db_name.lower():
        return "SAFE"
    elif "dev" in db_name.lower():
        return "CAUTION"
    else:
        return "UNKNOWN"

def main():
    """Main function"""
    print_header("ALEMBIC DATABASE SAFETY CHECK")
    print(f"{Colors.OKCYAN}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    
    # 1. Environment and Database Information
    print_section("Environment & Database Configuration")
    
    try:
        environment, db_url, db_name, db_type = get_database_info()
        
        print_info(f"Environment: {environment}")
        print_info(f"Database Type: {db_type}")
        print_info(f"Database Name: {db_name}")
        print_info(f"Database URL: {db_url}")
        
        # Safety analysis
        safety_level = analyze_database_safety(db_name, environment)
        
        if safety_level == "SAFE":
            print_success(f"Safety Level: {safety_level} - Test database detected")
        elif safety_level == "CAUTION":
            print_warning(f"Safety Level: {safety_level} - Development database")
        elif safety_level == "DANGER":
            print_error(f"Safety Level: {safety_level} - Production database!")
        else:
            print_warning(f"Safety Level: {safety_level} - Please verify database")
            
    except Exception as e:
        print_error(f"Failed to get database info: {e}")
        return False
    
    # 2. Database Connection Test
    print_section("Database Connection Test")
    
    connection_ok, connection_result = test_database_connection(db_url)
    
    if connection_ok:
        print_success("Database connection successful!")
        print_info(f"PostgreSQL Version: {connection_result.split()[1] if connection_result else 'Unknown'}")
    else:
        print_error(f"Database connection failed: {connection_result}")
        print_warning("Cannot proceed with Alembic operations")
        return False
    
    # 3. Alembic Current Status
    print_section("Alembic Migration Status")
    
    current_ok, current_result = get_alembic_current()
    
    if current_ok:
        if current_result and current_result.strip():
            print_success(f"Current revision: {current_result}")
        else:
            print_warning("No current revision (database not initialized)")
    else:
        print_error(f"Failed to get current revision: {current_result}")
    
    # 4. Alembic Head Status
    heads_ok, heads_result = get_alembic_heads()
    
    if heads_ok:
        print_info(f"Latest available revision: {heads_result}")
    else:
        print_warning(f"Could not get head revision: {heads_result}")
    
    # 5. Migration History Summary
    print_section("Migration History Summary")
    
    history_ok, history_result = get_alembic_history()
    
    if history_ok:
        history_lines = history_result.split('\n')
        migration_count = len([line for line in history_lines if line.strip() and not line.startswith('Rev:')])
        print_info(f"Total migrations available: {migration_count}")
        
        if len(history_lines) > 0:
            print_info("Recent migrations:")
            for line in history_lines[:5]:  # Show first 5 lines
                if line.strip():
                    print(f"  {line}")
    else:
        print_warning(f"Could not get migration history: {history_result}")
    
    # 6. Safety Summary
    print_section("Safety Summary")
    
    if safety_level == "SAFE":
        print_success("✅ SAFE TO PROCEED - Test database detected")
        print_info("You can safely run: alembic upgrade head")
    elif safety_level == "CAUTION":
        print_warning("⚠️  PROCEED WITH CAUTION - Development database")
        print_info("Make sure this is intentional before running migrations")
    elif safety_level == "DANGER":
        print_error("🚨 DANGER - Production database detected!")
        print_error("DO NOT run migrations unless you're absolutely sure!")
    else:
        print_warning("❓ UNKNOWN DATABASE - Please verify before proceeding")
    
    print_header("CHECK COMPLETE")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}⚠️  Check interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Unexpected error: {e}{Colors.ENDC}")
        sys.exit(1) 