from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.models.user import User
from app.services.recommend.service import (
    avoid_list,
    create_plan,
    create_recommendation,
    save_feedback,
    swap_recommendation,
)

router = APIRouter(tags=["recommend"])


class RecommendIn(BaseModel):
    date: date
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"] | None = None
    scene: Literal["takeout", "canteen", "homecook"] | None = None


class SwapIn(BaseModel):
    food_id: int
    reason: Literal["not_available", "dont_like", "too_much", "other"] = "other"


class FeedbackIn(BaseModel):
    action: Literal["accept", "ignore", "dislike"]
    food_ids: list[int] = Field(default_factory=list)


class PlanIn(BaseModel):
    start: date
    days: int = Field(default=3, ge=1, le=3)
    scene: Literal["takeout", "canteen", "homecook"] | None = None


@router.post("/recommend")
async def recommend(body: RecommendIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await create_recommendation(db, user.id, body.date, body.meal_type, body.scene))


@router.post("/recommend/plan")
async def recommend_plan(body: PlanIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await create_plan(db, user.id, body.start, body.days, body.scene))


@router.post("/recommend/{rec_id}/swap")
async def swap(rec_id: int, body: SwapIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return ok(await swap_recommendation(db, user.id, rec_id, body.food_id, body.reason))


@router.post("/recommend/{rec_id}/feedback")
async def feedback(
    rec_id: int, body: FeedbackIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await save_feedback(db, user.id, rec_id, body.action, body.food_ids)
    return ok({"ok": True})


@router.get("/avoid-list")
async def get_avoid_list(
    date: date, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return ok({"items": await avoid_list(db, user.id, date)})
