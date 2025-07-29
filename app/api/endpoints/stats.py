from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timedelta
from typing import Optional

from app.db.async_session import get_async_db
from app.services.async_auth import AsyncAuthService, get_current_active_user_async
from app.services.async_stats import AsyncStatsService
from app.schemas.stats import (
    StatsTimeRange, TimePeriod, SimpleTimeRange, TimeUnit, ComprehensiveStats, QuickStats,
    CalorieStats, MacronutrientStats, MicronutrientStats,
    ConsumptionPatternStats, ProgressStats, NutritionOverview,
    PeriodComparison
)
from app.models.user import User

router = APIRouter()


@router.get("/quick", response_model=QuickStats)
async def get_quick_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get quick statistics for dashboard display."""
    return await AsyncStatsService.calculate_quick_stats(db=db, user_id=current_user.id)


@router.get("/comprehensive", response_model=ComprehensiveStats)
async def get_comprehensive_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get comprehensive statistics for a given time period."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_comprehensive_stats(
        db=db, 
        user_id=current_user.id, 
        simple_range=simple_range
    )


@router.get("/calories", response_model=CalorieStats)
async def get_calorie_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get detailed calorie intake statistics."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_calorie_stats(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/macronutrients", response_model=MacronutrientStats)
async def get_macronutrient_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get macronutrient distribution and trends statistics."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_macronutrient_stats(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/micronutrients", response_model=MicronutrientStats)
async def get_micronutrient_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get micronutrient intake statistics and deficiency alerts."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_micronutrient_stats(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/consumption-patterns", response_model=ConsumptionPatternStats)
async def get_consumption_pattern_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get food consumption pattern statistics."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_consumption_patterns(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/progress", response_model=ProgressStats)
async def get_progress_stats(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get health and fitness progress statistics."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_progress_stats(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/nutrition-overview", response_model=NutritionOverview)
async def get_nutrition_overview(
    unit: TimeUnit = Query(..., description="Time unit (hour, day, week, month, year)"),
    num: int = Query(..., ge=1, le=365, description="Number of time units (1-365)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get comprehensive nutrition overview including calories, macros, and micronutrients."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    return await AsyncStatsService.calculate_simple_nutrition_overview(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )


@router.get("/trends")
async def get_trend_analysis(
    unit: TimeUnit = Query(default=TimeUnit.day, description="Time unit for trend analysis"),
    num: int = Query(default=30, ge=7, le=365, description="Number of time units to analyze"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get trend analysis for various metrics over time."""
    simple_range = SimpleTimeRange(unit=unit, num=num)
    
    stats = await AsyncStatsService.calculate_simple_comprehensive_stats(
        db=db,
        user_id=current_user.id,
        simple_range=simple_range
    )
    
    # Extract trend data
    calorie_data = [
        {"date": dp.timestamp.date(), "calories": float(dp.calories)}
        for dp in stats.nutrition_overview.calorie_stats.data_points
    ]
    
    macro_data = [
        {
            "date": dp.date,
            "carbs": float(dp.carbs_g),
            "protein": float(dp.protein_g),
            "fats": float(dp.fats_g)
        }
        for dp in stats.nutrition_overview.macronutrient_stats.data_points
    ]
    
    return {
        "period": f"{num} {unit}s",
        "calorie_trend": calorie_data,
        "macronutrient_trend": macro_data,
        "insights": stats.advanced_analytics.optimization_suggestions if stats.advanced_analytics else []
    }


# Legacy endpoints (keeping the old API for backward compatibility)
@router.get("/legacy/comprehensive", response_model=ComprehensiveStats)
async def get_comprehensive_stats_legacy(
    start_date: date = Query(..., description="Start date for statistics calculation"),
    end_date: date = Query(..., description="End date for statistics calculation"),
    period: TimePeriod = Query(default=TimePeriod.daily, description="Data granularity"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get comprehensive statistics for a given time range (legacy endpoint)."""
    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before or equal to end date"
        )
    
    # Limit the range to prevent performance issues
    days_diff = (end_date - start_date).days
    if days_diff > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 365 days"
        )
    
    time_range = StatsTimeRange(
        start_date=start_date,
        end_date=end_date,
        period=period
    )
    
    return await AsyncStatsService.calculate_comprehensive_stats(
        db=db, 
        user_id=current_user.id, 
        time_range=time_range
    )


@router.get("/weekly-summary", response_model=ComprehensiveStats)
async def get_weekly_summary(
    week_offset: int = Query(default=0, description="Weeks ago (0 = current week, 1 = last week, etc.)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get comprehensive stats for a specific week."""
    if week_offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Week offset must be non-negative"
        )
    
    # Calculate the start and end of the specified week
    today = date.today()
    days_since_monday = today.weekday()
    current_week_start = today - timedelta(days=days_since_monday)
    
    # Calculate the target week
    target_week_start = current_week_start - timedelta(weeks=week_offset)
    target_week_end = target_week_start + timedelta(days=6)
    
    time_range = StatsTimeRange(
        start_date=target_week_start,
        end_date=target_week_end,
        period=TimePeriod.daily
    )
    
    return await AsyncStatsService.calculate_comprehensive_stats(
        db=db,
        user_id=current_user.id,
        time_range=time_range
    )


@router.get("/monthly-summary", response_model=ComprehensiveStats)
async def get_monthly_summary(
    year: int = Query(..., description="Year for the monthly summary"),
    month: int = Query(..., ge=1, le=12, description="Month for the summary (1-12)"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Get comprehensive stats for a specific month."""
    try:
        start_date = date(year, month, 1)
        
        # Calculate last day of the month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        end_date = next_month - timedelta(days=1)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date: {str(e)}"
        )
    
    time_range = StatsTimeRange(
        start_date=start_date,
        end_date=end_date,
        period=TimePeriod.daily
    )
    
    return await AsyncStatsService.calculate_comprehensive_stats(
        db=db,
        user_id=current_user.id,
        time_range=time_range
    )


@router.get("/comparison", response_model=PeriodComparison)
async def get_period_comparison(
    current_unit: TimeUnit = Query(..., description="Time unit for current period"),
    current_num: int = Query(..., ge=1, le=365, description="Number of time units for current period"),
    previous_unit: TimeUnit = Query(..., description="Time unit for previous period"),
    previous_num: int = Query(..., ge=1, le=365, description="Number of time units for previous period"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user_async)
):
    """Compare statistics between two time periods."""
    current_simple_range = SimpleTimeRange(unit=current_unit, num=current_num)
    previous_simple_range = SimpleTimeRange(unit=previous_unit, num=previous_num)
    
    current_stats = await AsyncStatsService.calculate_simple_comprehensive_stats(
        db=db, user_id=current_user.id, simple_range=current_simple_range
    )
    
    # For previous period, we need to shift the time back
    end_date = date.today()
    if current_unit == TimeUnit.day:
        previous_end_date = end_date - timedelta(days=current_num)
    elif current_unit == TimeUnit.week:
        previous_end_date = end_date - timedelta(weeks=current_num)
    elif current_unit == TimeUnit.month:
        previous_end_date = end_date - timedelta(days=current_num * 30)
    else:
        previous_end_date = end_date - timedelta(days=current_num)
    
    # Calculate previous stats with shifted end date
    if previous_unit == TimeUnit.day:
        previous_start_date = previous_end_date - timedelta(days=previous_num - 1)
    elif previous_unit == TimeUnit.week:
        previous_start_date = previous_end_date - timedelta(weeks=previous_num)
    elif previous_unit == TimeUnit.month:
        previous_start_date = previous_end_date - timedelta(days=previous_num * 30)
    else:
        previous_start_date = previous_end_date - timedelta(days=previous_num)
    
    previous_time_range = StatsTimeRange(
        start_date=previous_start_date,
        end_date=previous_end_date,
        period=TimePeriod.daily
    )
    
    previous_stats = await AsyncStatsService.calculate_comprehensive_stats(
        db=db, user_id=current_user.id, time_range=previous_time_range
    )
    
    # Calculate percentage changes
    changes = {}
    insights = []
    
    # Compare key metrics
    current_avg_calories = current_stats.nutrition_overview.calorie_stats.avg_daily_calories
    previous_avg_calories = previous_stats.nutrition_overview.calorie_stats.avg_daily_calories
    
    if previous_avg_calories > 0:
        calorie_change = ((current_avg_calories - previous_avg_calories) / previous_avg_calories) * 100
        changes["avg_daily_calories"] = calorie_change
        
        if calorie_change > 10:
            insights.append(f"Calorie intake increased by {calorie_change:.1f}% compared to previous period")
        elif calorie_change < -10:
            insights.append(f"Calorie intake decreased by {abs(calorie_change):.1f}% compared to previous period")
    
    # Compare dish variety
    current_dishes = current_stats.consumption_patterns.dishes_tried_count
    previous_dishes = previous_stats.consumption_patterns.dishes_tried_count
    
    if previous_dishes > 0:
        dish_variety_change = ((current_dishes - previous_dishes) / previous_dishes) * 100
        changes["dish_variety"] = dish_variety_change
        
        if dish_variety_change > 20:
            insights.append(f"Dish variety increased by {dish_variety_change:.1f}%")
        elif dish_variety_change < -20:
            insights.append(f"Dish variety decreased by {abs(dish_variety_change):.1f}%")
    
    # Compare goal adherence
    current_adherence = current_stats.progress_stats.avg_goal_adherence
    previous_adherence = previous_stats.progress_stats.avg_goal_adherence
    
    if previous_adherence > 0:
        adherence_change = ((current_adherence - previous_adherence) / previous_adherence) * 100
        changes["goal_adherence"] = adherence_change
        
        if adherence_change > 15:
            insights.append(f"Goal adherence improved by {adherence_change:.1f}%")
        elif adherence_change < -15:
            insights.append(f"Goal adherence declined by {abs(adherence_change):.1f}%")
    
    # Prepare simplified period data
    current_period_data = {
        "avg_daily_calories": float(current_avg_calories),
        "dishes_tried": current_dishes,
        "goal_adherence": float(current_adherence)
    }
    
    previous_period_data = {
        "avg_daily_calories": float(previous_avg_calories),
        "dishes_tried": previous_dishes,
        "goal_adherence": float(previous_adherence)
    }
    
    return PeriodComparison(
        current_period=current_period_data,
        previous_period=previous_period_data,
        changes=changes,
        insights=insights
    ) 