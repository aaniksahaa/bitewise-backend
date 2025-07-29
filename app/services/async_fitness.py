from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.models.fitness_plan import FitnessPlan
from app.models.user_profile import UserProfile
from app.models.intake import Intake
from app.models.dish import Dish


class AsyncFitnessService:
    """Async service for fitness-related operations."""

    @staticmethod
    async def create_fitness_plan(
        db: AsyncSession,
        user_id: int,
        goal_type: str,
        target_weight_kg: Optional[float] = None,
        target_calories_per_day: Optional[int] = None,
        start_date: date = None,
        end_date: date = None
    ) -> FitnessPlan:
        """Create a new fitness plan."""
        if start_date is None:
            start_date = date.today()
        if end_date is None:
            end_date = start_date + timedelta(days=90)  # Default 3 months
        
        # Generate suggestions based on goal type
        suggestions = await AsyncFitnessService._generate_plan_suggestions(
            db, user_id, goal_type, target_weight_kg, target_calories_per_day
        )
        
        fitness_plan = FitnessPlan(
            user_id=user_id,
            goal_type=goal_type,
            target_weight_kg=Decimal(str(target_weight_kg)) if target_weight_kg else None,
            target_calories_per_day=target_calories_per_day,
            start_date=start_date,
            end_date=end_date,
            suggestions=suggestions,
            created_at=datetime.utcnow()
        )
        
        db.add(fitness_plan)
        await db.commit()
        await db.refresh(fitness_plan)
        return fitness_plan

    @staticmethod
    async def get_fitness_plan(db: AsyncSession, plan_id: int, user_id: int) -> Optional[FitnessPlan]:
        """Get a specific fitness plan."""
        result = await db.execute(
            select(FitnessPlan)
            .options(selectinload(FitnessPlan.user))
            .where(and_(FitnessPlan.id == plan_id, FitnessPlan.user_id == user_id))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_fitness_plans(
        db: AsyncSession,
        user_id: int,
        active_only: bool = False
    ) -> List[FitnessPlan]:
        """Get all fitness plans for a user."""
        query = select(FitnessPlan).where(FitnessPlan.user_id == user_id)
        
        if active_only:
            today = date.today()
            query = query.where(
                and_(
                    FitnessPlan.start_date <= today,
                    FitnessPlan.end_date >= today
                )
            )
        
        query = query.order_by(desc(FitnessPlan.created_at))
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_fitness_plan(
        db: AsyncSession,
        plan_id: int,
        user_id: int,
        goal_type: Optional[str] = None,
        target_weight_kg: Optional[float] = None,
        target_calories_per_day: Optional[int] = None,
        end_date: Optional[date] = None
    ) -> Optional[FitnessPlan]:
        """Update a fitness plan."""
        result = await db.execute(
            select(FitnessPlan).where(
                and_(FitnessPlan.id == plan_id, FitnessPlan.user_id == user_id)
            )
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            return None
        
        if goal_type is not None:
            plan.goal_type = goal_type
        if target_weight_kg is not None:
            plan.target_weight_kg = Decimal(str(target_weight_kg))
        if target_calories_per_day is not None:
            plan.target_calories_per_day = target_calories_per_day
        if end_date is not None:
            plan.end_date = end_date
        
        plan.updated_at = datetime.utcnow()
        
        # Regenerate suggestions if goal changed
        if goal_type is not None:
            plan.suggestions = await AsyncFitnessService._generate_plan_suggestions(
                db, user_id, plan.goal_type, 
                float(plan.target_weight_kg) if plan.target_weight_kg else None,
                plan.target_calories_per_day
            )
        
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def delete_fitness_plan(db: AsyncSession, plan_id: int, user_id: int) -> bool:
        """Delete a fitness plan."""
        result = await db.execute(
            select(FitnessPlan).where(
                and_(FitnessPlan.id == plan_id, FitnessPlan.user_id == user_id)
            )
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            return False
        
        await db.delete(plan)
        await db.commit()
        return True

    @staticmethod
    async def get_fitness_progress(
        db: AsyncSession,
        plan_id: int,
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get progress for a specific fitness plan."""
        # Get the fitness plan
        plan_result = await db.execute(
            select(FitnessPlan).where(
                and_(FitnessPlan.id == plan_id, FitnessPlan.user_id == user_id)
            )
        )
        plan = plan_result.scalar_one_or_none()
        
        if not plan:
            return None
        
        # Calculate days completed
        today = date.today()
        days_completed = max(0, (min(today, plan.end_date) - plan.start_date).days)
        total_days = (plan.end_date - plan.start_date).days
        
        # Get calorie consumption during plan period
        calories_result = await db.execute(
            select(func.sum(Dish.calories * Intake.portion_size))
            .select_from(Intake)
            .join(Dish)
            .where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= plan.start_date,
                    func.date(Intake.intake_time) <= min(today, plan.end_date)
                )
            )
        )
        total_calories_consumed = calories_result.scalar() or Decimal("0")
        
        # Calculate target calories for the period
        target_calories = Decimal("0")
        if plan.target_calories_per_day:
            target_calories = Decimal(str(plan.target_calories_per_day)) * Decimal(str(days_completed))
        
        # Calculate calorie deficit/surplus
        calorie_difference = float(total_calories_consumed - target_calories) if target_calories > 0 else 0
        
        # Get weight progress (simplified - would need health history integration)
        weight_progress = await AsyncFitnessService._get_weight_progress(db, user_id, plan)
        
        progress = {
            "fitness_plan_id": plan_id,
            "goal_type": plan.goal_type,
            "days_completed": days_completed,
            "total_days": total_days,
            "completion_percentage": (days_completed / total_days * 100) if total_days > 0 else 0,
            "total_calories_consumed": float(total_calories_consumed),
            "target_calories": float(target_calories),
            "calorie_difference": calorie_difference,
            "weight_progress": weight_progress,
            "plan_start_date": plan.start_date.isoformat(),
            "plan_end_date": plan.end_date.isoformat()
        }
        
        return progress

    @staticmethod
    async def _generate_plan_suggestions(
        db: AsyncSession,
        user_id: int,
        goal_type: str,
        target_weight_kg: Optional[float] = None,
        target_calories_per_day: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate personalized suggestions for a fitness plan."""
        # Get user profile for personalization
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        # Get user's favorite dishes for meal suggestions
        favorite_dishes_result = await db.execute(
            select(Dish.id, Dish.name, Dish.calories, Dish.cuisine, func.count(Intake.id).label('count'))
            .select_from(Intake)
            .join(Dish)
            .where(Intake.user_id == user_id)
            .group_by(Dish.id, Dish.name, Dish.calories, Dish.cuisine)
            .order_by(desc('count'))
            .limit(10)
        )
        favorite_dishes = favorite_dishes_result.all()
        
        suggestions = {
            "daily_meals": [],
            "exercise_recommendations": [],
            "nutrition_tips": [],
            "goal_specific_advice": []
        }
        
        # Generate meal suggestions based on goal type
        if goal_type == "weight_loss":
            # Suggest lower calorie versions of favorite dishes
            for dish in favorite_dishes[:3]:
                suggestions["daily_meals"].append({
                    "meal_type": "main",
                    "dish_id": dish.id,
                    "dish_name": dish.name,
                    "calories": float(dish.calories) if dish.calories else 0,
                    "portion_suggestion": 0.8,  # Slightly smaller portions
                    "cuisine": dish.cuisine
                })
            
            suggestions["exercise_recommendations"] = [
                "30 minutes of cardio 5 times per week",
                "Strength training 2-3 times per week",
                "Daily walks of at least 10,000 steps"
            ]
            
            suggestions["nutrition_tips"] = [
                "Focus on protein-rich foods to maintain muscle mass",
                "Include plenty of vegetables for fiber and nutrients",
                "Stay hydrated with at least 8 glasses of water daily"
            ]
            
            suggestions["goal_specific_advice"] = [
                f"Aim for a caloric deficit of 500-750 calories per day",
                "Track your progress weekly, not daily",
                "Allow for one cheat meal per week to maintain motivation"
            ]
            
        elif goal_type == "weight_gain":
            # Suggest higher calorie versions of favorite dishes
            for dish in favorite_dishes[:3]:
                suggestions["daily_meals"].append({
                    "meal_type": "main",
                    "dish_id": dish.id,
                    "dish_name": dish.name,
                    "calories": float(dish.calories) if dish.calories else 0,
                    "portion_suggestion": 1.2,  # Larger portions
                    "cuisine": dish.cuisine
                })
            
            suggestions["exercise_recommendations"] = [
                "Strength training 4-5 times per week",
                "Compound exercises (squats, deadlifts, bench press)",
                "Limit cardio to 2-3 sessions per week"
            ]
            
            suggestions["nutrition_tips"] = [
                "Eat frequent, smaller meals throughout the day",
                "Include healthy fats like nuts, avocados, and olive oil",
                "Consume protein within 30 minutes after workouts"
            ]
            
            suggestions["goal_specific_advice"] = [
                f"Aim for a caloric surplus of 300-500 calories per day",
                "Focus on progressive overload in your workouts",
                "Get adequate sleep (7-9 hours) for muscle recovery"
            ]
            
        elif goal_type == "maintenance":
            # Suggest balanced portions of favorite dishes
            for dish in favorite_dishes[:3]:
                suggestions["daily_meals"].append({
                    "meal_type": "main",
                    "dish_id": dish.id,
                    "dish_name": dish.name,
                    "calories": float(dish.calories) if dish.calories else 0,
                    "portion_suggestion": 1.0,  # Normal portions
                    "cuisine": dish.cuisine
                })
            
            suggestions["exercise_recommendations"] = [
                "Mix of cardio and strength training",
                "3-4 workout sessions per week",
                "Include flexibility and mobility work"
            ]
            
            suggestions["nutrition_tips"] = [
                "Maintain a balanced diet with all macronutrients",
                "Listen to your hunger and fullness cues",
                "Include a variety of colorful fruits and vegetables"
            ]
            
            suggestions["goal_specific_advice"] = [
                "Focus on consistency rather than perfection",
                "Monitor your energy levels and adjust as needed",
                "Celebrate non-scale victories like improved strength"
            ]
        
        return suggestions

    @staticmethod
    async def _get_weight_progress(
        db: AsyncSession,
        user_id: int,
        plan: FitnessPlan
    ) -> Dict[str, Any]:
        """Get weight progress during the fitness plan period."""
        # This would integrate with health history
        # For now, return a simplified mock response
        
        return {
            "start_weight_kg": float(plan.target_weight_kg) + 5 if plan.target_weight_kg else None,
            "current_weight_kg": float(plan.target_weight_kg) + 2 if plan.target_weight_kg else None,
            "target_weight_kg": float(plan.target_weight_kg) if plan.target_weight_kg else None,
            "weight_change_kg": -3.0 if plan.target_weight_kg else 0,
            "progress_percentage": 60.0 if plan.target_weight_kg else 0
        }

    @staticmethod
    async def get_fitness_recommendations(
        db: AsyncSession,
        user_id: int
    ) -> Dict[str, Any]:
        """Get general fitness recommendations for a user."""
        # Get user profile
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        # Get recent intake patterns
        recent_intakes_result = await db.execute(
            select(func.avg(Dish.calories * Intake.portion_size))
            .select_from(Intake)
            .join(Dish)
            .where(
                and_(
                    Intake.user_id == user_id,
                    func.date(Intake.intake_time) >= date.today() - timedelta(days=7)
                )
            )
        )
        avg_daily_calories = recent_intakes_result.scalar() or Decimal("0")
        
        recommendations = {
            "suggested_goal": "maintenance",
            "recommended_daily_calories": 2000,
            "activity_level": "moderate",
            "recommendations": [
                "Based on your recent intake patterns, consider setting a fitness goal",
                "Track your meals consistently for better insights",
                "Consider adding regular physical activity to your routine"
            ]
        }
        
        if profile:
            # Calculate BMI and provide recommendations
            if profile.height_cm and profile.weight_kg:
                height_m = float(profile.height_cm) / 100
                bmi = float(profile.weight_kg) / (height_m ** 2)
                
                if bmi < 18.5:
                    recommendations["suggested_goal"] = "weight_gain"
                    recommendations["recommendations"].append("Your BMI suggests you might benefit from healthy weight gain")
                elif bmi > 25:
                    recommendations["suggested_goal"] = "weight_loss"
                    recommendations["recommendations"].append("Your BMI suggests you might benefit from weight management")
                else:
                    recommendations["suggested_goal"] = "maintenance"
                    recommendations["recommendations"].append("Your BMI is in a healthy range - focus on maintenance")
        
        return recommendations