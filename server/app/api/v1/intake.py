from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.responses import ok
from app.db.session import get_db
from app.models.food import Food, IntakeLog
from app.models.tracking import DeletedRecord, UserFoodAffinity
from app.models.user import User
from app.schemas.food import IntakeCreate
from app.services.dashboard import build_dashboard
from app.services.nutrition import scale_nutrients
from app.services.recommend.service import save_feedback

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("")
async def create_intake(
    body: IntakeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    food_ids = [item.food_id for item in body.items]
    foods = (
        await db.scalars(
            select(Food).options(selectinload(Food.portions)).where(Food.id.in_(food_ids), Food.review_status == 1)
        )
    ).all()
    food_map = {food.id: food for food in foods}
    missing = set(food_ids) - set(food_map)
    if missing:
        raise NotFoundError("部分食物不存在")

    created_ids: list[int] = []
    for item in body.items:
        food = food_map[item.food_id]
        snapshot = scale_nutrients(food.nutrients, item.grams)
        log = IntakeLog(
            user_id=user.id,
            log_date=body.log_date,
            meal_type=body.meal_type,
            food_id=food.id,
            food_name=food.name,
            grams=item.grams,
            portion_label=item.portion_label,
            nutrients_snapshot=snapshot,
            input_source=body.input_source,
            from_rec_id=body.from_rec_id,
        )
        db.add(log)
        await db.flush()
        created_ids.append(log.id)
        food.popularity += 1
        await _bump_eat(db, user.id, food.id, body.log_date)

    await db.commit()
    if body.from_rec_id:
        try:
            await save_feedback(db, user.id, body.from_rec_id, "accept", food_ids)
        except Exception:
            pass
    today = await build_dashboard(db, user.id, body.log_date)
    return ok({"created_ids": created_ids, "today": today})


@router.get("")
async def list_intake(
    date: date = Query(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs = (
        await db.scalars(
            select(IntakeLog)
            .where(IntakeLog.user_id == user.id, IntakeLog.log_date == date)
            .order_by(IntakeLog.logged_at.asc())
        )
    ).all()
    return ok(
        {
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
            ]
        }
    )


@router.delete("/{intake_id}")
async def delete_intake(
    intake_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    log = await db.scalar(select(IntakeLog).where(IntakeLog.id == intake_id, IntakeLog.user_id == user.id))
    if log is None:
        raise NotFoundError("记录不存在")
    log_date = log.log_date
    db.add(DeletedRecord(user_id=user.id, entity="intake_logs", entity_id=log.id))
    await db.delete(log)
    await db.commit()
    today = await build_dashboard(db, user.id, log_date)
    return ok({"today": today})


async def _bump_eat(db: AsyncSession, user_id: int, food_id: int, log_date: date) -> None:
    row = await db.get(UserFoodAffinity, (user_id, food_id))
    if row is None:
        row = UserFoodAffinity(user_id=user_id, food_id=food_id)
        db.add(row)
        await db.flush()
    row.eat_count = int(row.eat_count or 0) + 1
    row.last_eaten_at = log_date
    row.affinity = max(-1.0, min(1.0, float(row.affinity or 0) + 0.05))
