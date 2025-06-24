from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TimePeriod(str, Enum):
    """Time period options for stats queries."""
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class TimeUnit(str, Enum):
    """Time unit options for simplified stats queries."""
    hour = "hour"
    day = "day"
    week = "week"
    month = "month"
    year = "year"


class StatsTimeRange(BaseModel):
    """Schema for time range queries."""
    start_date: date = Field(..., description="Start date for stats calculation")
    end_date: date = Field(..., description="End date for stats calculation")
    period: TimePeriod = Field(default=TimePeriod.daily, description="Granularity of data points")


class SimpleTimeRange(BaseModel):
    """Schema for simplified time range queries using unit and count."""
    unit: TimeUnit = Field(..., description="Time unit (hour, day, week, month, year)")
    num: int = Field(..., ge=1, le=365, description="Number of time units (1-365)")


# Nutrition Analytics Schemas
class CalorieDataPoint(BaseModel):
    """Single data point for calorie tracking."""
    timestamp: datetime
    calories: Decimal
    goal_calories: Optional[Decimal] = None
    deficit_surplus: Optional[Decimal] = None


class CalorieStats(BaseModel):
    """Calorie intake statistics."""
    data_points: List[CalorieDataPoint]
    avg_daily_calories: Decimal
    total_calories: Decimal
    peak_consumption_hour: Optional[int] = None
    days_above_goal: int
    days_below_goal: int


class MacronutrientBreakdown(BaseModel):
    """Macronutrient distribution."""
    carbs_percentage: Decimal
    protein_percentage: Decimal
    fats_percentage: Decimal
    carbs_grams: Decimal
    protein_grams: Decimal
    fats_grams: Decimal
    fiber_grams: Decimal
    sugar_grams: Decimal
    saturated_fats_grams: Decimal
    unsaturated_fats_grams: Decimal


class MacronutrientDataPoint(BaseModel):
    """Daily macronutrient data point."""
    date: date
    carbs_g: Decimal
    protein_g: Decimal
    fats_g: Decimal
    fiber_g: Decimal
    sugar_g: Decimal


class MacronutrientStats(BaseModel):
    """Macronutrient statistics over time."""
    current_breakdown: MacronutrientBreakdown
    data_points: List[MacronutrientDataPoint]
    avg_breakdown: MacronutrientBreakdown


class MicronutrientValue(BaseModel):
    """Single micronutrient value with daily value percentage."""
    amount: Decimal
    unit: str
    daily_value_percentage: Optional[Decimal] = None


class MicronutrientStats(BaseModel):
    """Micronutrient intake statistics."""
    vitamins: Dict[str, MicronutrientValue] = Field(
        default_factory=dict,
        description="Vitamin intake (A, B1, B2, B3, B5, B6, B9, B12, C, D, E, K)"
    )
    minerals: Dict[str, MicronutrientValue] = Field(
        default_factory=dict,
        description="Mineral intake (calcium, iron, potassium, sodium, zinc, magnesium)"
    )
    deficiency_alerts: List[str] = Field(default_factory=list)


# Food Consumption Pattern Schemas
class DishFrequency(BaseModel):
    """Dish consumption frequency."""
    dish_id: int
    dish_name: str
    cuisine: Optional[str] = None
    consumption_count: int
    last_consumed: datetime
    avg_portion_size: Decimal


class CuisineDistribution(BaseModel):
    """Cuisine consumption distribution."""
    cuisine: str
    consumption_count: int
    percentage: Decimal
    calories_consumed: Decimal


class EatingPatternDataPoint(BaseModel):
    """Eating pattern data point."""
    hour: int
    intake_count: int
    avg_calories: Decimal


class ConsumptionPatternStats(BaseModel):
    """Food consumption pattern statistics."""
    top_dishes: List[DishFrequency]
    cuisine_distribution: List[CuisineDistribution]
    eating_patterns: List[EatingPatternDataPoint]
    dishes_tried_count: int
    unique_cuisines_count: int
    avg_meals_per_day: Decimal
    weekend_vs_weekday_ratio: Decimal


# Health and Progress Schemas
class HealthMetricDataPoint(BaseModel):
    """Health metric data point."""
    date: date
    weight_kg: Optional[Decimal] = None
    bmi: Optional[Decimal] = None
    calories_consumed: Decimal
    goal_adherence_percentage: Decimal


class ProgressStats(BaseModel):
    """Health and fitness progress statistics."""
    health_metrics: List[HealthMetricDataPoint]
    weight_trend: Optional[str] = None  # "increasing", "decreasing", "stable"
    avg_goal_adherence: Decimal
    dietary_restriction_compliance: Decimal
    best_nutrition_day: Optional[date] = None
    improvement_trend: Optional[str] = None


# Advanced Analytics Schemas
class CorrelationInsight(BaseModel):
    """Correlation analysis insight."""
    factor1: str
    factor2: str
    correlation_strength: Decimal
    description: str


class PredictiveInsight(BaseModel):
    """Predictive analytics insight."""
    metric: str
    predicted_value: Decimal
    confidence_level: Decimal
    time_horizon_days: int
    recommendation: str


class AdvancedAnalytics(BaseModel):
    """Advanced analytics and insights."""
    correlations: List[CorrelationInsight]
    predictions: List[PredictiveInsight]
    optimization_suggestions: List[str]


# Comprehensive Stats Response
class NutritionOverview(BaseModel):
    """Complete nutrition overview."""
    calorie_stats: CalorieStats
    macronutrient_stats: MacronutrientStats
    micronutrient_stats: MicronutrientStats


class ComprehensiveStats(BaseModel):
    """Complete user statistics response."""
    time_range: StatsTimeRange
    nutrition_overview: NutritionOverview
    consumption_patterns: ConsumptionPatternStats
    progress_stats: ProgressStats
    advanced_analytics: Optional[AdvancedAnalytics] = None
    generated_at: datetime = Field(default_factory=datetime.now)


# Quick Stats for Dashboard
class QuickStats(BaseModel):
    """Quick stats for dashboard display."""
    today_calories: Decimal
    today_goal_percentage: Decimal
    weekly_avg_calories: Decimal
    top_cuisine_this_week: Optional[str] = None
    total_dishes_tried: int
    current_streak_days: int
    weight_change_this_month: Optional[Decimal] = None


# Comparison Stats
class PeriodComparison(BaseModel):
    """Comparison between two time periods."""
    current_period: Dict[str, Any]
    previous_period: Dict[str, Any]
    changes: Dict[str, Decimal]  # percentage changes
    insights: List[str]


# Export Stats Schema
class StatsExportData(BaseModel):
    """Data structure for stats export."""
    user_id: int
    export_date: datetime
    time_range: StatsTimeRange
    data: ComprehensiveStats
    format: str = Field(default="json", description="Export format (json, csv, pdf)") 