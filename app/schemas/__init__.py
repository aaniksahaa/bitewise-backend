"""Pydantic schemas for request and response validation."""

# Dish schemas
from .dish import (
    DishBase,
    DishCreate,
    DishUpdate,
    DishResponse,
    DishListItem,
    DishListResponse
)

# Intake schemas
from .intake import (
    IntakeBase,
    IntakeCreate,
    IntakeCreateByName,
    IntakeUpdate,
    IntakeResponse,
    IntakeListItem,
    IntakeListResponse,
    IntakePeriodQuery,
    DishDetail,
    NutritionalSummary
)

# Stats schemas
from .stats import (
    TimePeriod, TimeUnit, StatsTimeRange, SimpleTimeRange,
    CalorieStats, CalorieDataPoint,
    MacronutrientStats, MacronutrientBreakdown, MacronutrientDataPoint,
    MicronutrientStats, MicronutrientValue,
    ConsumptionPatternStats, DishFrequency, CuisineDistribution, EatingPatternDataPoint,
    ProgressStats, HealthMetricDataPoint,
    NutritionOverview, ComprehensiveStats, QuickStats,
    PeriodComparison, AdvancedAnalytics, CorrelationInsight, PredictiveInsight
)

__all__ = [
    # Dish schemas
    "DishBase",
    "DishCreate", 
    "DishUpdate",
    "DishResponse",
    "DishListItem",
    "DishListResponse",
    # Intake schemas
    "IntakeBase",
    "IntakeCreate",
    "IntakeCreateByName",
    "IntakeUpdate", 
    "IntakeResponse",
    "IntakeListItem",
    "IntakeListResponse",
    "IntakePeriodQuery",
    "DishDetail",
    "NutritionalSummary",
    # Stats schemas
    "StatsTimeRange",
    "TimePeriod",
    "CalorieStats",
    "CalorieDataPoint",
    "MacronutrientStats",
    "MacronutrientBreakdown",
    "MicronutrientStats",
    "ConsumptionPatternStats",
    "ProgressStats",
    "NutritionOverview",
    "ComprehensiveStats",
    "QuickStats",
    "PeriodComparison",
] 