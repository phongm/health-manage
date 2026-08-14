from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.food import Food, IntakeLog
from app.models.tracking import ExerciseLog
from app.models.user import UserProfile
from app.services.nutrition import EXERCISE_CREDIT_RATIO, calc_remaining, next_meal, sum_nutrients
from app.services.report import MICRO_KEYS

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")


async def build_dashboard(db: AsyncSession, user_id: int, log_date: date) -> dict:
    profile = await db.get(UserProfile, user_id)
    if profile is None:
        raise NotFoundError("尚未填写基础信息")

    target = profile.target_nutrients or {"energy_kcal": float(profile.target_kcal or 0)}
    logs = (
        await db.scalars(
            select(IntakeLog)
            .where(IntakeLog.user_id == user_id, IntakeLog.log_date == log_date)
            .order_by(IntakeLog.logged_at.asc())
        )
    ).all()

    intake = sum_nutrients([log.nutrients_snapshot or {} for log in logs])
    exercises = (
        await db.scalars(
            select(ExerciseLog).where(ExerciseLog.user_id == user_id, ExerciseLog.log_date == log_date)
        )
    ).all()
    burned = sum(float(row.kcal_burned) for row in exercises)
    remaining = calc_remaining(target, intake, today_exercise_kcal=burned)

    meals: dict[str, dict] = {}
    logged: set[str] = set()
    for meal in MEAL_TYPES:
        meal_logs = [log for log in logs if log.meal_type == meal]
        kcal = sum(float((log.nutrients_snapshot or {}).get("energy_kcal") or 0) for log in meal_logs)
        meals[meal] = {"kcal": round(kcal, 1), "logged": bool(meal_logs)}
        if meal_logs:
            logged.add(meal)

    return {
        "date": log_date.isoformat(),
        "target": target,
        "intake": intake,
        "exercise": {
            "kcal_burned": round(burned, 1),
            "credited_kcal": round(burned * EXERCISE_CREDIT_RATIO, 1),
        },
        "remaining": remaining,
        "meals": meals,
        "next_meal": next_meal(logged),
        "micros": {
            key: {
                "intake": intake.get(key),
                "target": target.get(key),
                "remaining": remaining.get(key),
            }
            for key in MICRO_KEYS
            if key in target or key in intake
        },
        "items": [
            {
                "id": log.id,
                "meal_type": log.meal_type,
                "food_id": log.food_id,
                "food_name": log.food_name,
                "grams": float(log.grams),
                "portion_label": log.portion_label,
                "nutrients": log.nutrients_snapshot,
                "input_source": log.input_source,
            }
            for log in logs
        ],
    }


async def load_food_with_portions(db: AsyncSession, food_id: int) -> Food:
    food = await db.scalar(
        select(Food).options(selectinload(Food.portions)).where(Food.id == food_id, Food.review_status == 1)
    )
    if food is None:
        raise NotFoundError("食物不存在")
    return food
