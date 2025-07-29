#!/usr/bin/env python3
"""
Final Async Verification

This script performs a comprehensive verification of the async database migration.
It checks:
1. No synchronous database imports
2. All endpoints use async database sessions
3. All services use async database methods
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_verification_script(script_path: str) -> bool:
    """
    Run a verification script and return True if it passes.
    
    Args:
        script_path: Path to the verification script
        
    Returns:
        bool: True if verification passes, False otherwise
    """
    try:
        logger.info(f"Running {os.path.basename(script_path)}...")
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Check if verification passed
        passed = result.returncode == 0
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{os.path.basename(script_path)}: {status}")
        
        return passed
    
    except Exception as e:
        logger.error(f"Error running {script_path}: {e}")
        return False

def main():
    """Main function."""
    logger.info("Starting final async verification")
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define verification scripts
    verification_scripts = [
        os.path.join(script_dir, "verify_async_only_migration.py"),
        os.path.join(script_dir, "test_endpoint_async_verification.py"),
    ]
    
    # Run verification scripts
    results = []
    for script in verification_scripts:
        if os.path.isfile(script):
            result = run_verification_script(script)
            results.append((os.path.basename(script), result))
        else:
            logger.warning(f"Verification script not found: {script}")
            results.append((os.path.basename(script), False))
    
    # Print summary
    print("\n=== Final Async Verification Summary ===")
    all_passed = True
    for script_name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"{script_name}: {status}")
        all_passed = all_passed and passed
    
    # Final result
    if all_passed:
        logger.info("All verifications passed! Async migration is complete.")
        sys.exit(0)
    else:
        logger.warning("Some verifications failed. Async migration is incomplete.")
        sys.exit(1)

if __name__ == "__main__":
    main()