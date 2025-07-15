from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, extract, and_, case, desc, select
from collections import defaultdict
import statistics

from app.models.intake import Intake
from app.models.dish import Dish
from app.models.user_profile import UserProfile
from app.models.health_history import HealthHistory
from app.schemas.stats import (
    StatsTimeRange, TimePeriod, SimpleTimeRange, TimeUnit, CalorieStats, CalorieDataPoint,
    MacronutrientStats, MacronutrientBreakdown, MacronutrientDataPoint,
    MicronutrientStats, MicronutrientValue, ConsumptionPatternStats,
    DishFrequency, CuisineDistribution, EatingPatternDataPoint,
    ProgressStats, HealthMetricDataPoint, NutritionOverview,
    ComprehensiveStats, QuickStats, PeriodComparison, AdvancedAnalytics,
    CorrelationInsight, PredictiveInsight
)


class StatsService:
    """Service for calculating comprehensive nutrition and health statistics."""

    # Daily Value Reference Amounts (in appropriate units)
    DAILY_VALUES = {
        'vit_a_mcg': 900,
        'vit_b1_mg': 1.2,
        'vit_b2_mg': 1.3,
        'vit_b3_mg': 16,
        'vit_b5_mg': 5,
        'vit_b6_mg': 1.7,
        'vit_b9_mcg': 400,
        'vit_b12_mcg': 2.4,
        'vit_c_mg': 90,
        'vit_d_mcg': 20,
        'vit_e_mg': 15,
        'vit_k_mcg': 120,
        'calcium_mg': 1000,
        'iron_mg': 18,
        'potassium_mg': 4700,
        'sodium_mg': 2300,
        'zinc_mg': 11,
        'magnesium_mg': 400
    }

    @staticmethod
    def convert_simple_to_full_range(simple_range: SimpleTimeRange) -> StatsTimeRange:
        """Convert SimpleTimeRange to StatsTimeRange with proper dates and period."""
        end_date = date.today()
        
        # Calculate start date based on unit and num
        if simple_range.unit == TimeUnit.hour:
            start_datetime = datetime.now() - timedelta(hours=simple_range.num)
            start_date = start_datetime.date()
            period = TimePeriod.hourly
        elif simple_range.unit == TimeUnit.day:
            start_date = end_date - timedelta(days=simple_range.num - 1)  # -1 to include today
            period = TimePeriod.daily
        elif simple_range.unit == TimeUnit.week:
            start_date = end_date - timedelta(weeks=simple_range.num)
            period = TimePeriod.weekly
        elif simple_range.unit == TimeUnit.month:
            # Approximate months as 30 days
            start_date = end_date - timedelta(days=simple_range.num * 30)
            period = TimePeriod.monthly
        elif simple_range.unit == TimeUnit.year:
            start_date = end_date - timedelta(days=simple_range.num * 365)
            period = TimePeriod.yearly
        else:
            # Default fallback
            start_date = end_date - timedelta(days=simple_range.num)
            period = TimePeriod.daily

        return StatsTimeRange(
            start_date=start_date,
            end_date=end_date,
            period=period
        )

    @staticmethod
    async def _get_user_goal_calories(db: AsyncSession, user_id: int) -> Decimal:
        """Get user's daily calorie goal from their profile and health data."""
        # profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        # modified for asyncio
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
        if not profile:
            return Decimal("2000")  # Default goal
        
        # Basic calculation: BMR * activity factor
        # This is simplified - in reality you'd use more sophisticated calculations
        age = (date.today() - profile.date_of_birth).days / 365.25
        
        if profile.gender.value == 'male':
            bmr = 88.362 + (13.397 * float(profile.weight_kg)) + (4.799 * float(profile.height_cm)) - (5.677 * age)
        else:
            bmr = 447.593 + (9.247 * float(profile.weight_kg)) + (3.098 * float(profile.height_cm)) - (4.330 * age)
        
        # Assuming moderate activity level (1.55 multiplier)
        daily_calories = bmr * 1.55
        return Decimal(str(round(daily_calories)))

    @staticmethod
    def _aggregate_intakes_by_period(
        intakes: List[Intake], 
        period: TimePeriod,
        start_date: date,
        end_date: date
    ) -> Dict[str, List[Intake]]:
        """Group intakes by time period."""
        grouped = defaultdict(list)
        
        for intake in intakes:
            intake_date = intake.intake_time.date()
            
            if period == TimePeriod.hourly:
                key = intake.intake_time.strftime("%Y-%m-%d %H:00")
            elif period == TimePeriod.daily:
                key = intake_date.strftime("%Y-%m-%d")
            elif period == TimePeriod.weekly:
                # Get Monday of the week
                monday = intake_date - timedelta(days=intake_date.weekday())
                key = monday.strftime("%Y-%m-%d")
            elif period == TimePeriod.monthly:
                key = intake_date.strftime("%Y-%m")
            else:  # yearly
                key = intake_date.strftime("%Y")
            
            grouped[key].append(intake)
        
        return grouped

    @staticmethod
    async def calculate_calorie_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> CalorieStats:
        """Calculate comprehensive calorie statistics."""
        # Get intakes in the specified range
        # intakes = db.query(Intake).join(Dish).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= time_range.start_date,
        #         func.date(Intake.intake_time) <= time_range.end_date
        #     )
        # ).all()
        # modified for asyncio
        intakes = (await db.execute(
            select(Intake).options(joinedload(Intake.dish)).where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= time_range.start_date,
                    func.date(Intake.intake_time) <= time_range.end_date
                )
            )
        )).scalars().all()

        goal_calories = await StatsService._get_user_goal_calories(db, user_id)
        grouped_intakes = StatsService._aggregate_intakes_by_period(
            intakes, time_range.period, time_range.start_date, time_range.end_date
        )

        data_points = []
        total_calories = Decimal("0")
        daily_calories = []
        hourly_consumption = defaultdict(list)
        days_above_goal = 0
        days_below_goal = 0

        for period_key, period_intakes in grouped_intakes.items():
            period_calories = Decimal("0")
            
            for intake in period_intakes:
                if intake.dish and intake.dish.calories:
                    portion_multiplier = intake.portion_size or Decimal("1.0")
                    calories = intake.dish.calories * portion_multiplier
                    period_calories += calories
                    
                    # Track hourly consumption for peak analysis
                    hour = intake.intake_time.hour
                    hourly_consumption[hour].append(float(calories))

            total_calories += period_calories
            
            # For daily periods, track goal adherence
            if time_range.period == TimePeriod.daily:
                daily_calories.append(float(period_calories))
                if period_calories > goal_calories:
                    days_above_goal += 1
                elif period_calories < goal_calories:
                    days_below_goal += 1

            # Create data point
            if time_range.period == TimePeriod.hourly:
                timestamp = datetime.strptime(period_key, "%Y-%m-%d %H:00")
            else:
                timestamp = datetime.strptime(period_key, "%Y-%m-%d")
            
            deficit_surplus = period_calories - goal_calories if time_range.period == TimePeriod.daily else None
            
            data_points.append(CalorieDataPoint(
                timestamp=timestamp,
                calories=period_calories,
                goal_calories=goal_calories,
                deficit_surplus=deficit_surplus
            ))

        # Calculate averages and peak hour
        avg_daily_calories = Decimal(str(statistics.mean(daily_calories))) if daily_calories else Decimal("0")
        
        peak_hour = None
        if hourly_consumption:
            hourly_totals = {hour: sum(calories) for hour, calories in hourly_consumption.items()}
            peak_hour = max(hourly_totals, key=hourly_totals.get)

        return CalorieStats(
            data_points=data_points,
            avg_daily_calories=avg_daily_calories,
            total_calories=total_calories,
            peak_consumption_hour=peak_hour,
            days_above_goal=days_above_goal,
            days_below_goal=days_below_goal
        )

    @staticmethod
    async def calculate_macronutrient_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> MacronutrientStats:
        """Calculate macronutrient distribution and trends."""
        # intakes = db.query(Intake).join(Dish).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= time_range.start_date,
        #         func.date(Intake.intake_time) <= time_range.end_date
        #     )
        # ).all()
        # modified for asyncio
        intakes = (await db.execute(
            select(Intake).options(joinedload(Intake.dish)).where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= time_range.start_date,
                    func.date(Intake.intake_time) <= time_range.end_date
                )
            )
        )).scalars().all()

        # Calculate current breakdown
        total_carbs = total_protein = total_fats = Decimal("0")
        total_fiber = total_sugar = Decimal("0")
        total_sat_fats = total_unsat_fats = Decimal("0")
        
        daily_data = defaultdict(lambda: {
            'carbs': Decimal("0"), 'protein': Decimal("0"), 'fats': Decimal("0"),
            'fiber': Decimal("0"), 'sugar': Decimal("0")
        })

        for intake in intakes:
            if intake.dish:
                portion = intake.portion_size or Decimal("1.0")
                intake_date = intake.intake_time.date()
                
                if intake.dish.carbs_g:
                    carbs = intake.dish.carbs_g * portion
                    total_carbs += carbs
                    daily_data[intake_date]['carbs'] += carbs
                
                if intake.dish.protein_g:
                    protein = intake.dish.protein_g * portion
                    total_protein += protein
                    daily_data[intake_date]['protein'] += protein
                
                if intake.dish.fats_g:
                    fats = intake.dish.fats_g * portion
                    total_fats += fats
                    daily_data[intake_date]['fats'] += fats
                
                if intake.dish.fiber_g:
                    fiber = intake.dish.fiber_g * portion
                    total_fiber += fiber
                    daily_data[intake_date]['fiber'] += fiber
                
                if intake.dish.sugar_g:
                    sugar = intake.dish.sugar_g * portion
                    total_sugar += sugar
                    daily_data[intake_date]['sugar'] += sugar
                
                if intake.dish.sat_fats_g:
                    total_sat_fats += intake.dish.sat_fats_g * portion
                
                if intake.dish.unsat_fats_g:
                    total_unsat_fats += intake.dish.unsat_fats_g * portion

        # Calculate percentages
        total_macros = total_carbs + total_protein + total_fats
        if total_macros > 0:
            carbs_pct = (total_carbs / total_macros) * 100
            protein_pct = (total_protein / total_macros) * 100
            fats_pct = (total_fats / total_macros) * 100
        else:
            carbs_pct = protein_pct = fats_pct = Decimal("0")

        current_breakdown = MacronutrientBreakdown(
            carbs_percentage=carbs_pct,
            protein_percentage=protein_pct,
            fats_percentage=fats_pct,
            carbs_grams=total_carbs,
            protein_grams=total_protein,
            fats_grams=total_fats,
            fiber_grams=total_fiber,
            sugar_grams=total_sugar,
            saturated_fats_grams=total_sat_fats,
            unsaturated_fats_grams=total_unsat_fats
        )

        # Create daily data points
        data_points = []
        for date_key in sorted(daily_data.keys()):
            data_points.append(MacronutrientDataPoint(
                date=date_key,
                carbs_g=daily_data[date_key]['carbs'],
                protein_g=daily_data[date_key]['protein'],
                fats_g=daily_data[date_key]['fats'],
                fiber_g=daily_data[date_key]['fiber'],
                sugar_g=daily_data[date_key]['sugar']
            ))

        # Calculate average breakdown (simplified as current for now)
        avg_breakdown = current_breakdown

        return MacronutrientStats(
            current_breakdown=current_breakdown,
            data_points=data_points,
            avg_breakdown=avg_breakdown
        )

    @staticmethod
    async def calculate_micronutrient_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> MicronutrientStats:
        """Calculate micronutrient intake and deficiency alerts."""
        # intakes = db.query(Intake).join(Dish).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= time_range.start_date,
        #         func.date(Intake.intake_time) <= time_range.end_date
        #     )
        # ).all()
        # modified for asyncio
        intakes = (await db.execute(
            select(Intake).options(joinedload(Intake.dish)).where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= time_range.start_date,
                    func.date(Intake.intake_time) <= time_range.end_date
                )
            )
        )).scalars().all()

        # Initialize totals
        micronutrient_totals = {nutrient: Decimal("0") for nutrient in StatsService.DAILY_VALUES.keys()}

        for intake in intakes:
            if intake.dish:
                portion = intake.portion_size or Decimal("1.0")
                
                for nutrient in micronutrient_totals.keys():
                    value = getattr(intake.dish, nutrient, None)
                    if value:
                        micronutrient_totals[nutrient] += value * portion

        # Calculate daily value percentages and create response
        vitamins = {}
        minerals = {}
        deficiency_alerts = []

        vitamin_nutrients = [n for n in micronutrient_totals.keys() if n.startswith('vit_')]
        mineral_nutrients = [n for n in micronutrient_totals.keys() if not n.startswith('vit_')]

        for nutrient, total in micronutrient_totals.items():
            daily_value = StatsService.DAILY_VALUES[nutrient]
            dv_percentage = (total / Decimal(str(daily_value))) * 100
            
            # Determine unit
            if 'mcg' in nutrient:
                unit = 'mcg'
            elif 'mg' in nutrient:
                unit = 'mg'
            else:
                unit = 'mg'  # default

            micronutrient_value = MicronutrientValue(
                amount=total,
                unit=unit,
                daily_value_percentage=dv_percentage
            )

            # Categorize into vitamins or minerals
            if nutrient in vitamin_nutrients:
                vitamin_name = nutrient.replace('_', ' ').replace('vit ', 'Vitamin ').upper()
                vitamins[vitamin_name] = micronutrient_value
            else:
                mineral_name = nutrient.replace('_mg', '').replace('_mcg', '').capitalize()
                minerals[mineral_name] = micronutrient_value

            # Check for deficiencies (less than 70% of daily value)
            if dv_percentage < 70:
                nutrient_display = nutrient.replace('_', ' ').replace('vit ', 'Vitamin ').title()
                deficiency_alerts.append(f"Low {nutrient_display} intake: {dv_percentage:.1f}% of daily value")

        return MicronutrientStats(
            vitamins=vitamins,
            minerals=minerals,
            deficiency_alerts=deficiency_alerts
        )

    @staticmethod
    async def calculate_consumption_pattern_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> ConsumptionPatternStats:
        """Calculate food consumption pattern statistics."""
        # intakes = db.query(Intake).join(Dish).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= time_range.start_date,
        #         func.date(Intake.intake_time) <= time_range.end_date
        #     )
        # ).all()
        # modified for asyncio
        intakes = (await db.execute(
            select(Intake).options(joinedload(Intake.dish)).where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= time_range.start_date,
                    func.date(Intake.intake_time) <= time_range.end_date
                )
            )
        )).scalars().all()

        # Dish frequency analysis
        dish_stats = defaultdict(lambda: {
            'count': 0, 'total_portion': Decimal("0"), 'last_consumed': None, 'name': '', 'cuisine': None
        })
        
        cuisine_stats = defaultdict(lambda: {'count': 0, 'calories': Decimal("0")})
        hourly_patterns = defaultdict(lambda: {'count': 0, 'calories': Decimal("0")})
        unique_dishes = set()
        unique_cuisines = set()
        
        weekend_intakes = 0
        weekday_intakes = 0

        for intake in intakes:
            if intake.dish:
                dish_id = intake.dish.id
                unique_dishes.add(dish_id)
                
                # Dish frequency
                dish_stats[dish_id]['count'] += 1
                dish_stats[dish_id]['total_portion'] += intake.portion_size or Decimal("1.0")
                dish_stats[dish_id]['name'] = intake.dish.name
                dish_stats[dish_id]['cuisine'] = intake.dish.cuisine
                
                if not dish_stats[dish_id]['last_consumed'] or intake.intake_time > dish_stats[dish_id]['last_consumed']:
                    dish_stats[dish_id]['last_consumed'] = intake.intake_time

                # Cuisine analysis
                if intake.dish.cuisine:
                    cuisine = intake.dish.cuisine
                    unique_cuisines.add(cuisine)
                    cuisine_stats[cuisine]['count'] += 1
                    
                    if intake.dish.calories:
                        portion = intake.portion_size or Decimal("1.0")
                        cuisine_stats[cuisine]['calories'] += intake.dish.calories * portion

                # Hourly patterns
                hour = intake.intake_time.hour
                hourly_patterns[hour]['count'] += 1
                if intake.dish.calories:
                    portion = intake.portion_size or Decimal("1.0")
                    hourly_patterns[hour]['calories'] += intake.dish.calories * portion

                # Weekend vs weekday
                if intake.intake_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
                    weekend_intakes += 1
                else:
                    weekday_intakes += 1

        # Create top dishes list
        top_dishes = []
        for dish_id, stats in sorted(dish_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            avg_portion = stats['total_portion'] / stats['count'] if stats['count'] > 0 else Decimal("1.0")
            top_dishes.append(DishFrequency(
                dish_id=dish_id,
                dish_name=stats['name'],
                cuisine=stats['cuisine'],
                consumption_count=stats['count'],
                last_consumed=stats['last_consumed'],
                avg_portion_size=avg_portion
            ))

        # Create cuisine distribution
        total_cuisine_count = sum(stats['count'] for stats in cuisine_stats.values())
        cuisine_distribution = []
        for cuisine, stats in sorted(cuisine_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            percentage = (Decimal(str(stats['count'])) / Decimal(str(total_cuisine_count))) * 100 if total_cuisine_count > 0 else Decimal("0")
            cuisine_distribution.append(CuisineDistribution(
                cuisine=cuisine,
                consumption_count=stats['count'],
                percentage=percentage,
                calories_consumed=stats['calories']
            ))

        # Create eating patterns
        eating_patterns = []
        for hour in range(24):
            count = hourly_patterns[hour]['count']
            avg_calories = hourly_patterns[hour]['calories'] / count if count > 0 else Decimal("0")
            eating_patterns.append(EatingPatternDataPoint(
                hour=hour,
                intake_count=count,
                avg_calories=avg_calories
            ))

        # Calculate ratios and averages
        total_days = (time_range.end_date - time_range.start_date).days + 1
        avg_meals_per_day = Decimal(str(len(intakes))) / Decimal(str(total_days)) if total_days > 0 else Decimal("0")
        
        weekend_vs_weekday_ratio = Decimal("0")
        if weekday_intakes > 0:
            weekend_vs_weekday_ratio = Decimal(str(weekend_intakes)) / Decimal(str(weekday_intakes))

        return ConsumptionPatternStats(
            top_dishes=top_dishes,
            cuisine_distribution=cuisine_distribution,
            eating_patterns=eating_patterns,
            dishes_tried_count=len(unique_dishes),
            unique_cuisines_count=len(unique_cuisines),
            avg_meals_per_day=avg_meals_per_day,
            weekend_vs_weekday_ratio=weekend_vs_weekday_ratio
        )

    @staticmethod
    async def calculate_progress_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> ProgressStats:
        """Calculate health and fitness progress statistics."""
        # Get health history data
        # health_data = db.query(HealthHistory).filter(
        #     and_(
        #         HealthHistory.user_id == user_id,
        #         func.date(HealthHistory.change_timestamp) >= time_range.start_date,
        #         func.date(HealthHistory.change_timestamp) <= time_range.end_date
        #     )
        # ).order_by(HealthHistory.change_timestamp).all()
        # modified for asyncio
        health_data = (await db.execute(
            select(HealthHistory).where(
                and_(
                    HealthHistory.user_id == user_id,
                    func.date(HealthHistory.change_timestamp) >= time_range.start_date,
                    func.date(HealthHistory.change_timestamp) <= time_range.end_date
                )
            ).order_by(HealthHistory.change_timestamp)
        )).scalars().all()

        # Get user profile for goal tracking
        # profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        # modified for asyncio
        profile = (await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))).scalars().first()
        goal_calories = await StatsService._get_user_goal_calories(db, user_id)

        # Get daily calorie intakes
        # daily_intakes = db.query(
        #     func.date(Intake.intake_time).label('date'),
        #     func.sum(Dish.calories * Intake.portion_size).label('total_calories')
        # ).join(Dish).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= time_range.start_date,
        #         func.date(Intake.intake_time) <= time_range.end_date
        #     )
        # ).group_by(func.date(Intake.intake_time)).all()
        # modified for asyncio
        daily_intakes = (await db.execute(
            select(
                func.date(Intake.intake_time).label('date'),
                func.sum(Dish.calories * Intake.portion_size).label('total_calories')
            ).select_from(Intake).join(Dish).where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= time_range.start_date,
                    func.date(Intake.intake_time) <= time_range.end_date
                )
            ).group_by(func.date(Intake.intake_time))
        )).all()

        # Create health metrics data points
        health_metrics = []
        goal_adherences = []
        best_day_score = 0
        best_day = None

        # Create a mapping of dates to calorie intakes
        calorie_by_date = {intake.date: intake.total_calories or Decimal("0") for intake in daily_intakes}

        for health_record in health_data:
            record_date = health_record.change_timestamp.date()
            calories_consumed = calorie_by_date.get(record_date, Decimal("0"))
            
            # Calculate goal adherence (closer to goal = better score)
            if goal_calories > 0:
                goal_adherence = 100 - abs(float(calories_consumed - goal_calories)) / float(goal_calories) * 100
                goal_adherence = max(0, goal_adherence)  # Ensure non-negative
            else:
                goal_adherence = 0

            goal_adherences.append(goal_adherence)

            # Track best nutrition day
            if goal_adherence > best_day_score:
                best_day_score = goal_adherence
                best_day = record_date

            # Calculate BMI if height is available
            bmi = None
            if profile and profile.height_cm and health_record.weight_kg:
                height_m = float(profile.height_cm) / 100
                bmi = Decimal(str(float(health_record.weight_kg) / (height_m ** 2)))

            health_metrics.append(HealthMetricDataPoint(
                date=record_date,
                weight_kg=health_record.weight_kg,
                bmi=bmi,
                calories_consumed=calories_consumed,
                goal_adherence_percentage=Decimal(str(goal_adherence))
            ))

        # Determine weight trend
        weight_trend = None
        if len(health_data) >= 2:
            first_weight = health_data[0].weight_kg
            last_weight = health_data[-1].weight_kg
            if first_weight and last_weight:
                if last_weight > first_weight * Decimal("1.02"):  # 2% increase
                    weight_trend = "increasing"
                elif last_weight < first_weight * Decimal("0.98"):  # 2% decrease
                    weight_trend = "decreasing"
                else:
                    weight_trend = "stable"

        # Calculate average goal adherence
        avg_goal_adherence = Decimal(str(statistics.mean(goal_adherences))) if goal_adherences else Decimal("0")

        # Calculate dietary restriction compliance (simplified)
        dietary_restriction_compliance = Decimal("85.0")  # Placeholder - would need more complex logic

        # Determine improvement trend
        improvement_trend = None
        if len(goal_adherences) >= 7:  # Need at least a week of data
            recent_avg = statistics.mean(goal_adherences[-7:])
            older_avg = statistics.mean(goal_adherences[:-7])
            if recent_avg > older_avg * 1.1:
                improvement_trend = "improving"
            elif recent_avg < older_avg * 0.9:
                improvement_trend = "declining"
            else:
                improvement_trend = "stable"

        return ProgressStats(
            health_metrics=health_metrics,
            weight_trend=weight_trend,
            avg_goal_adherence=avg_goal_adherence,
            dietary_restriction_compliance=dietary_restriction_compliance,
            best_nutrition_day=best_day,
            improvement_trend=improvement_trend
        )

    @staticmethod
    async def calculate_comprehensive_stats(
        db: AsyncSession, 
        user_id: int, 
        time_range: StatsTimeRange
    ) -> ComprehensiveStats:
        """Calculate all statistics for comprehensive overview."""
        # Calculate all individual stats
        calorie_stats = await StatsService.calculate_calorie_stats(db, user_id, time_range)
        macronutrient_stats = await StatsService.calculate_macronutrient_stats(db, user_id, time_range)
        micronutrient_stats = await StatsService.calculate_micronutrient_stats(db, user_id, time_range)
        consumption_patterns = await StatsService.calculate_consumption_pattern_stats(db, user_id, time_range)
        progress_stats = await StatsService.calculate_progress_stats(db, user_id, time_range)

        # Create nutrition overview
        nutrition_overview = NutritionOverview(
            calorie_stats=calorie_stats,
            macronutrient_stats=macronutrient_stats,
            micronutrient_stats=micronutrient_stats
        )

        # Generate advanced analytics (simplified for now)
        advanced_analytics = StatsService._generate_advanced_analytics(
            calorie_stats, macronutrient_stats, consumption_patterns, progress_stats
        )

        return ComprehensiveStats(
            time_range=time_range,
            nutrition_overview=nutrition_overview,
            consumption_patterns=consumption_patterns,
            progress_stats=progress_stats,
            advanced_analytics=advanced_analytics
        )

    @staticmethod
    def _generate_advanced_analytics(
        calorie_stats: CalorieStats,
        macro_stats: MacronutrientStats,
        consumption_stats: ConsumptionPatternStats,
        progress_stats: ProgressStats
    ) -> AdvancedAnalytics:
        """Generate advanced analytics and insights."""
        correlations = []
        predictions = []
        suggestions = []

        # Correlation analysis (simplified examples)
        if calorie_stats.peak_consumption_hour and consumption_stats.avg_meals_per_day > 0:
            correlations.append(CorrelationInsight(
                factor1="Peak eating hour",
                factor2="Total daily calories",
                correlation_strength=Decimal("0.65"),
                description=f"Peak consumption occurs at {calorie_stats.peak_consumption_hour}:00, suggesting a correlation with daily calorie intake patterns."
            ))

        # Predictive insights (simplified examples)
        if progress_stats.improvement_trend == "improving":
            predictions.append(PredictiveInsight(
                metric="Goal adherence",
                predicted_value=progress_stats.avg_goal_adherence + Decimal("10"),
                confidence_level=Decimal("75"),
                time_horizon_days=30,
                recommendation="Continue current eating patterns to maintain improvement trend."
            ))

        # Optimization suggestions
        if macro_stats.current_breakdown.protein_percentage < 20:
            suggestions.append("Consider increasing protein intake to 20-30% of total calories for better satiety and muscle maintenance.")

        if calorie_stats.peak_consumption_hour and calorie_stats.peak_consumption_hour > 20:
            suggestions.append("Try eating your largest meal earlier in the day to improve metabolism and sleep quality.")

        if consumption_stats.unique_cuisines_count < 5:
            suggestions.append("Diversify your cuisine choices to ensure a wider range of nutrients and prevent dietary boredom.")

        return AdvancedAnalytics(
            correlations=correlations,
            predictions=predictions,
            optimization_suggestions=suggestions
        )

    @staticmethod
    async def calculate_quick_stats(db: AsyncSession, user_id: int) -> QuickStats:
        """Calculate quick stats for dashboard display."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Today's calories
        # today_calories = db.query(
        #     func.sum(Dish.calories * Intake.portion_size)
        # ).select_from(Intake).join(Dish, Intake.dish_id == Dish.id).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) == today
        #     )
        # ).scalar() or Decimal("0")
        # modified for asyncio
        today_calories_result = await db.execute(
            select(func.sum(Dish.calories * Intake.portion_size))
            .select_from(Intake).join(Dish, Intake.dish_id == Dish.id)
            .where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) == today
                )
            )
        )
        today_calories = today_calories_result.scalar() or Decimal("0")

        # Goal percentage
        goal_calories = await StatsService._get_user_goal_calories(db, user_id)
        today_goal_percentage = (today_calories / goal_calories * 100) if goal_calories > 0 else Decimal("0")

        # Weekly average - simplified approach
        # weekly_intakes = db.query(
        #     func.date(Intake.intake_time).label('date'),
        #     func.sum(Dish.calories * Intake.portion_size).label('daily_calories')
        # ).select_from(Intake).join(Dish, Intake.dish_id == Dish.id).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= week_ago,
        #         func.date(Intake.intake_time) <= today
        #     )
        # ).group_by(func.date(Intake.intake_time)).all()
        # modified for asyncio
        weekly_intakes = (await db.execute(
            select(
                func.date(Intake.intake_time).label('date'),
                func.sum(Dish.calories * Intake.portion_size).label('daily_calories')
            ).select_from(Intake).join(Dish, Intake.dish_id == Dish.id)
            .where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= week_ago,
                    func.date(Intake.intake_time) <= today
                )
            ).group_by(func.date(Intake.intake_time))
        )).all()

        # Calculate average from the daily totals
        if weekly_intakes:
            daily_totals = [float(intake.daily_calories or 0) for intake in weekly_intakes]
            weekly_avg = Decimal(str(sum(daily_totals) / len(daily_totals)))
        else:
            weekly_avg = Decimal("0")

        # Top cuisine this week
        # top_cuisine = db.query(
        #     Dish.cuisine,
        #     func.count(Intake.id).label('intake_count')
        # ).select_from(Intake).join(Dish, Intake.dish_id == Dish.id).filter(
        #     and_(
        #         Intake.user_id == user_id,
        #         func.date(Intake.intake_time) >= week_ago,
        #         Dish.cuisine.isnot(None)
        #     )
        # ).group_by(Dish.cuisine).order_by(desc('intake_count')).first()
        # modified for asyncio
        top_cuisine = (await db.execute(
            select(
                Dish.cuisine,
                func.count(Intake.id).label('intake_count')
            ).select_from(Intake).join(Dish, Intake.dish_id == Dish.id)
            .where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= week_ago,
                    Dish.cuisine.isnot(None)
                )
            ).group_by(Dish.cuisine).order_by(desc('intake_count'))
        )).first()

        top_cuisine_name = top_cuisine.cuisine if top_cuisine else None

        # Total dishes tried (all time)
        # total_dishes_tried = db.query(func.count(func.distinct(Intake.dish_id))).filter(
        #     Intake.user_id == user_id
        # ).scalar() or 0
        # modified for asyncio
        total_dishes_tried_result = await db.execute(
            select(func.count(func.distinct(Intake.dish_id)))
            .where(Intake.user_id == user_id)
        )
        total_dishes_tried = total_dishes_tried_result.scalar() or 0

        # Calculate current streak (simplified - consecutive days with intakes)
        current_streak = 0
        check_date = today
        while True:
            # has_intake = db.query(Intake).filter(
            #     and_(
            #         Intake.user_id == user_id,
            #         func.date(Intake.intake_time) == check_date
            #     )
            # ).first()
            # modified for asyncio
            has_intake = (await db.execute(
                select(Intake).where(
                    and_(
                        Intake.user_id == user_id,
                        func.date(Intake.intake_time) == check_date
                    )
                )
            )).scalars().first()
            
            if has_intake:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
            
            # Limit check to prevent infinite loop
            if current_streak > 365:
                break

        # Weight change this month (requires health history)
        weight_change = None
        # recent_weight = db.query(HealthHistory.weight_kg).filter(
        #     and_(
        #         HealthHistory.user_id == user_id,
        #         func.date(HealthHistory.change_timestamp) >= month_ago
        #     )
        # ).order_by(desc(HealthHistory.change_timestamp)).first()
        # modified for asyncio
        recent_weight = (await db.execute(
            select(HealthHistory.weight_kg).where(
                and_(
                    HealthHistory.user_id == user_id,
                    func.date(HealthHistory.change_timestamp) >= month_ago
                )
            ).order_by(desc(HealthHistory.change_timestamp))
        )).first()

        # month_ago_weight = db.query(HealthHistory.weight_kg).filter(
        #     and_(
        #         HealthHistory.user_id == user_id,
        #         func.date(HealthHistory.change_timestamp) <= month_ago
        #     )
        # ).order_by(desc(HealthHistory.change_timestamp)).first()
        # modified for asyncio
        month_ago_weight = (await db.execute(
            select(HealthHistory.weight_kg).where(
                and_(
                    HealthHistory.user_id == user_id,
                    func.date(HealthHistory.change_timestamp) <= month_ago
                )
            ).order_by(desc(HealthHistory.change_timestamp))
        )).first()

        if recent_weight and month_ago_weight and recent_weight.weight_kg and month_ago_weight.weight_kg:
            weight_change = recent_weight.weight_kg - month_ago_weight.weight_kg

        return QuickStats(
            today_calories=today_calories,
            today_goal_percentage=today_goal_percentage,
            weekly_avg_calories=weekly_avg,
            top_cuisine_this_week=top_cuisine_name,
            total_dishes_tried=total_dishes_tried,
            current_streak_days=current_streak,
            weight_change_this_month=weight_change
        )

    # Simplified API methods using SimpleTimeRange
    @staticmethod
    async def calculate_simple_calorie_stats(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> CalorieStats:
        """Calculate calorie stats using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_calorie_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_macronutrient_stats(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> MacronutrientStats:
        """Calculate macronutrient stats using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_macronutrient_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_micronutrient_stats(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> MicronutrientStats:
        """Calculate micronutrient stats using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_micronutrient_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_consumption_patterns(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> ConsumptionPatternStats:
        """Calculate consumption patterns using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_consumption_pattern_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_progress_stats(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> ProgressStats:
        """Calculate progress stats using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_progress_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_comprehensive_stats(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> ComprehensiveStats:
        """Calculate comprehensive stats using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        return await StatsService.calculate_comprehensive_stats(db, user_id, time_range)

    @staticmethod
    async def calculate_simple_nutrition_overview(
        db: AsyncSession, 
        user_id: int, 
        simple_range: SimpleTimeRange
    ) -> NutritionOverview:
        """Calculate nutrition overview using simplified time range."""
        time_range = StatsService.convert_simple_to_full_range(simple_range)
        
        # Calculate individual nutrition stats
        calorie_stats = await StatsService.calculate_calorie_stats(db, user_id, time_range)
        macronutrient_stats = await StatsService.calculate_macronutrient_stats(db, user_id, time_range)
        micronutrient_stats = await StatsService.calculate_micronutrient_stats(db, user_id, time_range)
        
        return NutritionOverview(
            calorie_stats=calorie_stats,
            macronutrient_stats=macronutrient_stats,
            micronutrient_stats=micronutrient_stats
        ) 