from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ExcludedUserError, NotFoundError, QuotaError
from app.models.food import Food, IntakeLog
from app.models.tracking import (
    Recommendation,
    RecommendationFeedback,
    UserFoodAffinity,
)
from app.models.user import UserPreference, UserProfile
from app.services.dashboard import build_dashboard
from app.services.nutrition import calc_remaining
from app.services.quota import consume_usage
from app.services.recommend.engine import (
    ENGINE_VERSION,
    RECOMMEND_DAILY_LIMIT,
    SWAP_LIMIT,
    FoodView,
    Portion,
    SelectedItem,
    UserCtx,
    build_avoid_list,
    build_meal,
    serialize_meal,
    swap_item,
)


def to_view(food: Food) -> FoodView:
    return FoodView(
        id=food.id,
        name=food.name,
        category=food.category,
        cook_method=food.cook_method,
        role_tags=food.role_tags or [],
        attr_tags=food.attr_tags or [],
        ingredient_tags=food.ingredient_tags or [],
        scene_tags=food.scene_tags or [],
        meal_tags=food.meal_tags or [],
        nutrients=food.nutrients or {},
        portions=[
            Portion(label=p.label, grams=float(p.grams), is_default=p.is_default) for p in food.portions
        ],
        popularity=food.popularity or 0,
    )


async def _load_ctx(
    db: AsyncSession,
    user_id: int,
    rec_date: date,
    meal_type: str | None,
    scene: str | None,
) -> tuple[UserCtx, UserProfile]:
    profile = await db.get(UserProfile, user_id)
    if profile is None:
        raise NotFoundError("尚未填写基础信息")
    if profile.is_excluded:
        raise ExcludedUserError()
    prefs = await db.get(UserPreference, user_id)
    dash = await build_dashboard(db, user_id, rec_date)
    meal = meal_type or dash["next_meal"]
    resolved_scene = scene
    if not resolved_scene and prefs:
        by_meal = prefs.scene_by_meal or {}
        resolved_scene = by_meal.get(meal) or prefs.scene_default
    resolved_scene = resolved_scene or "takeout"

    affinities = (
        await db.scalars(select(UserFoodAffinity).where(UserFoodAffinity.user_id == user_id))
    ).all()
    last_eaten = {row.food_id: row.last_eaten_at for row in affinities if row.last_eaten_at}
    affinity_map = {row.food_id: float(row.affinity) for row in affinities}
    logged = {k for k, v in dash["meals"].items() if v["logged"]}
    eaten_today = {item["food_id"] for item in dash["items"] if item["food_id"]}
    remaining = calc_remaining(
        dash["target"],
        dash["intake"],
        today_exercise_kcal=float(dash["exercise"]["kcal_burned"] or 0),
    )
    ctx = UserCtx(
        goal=profile.goal,
        allergens=list(prefs.allergens or []) if prefs else [],
        avoid_ingredients=list(prefs.avoid_ingredients or []) if prefs else [],
        avoid_categories=list(prefs.avoid_categories or []) if prefs else [],
        diet_type=prefs.diet_type if prefs else "omnivore",
        spice_level=int(prefs.spice_level) if prefs else 2,
        scene=resolved_scene,
        meal_type=meal,
        rec_date=rec_date,
        target=dash["target"],
        today_intake=dash["intake"],
        remaining=remaining,
        logged_meals=logged - {meal},
        eaten_today=eaten_today,
        last_eaten=last_eaten,
        affinity=affinity_map,
    )
    return ctx, profile


async def _catalog(db: AsyncSession) -> list[FoodView]:
    foods = (
        await db.scalars(select(Food).options(selectinload(Food.portions)).where(Food.review_status == 1))
    ).all()
    return [to_view(food) for food in foods]


async def _persist(db: AsyncSession, user_id: int, ctx: UserCtx, items: list[SelectedItem], context: dict, swaps: int) -> dict:
    payload = serialize_meal(items, ctx, context, swaps)
    rec = Recommendation(
        user_id=user_id,
        rec_date=ctx.rec_date,
        meal_type=ctx.meal_type,
        scene=ctx.scene,
        items=payload["items"],
        context=context,
        version=ENGINE_VERSION,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    payload["rec_id"] = rec.id
    return payload


async def _generate(db: AsyncSession, user_id: int, rec_date: date, meal_type: str | None, scene: str | None) -> dict:
    ctx, _ = await _load_ctx(db, user_id, rec_date, meal_type, scene)
    items, context = build_meal(await _catalog(db), ctx)
    return await _persist(db, user_id, ctx, items, context, SWAP_LIMIT)


async def create_recommendation(db: AsyncSession, user_id: int, rec_date: date, meal_type: str | None, scene: str | None) -> dict:
    today_count = await db.scalar(
        select(func.count()).where(
            Recommendation.user_id == user_id,
            Recommendation.rec_date == rec_date,
        )
    )
    if (today_count or 0) >= RECOMMEND_DAILY_LIMIT:
        raise QuotaError("今日推荐次数已用完，明天再来或升级后可继续获取推荐")
    return await _generate(db, user_id, rec_date, meal_type, scene)


async def create_plan(db: AsyncSession, user_id: int, start: date, days: int, scene: str | None) -> dict:
    await consume_usage(db, user_id, "recommend_plan", 1, "今日多日食谱次数已用完")
    days = min(max(days, 1), 3)
    plan = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        meals = []
        for meal in ("breakfast", "lunch", "dinner"):
            rec = await _generate(db, user_id, day, meal, scene)
            meals.append(rec)
        plan.append({"date": day.isoformat(), "meals": meals})
    return {"days": plan}


async def swap_recommendation(db: AsyncSession, user_id: int, rec_id: int, food_id: int, reason: str) -> dict:
    rec = await db.scalar(
        select(Recommendation).where(Recommendation.id == rec_id, Recommendation.user_id == user_id)
    )
    if rec is None:
        raise NotFoundError("推荐不存在")
    swap_count = await db.scalar(
        select(func.count()).where(
            RecommendationFeedback.rec_id == rec_id,
            RecommendationFeedback.action == "swap",
        )
    )
    used = swap_count or 0
    if used >= SWAP_LIMIT:
        raise QuotaError("本餐换一换次数已用完。后续可开通会员不限次替换")
    ctx, _ = await _load_ctx(db, user_id, rec.rec_date, rec.meal_type, rec.scene)
    catalog = await _catalog(db)
    food_map = {f.id: f for f in catalog}
    current = []
    for item in rec.items:
        food = food_map.get(item["food_id"])
        if food is None:
            continue
        current.append(
            SelectedItem(
                food=food,
                role=item.get("role") or "protein",
                grams=float(item["grams"]),
                portion_label=item.get("portion_label") or "",
                nutrients=item.get("nutrients") or {},
                score=0,
                swappable=item.get("swappable", True),
            )
        )
    try:
        updated = swap_item(catalog, ctx, current, food_id, reason)
    except ValueError as exc:
        raise NotFoundError("暂无合适的替换") from exc

    db.add(
        RecommendationFeedback(
            user_id=user_id, rec_id=rec_id, food_id=food_id, action="swap", reason=reason
        )
    )
    if reason == "dont_like":
        await _bump_affinity(db, user_id, food_id, delta=-0.3, dislike=True)

    items_payload = serialize_meal(updated, ctx, rec.context or {}, SWAP_LIMIT - used - 1)
    rec.items = items_payload["items"]
    rec.context = {**(rec.context or {}), "last_swap": {"food_id": food_id, "reason": reason}}
    await db.commit()
    items_payload["rec_id"] = rec.id
    return items_payload


async def save_feedback(db: AsyncSession, user_id: int, rec_id: int, action: str, food_ids: list[int]) -> None:
    rec = await db.scalar(
        select(Recommendation).where(Recommendation.id == rec_id, Recommendation.user_id == user_id)
    )
    if rec is None:
        raise NotFoundError("推荐不存在")
    for food_id in food_ids or [None]:
        db.add(
            RecommendationFeedback(
                user_id=user_id, rec_id=rec_id, food_id=food_id, action=action
            )
        )
        if action == "accept" and food_id:
            await _bump_affinity(db, user_id, food_id, delta=0.15, accept=True)
        if action == "dislike" and food_id:
            await _bump_affinity(db, user_id, food_id, delta=-0.3, dislike=True)
    await db.commit()


async def _bump_affinity(db, user_id, food_id, delta, accept=False, dislike=False):
    row = await db.get(UserFoodAffinity, (user_id, food_id))
    if row is None:
        row = UserFoodAffinity(user_id=user_id, food_id=food_id)
        db.add(row)
        await db.flush()
    row.affinity = max(-1.0, min(1.0, float(row.affinity or 0) + delta))
    if accept:
        row.accept_count += 1
    if dislike:
        row.dislike_count += 1


async def avoid_list(db: AsyncSession, user_id: int, rec_date: date) -> list[dict]:
    ctx, _ = await _load_ctx(db, user_id, rec_date, None, None)
    return build_avoid_list(ctx)
