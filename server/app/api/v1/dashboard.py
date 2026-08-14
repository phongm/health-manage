from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.models.food import Food
from app.models.user import User
from app.schemas.food import ParseTextIn
from app.services.dashboard import build_dashboard
from app.services.parse_text import CatalogFood, parse_food_text
from app.services.quota import IMAGE_PARSE_DAILY_LIMIT, consume_usage

dashboard_router = APIRouter(tags=["dashboard"])
parse_router = APIRouter(prefix="/parse", tags=["parse"])


async def _catalog(db: AsyncSession) -> list[CatalogFood]:
    foods = (
        await db.scalars(select(Food).options(selectinload(Food.portions)).where(Food.review_status == 1))
    ).all()
    return [
        CatalogFood(
            id=food.id,
            name=food.name,
            aliases=food.aliases or [],
            portions=[(p.label, float(p.grams), p.is_default) for p in food.portions],
        )
        for food in foods
    ]


@dashboard_router.get("/dashboard")
async def get_dashboard(
    date: date = Query(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(await build_dashboard(db, user.id, date))


@parse_router.post("/text")
async def parse_text(
    body: ParseTextIn,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return ok(parse_food_text(body.text, await _catalog(db)))


class ParseImageIn(BaseModel):
    hint: str | None = None
    image_file_id: str | None = None


@parse_router.post("/image")
async def parse_image(
    body: ParseImageIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not (body.hint or "").strip():
        raise AppError(
            5001,
            "拍照识别需配置视觉模型。可先在备注里写食物名称，我们按文字解析并请你确认份量。",
            400,
        )
    await consume_usage(
        db,
        user.id,
        "parse_image",
        IMAGE_PARSE_DAILY_LIMIT,
        "今日拍照解析次数已用完",
    )
    result = parse_food_text(body.hint or "", await _catalog(db))
    for item in result["items"]:
        item["need_confirm"] = True
        item["confidence"] = min(float(item.get("confidence") or 0.8), 0.72)
    result["parser"] = "image_hint"
    return ok(result)
