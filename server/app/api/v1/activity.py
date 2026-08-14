from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.responses import ok
from app.db.session import get_db
from app.models.tracking import DeletedRecord, Exercise, ExerciseLog, WeightLog
from app.models.user import User, UserProfile
from app.services.dashboard import build_dashboard
from app.services.nutrition import EXERCISE_CREDIT_RATIO

router = APIRouter(tags=["activity"])


class WeightIn(BaseModel):
    log_date: date
    weight_kg: float = Field(gt=30, lt=300)
    body_fat_pct: float | None = Field(default=None, ge=3, le=70)


class ExerciseIn(BaseModel):
    log_date: date
    exercise_id: int
    duration_min: int = Field(ge=1, le=600)
    intensity: Literal[1, 2, 3] = 2


def _ma7(logs: list[WeightLog]) -> list[dict]:
    by_date = {row.log_date: float(row.weight_kg) for row in logs}
    dates = sorted(by_date)
    out = []
    for i, d in enumerate(dates):
        window = [by_date[x] for x in dates[max(0, i - 6) : i + 1]]
        out.append({"log_date": d.isoformat(), "weight_kg": round(sum(window) / len(window), 1)})
    return out


@router.get("/weight")
async def get_weight(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    date_to = date_to or date.today()
    date_from = date_from or (date_to - timedelta(days=89))
    logs = (
        await db.scalars(
            select(WeightLog)
            .where(WeightLog.user_id == user.id, WeightLog.log_date >= date_from, WeightLog.log_date <= date_to)
            .order_by(WeightLog.log_date.asc())
        )
    ).all()
    ma = _ma7(list(logs))
    trend = None
    if len(ma) >= 8:
        trend = round(ma[-1]["weight_kg"] - ma[-8]["weight_kg"], 2)
    elif len(ma) >= 2:
        days = max((date.fromisoformat(ma[-1]["log_date"]) - date.fromisoformat(ma[0]["log_date"])).days, 1)
        trend = round((ma[-1]["weight_kg"] - ma[0]["weight_kg"]) * 7 / days, 2)
    return ok(
        {
            "logs": [{"log_date": r.log_date.isoformat(), "weight_kg": float(r.weight_kg)} for r in logs],
            "ma7": ma,
            "trend_kg_per_week": trend,
        }
    )


@router.post("/weight")
async def put_weight(body: WeightIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(
        select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.log_date == body.log_date)
    )
    if row is None:
        row = WeightLog(user_id=user.id, log_date=body.log_date)
        db.add(row)
    row.weight_kg = body.weight_kg
    row.body_fat_pct = body.body_fat_pct
    profile = await db.get(UserProfile, user.id)
    if profile:
        profile.weight_kg = body.weight_kg
    await db.commit()
    return ok({"log_date": body.log_date.isoformat(), "weight_kg": body.weight_kg})


@router.get("/exercises")
async def list_exercises(_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Exercise).order_by(Exercise.id.asc()))).all()
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "met": [float(r.met_low), float(r.met_mid), float(r.met_high)],
                }
                for r in rows
            ]
        }
    )


@router.post("/exercise")
async def create_exercise(
    body: ExerciseIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    exercise = await db.get(Exercise, body.exercise_id)
    if exercise is None:
        raise NotFoundError("运动类型不存在")
    profile = await db.get(UserProfile, user.id)
    weight = float(profile.weight_kg) if profile else 60
    met = {1: float(exercise.met_low), 2: float(exercise.met_mid), 3: float(exercise.met_high)}[body.intensity]
    kcal = round(met * weight * (body.duration_min / 60), 1)
    log = ExerciseLog(
        user_id=user.id,
        log_date=body.log_date,
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        duration_min=body.duration_min,
        intensity=body.intensity,
        kcal_burned=kcal,
    )
    db.add(log)
    await db.commit()
    today = await build_dashboard(db, user.id, body.log_date)
    return ok({"id": log.id, "kcal_burned": kcal, "credited_kcal": round(kcal * EXERCISE_CREDIT_RATIO, 1), "today": today})


@router.get("/exercise")
async def list_exercise_logs(
    log_date: date = Query(alias="date"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.scalars(
            select(ExerciseLog).where(ExerciseLog.user_id == user.id, ExerciseLog.log_date == log_date)
        )
    ).all()
    return ok(
        {
            "items": [
                {
                    "id": r.id,
                    "name": r.exercise_name,
                    "duration_min": r.duration_min,
                    "intensity": r.intensity,
                    "kcal_burned": float(r.kcal_burned),
                }
                for r in rows
            ]
        }
    )


@router.delete("/exercise/{log_id}")
async def delete_exercise(
    log_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    row = await db.scalar(select(ExerciseLog).where(ExerciseLog.id == log_id, ExerciseLog.user_id == user.id))
    if row is None:
        raise NotFoundError("记录不存在")
    log_date = row.log_date
    db.add(DeletedRecord(user_id=user.id, entity="exercise_logs", entity_id=row.id))
    await db.delete(row)
    await db.commit()
    return ok({"today": await build_dashboard(db, user.id, log_date)})
