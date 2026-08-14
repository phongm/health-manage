from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.models.food import Food, IntakeLog
from app.models.tracking import ClientOp, DeletedRecord, ExerciseLog, WeightLog
from app.models.user import User, UserPreference, UserProfile
from app.services.nutrition import sum_nutrients
from app.services.report import calc_achievement, calc_micros, calc_structure

router = APIRouter(tags=["report"])


@router.get("/report/weekly")
async def weekly_report(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    end = date.today()
    start = end - timedelta(days=6)
    profile = await db.get(UserProfile, user.id)
    target = (profile.target_nutrients if profile else None) or {}
    logs = (
        await db.scalars(
            select(IntakeLog).where(
                IntakeLog.user_id == user.id, IntakeLog.log_date >= start, IntakeLog.log_date <= end
            )
        )
    ).all()
    by_day: dict[date, list] = {}
    for log in logs:
        by_day.setdefault(log.log_date, []).append(log.nutrients_snapshot or {})
    days = []
    for offset in range(7):
        d = start + timedelta(days=offset)
        intake = sum_nutrients(by_day.get(d, []))
        days.append({"date": d.isoformat(), "intake": intake, "logged": d in by_day})
    logged_days = [d for d in days if d["logged"]]
    avg = sum_nutrients([d["intake"] for d in logged_days]) if logged_days else {}
    if logged_days:
        avg = {k: round(v / len(logged_days), 1) for k, v in avg.items()}
    weights = (
        await db.scalars(
            select(WeightLog)
            .where(WeightLog.user_id == user.id, WeightLog.log_date >= start, WeightLog.log_date <= end)
            .order_by(WeightLog.log_date)
        )
    ).all()
    food_counts: dict[str, int] = {}
    for log in logs:
        food_counts[log.food_name] = food_counts.get(log.food_name, 0) + 1
    top_foods = sorted(food_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    food_ids = [log.food_id for log in logs if log.food_id]
    category_counts: dict[str, int] = {}
    if food_ids:
        foods = (await db.scalars(select(Food).where(Food.id.in_(food_ids)))).all()
        cat_map = {food.id: food.category for food in foods}
        for log in logs:
            cat = cat_map.get(log.food_id) or "other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
    return ok(
        {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "logged_days": len(logged_days),
            "target": target,
            "avg_intake": avg,
            "days": days,
            "achievement": calc_achievement(avg, target),
            "micros": calc_micros(avg, target),
            "structure": calc_structure(category_counts),
            "weight": {
                "first": float(weights[0].weight_kg) if weights else None,
                "last": float(weights[-1].weight_kg) if weights else None,
                "delta": round(float(weights[-1].weight_kg) - float(weights[0].weight_kg), 1)
                if len(weights) >= 2
                else None,
            },
            "top_foods": [{"name": n, "count": c} for n, c in top_foods],
            "disclaimer": "以上为记录与统计参考，不是医疗建议。",
        }
    )


@router.get("/export")
async def export_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await db.get(UserProfile, user.id)
    prefs = await db.get(UserPreference, user.id)
    intake = (await db.scalars(select(IntakeLog).where(IntakeLog.user_id == user.id))).all()
    weights = (await db.scalars(select(WeightLog).where(WeightLog.user_id == user.id))).all()
    exercises = (await db.scalars(select(ExerciseLog).where(ExerciseLog.user_id == user.id))).all()
    return ok(
        {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": {
                "gender": profile.gender,
                "birth_year": profile.birth_year,
                "height_cm": float(profile.height_cm),
                "weight_kg": float(profile.weight_kg),
                "goal": profile.goal,
                "target_kcal": float(profile.target_kcal or 0),
            }
            if profile
            else None,
            "preferences": {
                "allergens": prefs.allergens,
                "avoid_ingredients": prefs.avoid_ingredients,
                "scene_default": prefs.scene_default,
            }
            if prefs
            else None,
            "intake_logs": [
                {
                    "date": r.log_date.isoformat(),
                    "meal_type": r.meal_type,
                    "food_name": r.food_name,
                    "grams": float(r.grams),
                    "nutrients": r.nutrients_snapshot,
                }
                for r in intake
            ],
            "weight_logs": [{"date": r.log_date.isoformat(), "weight_kg": float(r.weight_kg)} for r in weights],
            "exercise_logs": [
                {
                    "date": r.log_date.isoformat(),
                    "name": r.exercise_name,
                    "duration_min": r.duration_min,
                    "kcal_burned": float(r.kcal_burned),
                }
                for r in exercises
            ],
        }
    )


@router.get("/sync")
async def sync_pull(
    since: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = since or datetime(2000, 1, 1)
    profile = await db.get(UserProfile, user.id)
    prefs = await db.get(UserPreference, user.id)
    intake = (
        await db.scalars(select(IntakeLog).where(IntakeLog.user_id == user.id, IntakeLog.created_at >= since))
    ).all()
    exercises = (
        await db.scalars(select(ExerciseLog).where(ExerciseLog.user_id == user.id, ExerciseLog.logged_at >= since))
    ).all()
    weights = (
        await db.scalars(select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.created_at >= since))
    ).all()
    deleted = (
        await db.scalars(
            select(DeletedRecord).where(DeletedRecord.user_id == user.id, DeletedRecord.deleted_at >= since)
        )
    ).all()
    grouped: dict[str, list[int]] = {}
    for row in deleted:
        grouped.setdefault(row.entity, []).append(row.entity_id)
    return ok(
        {
            "server_time": datetime.now(UTC).isoformat(),
            "profile": {
                "weight_kg": float(profile.weight_kg),
                "target_kcal": float(profile.target_kcal or 0),
                "is_excluded": profile.is_excluded,
            }
            if profile
            else None,
            "preferences": {
                "allergens": prefs.allergens or [],
                "avoid_ingredients": prefs.avoid_ingredients or [],
                "scene_default": prefs.scene_default,
                "scene_by_meal": prefs.scene_by_meal,
            }
            if prefs
            else None,
            "intake_logs": [
                {
                    "id": r.id,
                    "date": r.log_date.isoformat(),
                    "meal_type": r.meal_type,
                    "food_id": r.food_id,
                    "food_name": r.food_name,
                    "grams": float(r.grams),
                    "portion_label": r.portion_label,
                    "nutrients": r.nutrients_snapshot,
                }
                for r in intake
            ],
            "exercise_logs": [
                {
                    "id": r.id,
                    "date": r.log_date.isoformat(),
                    "name": r.exercise_name,
                    "duration_min": r.duration_min,
                    "kcal_burned": float(r.kcal_burned),
                }
                for r in exercises
            ],
            "weight_logs": [
                {"id": r.id, "date": r.log_date.isoformat(), "weight_kg": float(r.weight_kg)} for r in weights
            ],
            "deleted": {
                "intake_logs": grouped.get("intake_logs", []),
                "weight_logs": grouped.get("weight_logs", []),
                "exercise_logs": grouped.get("exercise_logs", []),
            },
        }
    )


class SyncOpIn(BaseModel):
    client_op_id: str = Field(min_length=8, max_length=64)
    type: str
    payload: dict = Field(default_factory=dict)


class SyncBatchIn(BaseModel):
    ops: list[SyncOpIn] = Field(default_factory=list, max_length=50)


@router.post("/sync/batch")
async def sync_batch(body: SyncBatchIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    results = []
    for op in body.ops:
        existing = await db.get(ClientOp, op.client_op_id)
        if existing and existing.user_id == user.id:
            results.append({"client_op_id": op.client_op_id, "idempotent": True, "result": existing.result})
            continue
        try:
            result = await _apply_sync_op(db, user.id, op.type, op.payload)
        except AppError as exc:
            results.append({"client_op_id": op.client_op_id, "error": {"code": exc.code, "message": exc.message}})
            continue
        db.add(ClientOp(client_op_id=op.client_op_id, user_id=user.id, kind=op.type, result=result))
        results.append({"client_op_id": op.client_op_id, "idempotent": False, "result": result})
    await db.commit()
    return ok({"results": results})


async def _apply_sync_op(db: AsyncSession, user_id: int, kind: str, payload: dict) -> dict:
    from sqlalchemy.orm import selectinload

    from app.models.food import Food
    from app.schemas.food import IntakeCreate
    from app.services.nutrition import scale_nutrients

    if kind == "intake.create":
        body = IntakeCreate.model_validate(payload)
        food_ids = [item.food_id for item in body.items]
        foods = (
            await db.scalars(
                select(Food).options(selectinload(Food.portions)).where(Food.id.in_(food_ids), Food.review_status == 1)
            )
        ).all()
        food_map = {food.id: food for food in foods}
        created_ids = []
        for item in body.items:
            food = food_map[item.food_id]
            log = IntakeLog(
                user_id=user_id,
                log_date=body.log_date,
                meal_type=body.meal_type,
                food_id=food.id,
                food_name=food.name,
                grams=item.grams,
                portion_label=item.portion_label,
                nutrients_snapshot=scale_nutrients(food.nutrients, item.grams),
                input_source=body.input_source,
                from_rec_id=body.from_rec_id,
            )
            db.add(log)
            await db.flush()
            created_ids.append(log.id)
        return {"created_ids": created_ids}

    if kind == "intake.delete":
        intake_id = int(payload["id"])
        log = await db.scalar(select(IntakeLog).where(IntakeLog.id == intake_id, IntakeLog.user_id == user_id))
        if log:
            db.add(DeletedRecord(user_id=user_id, entity="intake_logs", entity_id=log.id))
            await db.delete(log)
        return {"deleted": intake_id}

    if kind == "weight.upsert":
        log_date = date.fromisoformat(payload["log_date"])
        row = await db.scalar(select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.log_date == log_date))
        if row is None:
            row = WeightLog(user_id=user_id, log_date=log_date)
            db.add(row)
        row.weight_kg = payload["weight_kg"]
        return {"log_date": log_date.isoformat(), "weight_kg": payload["weight_kg"]}

    raise AppError(1001, f"不支持的同步操作: {kind}", 400)
