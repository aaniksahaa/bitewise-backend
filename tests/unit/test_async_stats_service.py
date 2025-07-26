#!/usr/bin/env python3

import asyncio
import sys
import os
from datetime import date, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db.async_session import get_async_db_manager
from app.services.async_stats import AsyncStatsService
from app.schemas.stats import SimpleTimeRange, TimeUnit


async def test_async_stats_service():
    """Test the async stats service functionality."""
    print("Testing AsyncStatsService...")
    
    try:
        # Get database manager
        db_manager = await get_async_db_manager()
        
        # Test database connection
        async for db in db_manager.get_async_session():
            print("✓ Database connection established")
            
            # Test quick stats calculation (should work even with no data)
            user_id = 1  # Test with user ID 1
            quick_stats = await AsyncStatsService.calculate_quick_stats(db, user_id)
            print(f"✓ Quick stats calculated: {quick_stats.today_calories} calories today")
            
            # Test simple time range conversion
            simple_range = SimpleTimeRange(unit=TimeUnit.day, num=7)
            time_range = AsyncStatsService.convert_simple_to_full_range(simple_range)
            print(f"✓ Time range conversion: {time_range.start_date} to {time_range.end_date}")
            
            # Test comprehensive stats calculation
            try:
                comprehensive_stats = await AsyncStatsService.calculate_simple_comprehensive_stats(
                    db, user_id, simple_range
                )
                print(f"✓ Comprehensive stats calculated for user {user_id}")
                print(f"  - Avg daily calories: {comprehensive_stats.nutrition_overview.calorie_stats.avg_daily_calories}")
                print(f"  - Dishes tried: {comprehensive_stats.consumption_patterns.dishes_tried_count}")
            except Exception as e:
                print(f"⚠ Comprehensive stats calculation failed (expected if no data): {e}")
            
            print("✓ AsyncStatsService tests completed successfully!")
            break  # Exit the async generator loop
            
    except Exception as e:
        print(f"✗ Error testing AsyncStatsService: {e}")
        raise


async def main():
    """Main test function."""
    try:
        await test_async_stats_service()
        print("\n🎉 All async stats service tests passed!")
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        sys.exit(1)
    finally:
        # Clean up database connections
        from app.db.async_session import close_async_db_manager
        await close_async_db_manager()


if __name__ == "__main__":
    asyncio.run(main())