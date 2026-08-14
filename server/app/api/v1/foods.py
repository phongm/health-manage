from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.exceptions import AppError
from app.core.responses import ok
from app.db.session import get_db
from app.models.food import Food
from app.models.tracking import FoodContribution
from app.models.user import User
from app.services.dashboard import load_food_with_portions

router = APIRouter(prefix="/foods", tags=["foods"])


def serialize_food(food: Food) -> dict:
    portions = sorted(food.portions, key=lambda p: (not p.is_default, p.sort_order))
    return {
        "food_id": food.id,
        "name": food.name,
        "category": food.category,
        "nutrients_per_100g": food.nutrients,
        "portions": [
            {"label": p.label, "grams": float(p.grams), "is_default": p.is_default} for p in portions
        ],
        "role_tags": food.role_tags or [],
        "scene_tags": food.scene_tags or [],
    }


@router.get("/search")
async def search_foods(
    q: str = Query(min_length=1, max_length=32),
    scene: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q.strip()}%"
    stmt = (
        select(Food)
        .options(selectinload(Food.portions))
        .where(
            Food.review_status == 1,
            or_(
                Food.name.ilike(pattern),
                Food.code.ilike(pattern),
                func.array_to_string(Food.aliases, ",").ilike(pattern),
            ),
        )
    )
    if scene:
        stmt = stmt.where(Food.scene_tags.any(scene))
    stmt = stmt.order_by(Food.popularity.desc(), Food.id.asc()).limit(limit)
    foods = (await db.scalars(stmt)).all()
    return ok({"items": [serialize_food(food) for food in foods]})


@router.get("/hot")
async def hot_foods(
    scene: str | None = None,
    limit: int = Query(default=50, ge=1, le=300),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Food).options(selectinload(Food.portions)).where(Food.review_status == 1)
    if scene:
        stmt = stmt.where(Food.scene_tags.any(scene))
    stmt = stmt.order_by(Food.popularity.desc(), Food.id.asc()).limit(limit)
    foods = (await db.scalars(stmt)).all()
    return ok({"items": [serialize_food(food) for food in foods]})


class ContributeIn(BaseModel):
    barcode: str | None = None
    name: str | None = None
    image_file_id: str | None = None
    image_url: str | None = None


@router.post("/contribute")
async def contribute(body: ContributeIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not body.barcode and not (body.name or "").strip():
        raise AppError(1001, "请至少提供条码或食物名称", 400)
    row = FoodContribution(
        user_id=user.id,
        barcode=body.barcode,
        name=body.name,
        image_url=body.image_url or body.image_file_id,
        status=0,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ok({"id": row.id, "status": 0, "message": "已提交，审核通过后才会进入食物库"})


@router.get("/{food_id}")
async def get_food(
    food_id: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    food = await load_food_with_portions(db, food_id)
    return ok(serialize_food(food))
