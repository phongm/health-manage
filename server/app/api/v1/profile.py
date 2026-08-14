from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.responses import ok
from app.db.session import get_db
from app.models.user import User, UserProfile
from app.models.tracking import WeightLog
from app.schemas.profile import ProfileUpdate
from app.services.nutrition import compute_profile_targets

router = APIRouter(prefix="/profile", tags=["profile"])


def _serialize(profile: UserProfile, extra: dict | None = None) -> dict:
    nutrients = profile.target_nutrients or {}
    data = {
        "gender": profile.gender,
        "birth_year": profile.birth_year,
        "height_cm": float(profile.height_cm),
        "weight_kg": float(profile.weight_kg),
        "body_fat_pct": float(profile.body_fat_pct) if profile.body_fat_pct is not None else None,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
        "goal_rate_kg_wk": float(profile.goal_rate_kg_wk),
        "target_weight_kg": float(profile.target_weight_kg) if profile.target_weight_kg else None,
        "bmr_kcal": float(profile.bmr_kcal or 0),
        "tdee_kcal": float(profile.tdee_kcal or 0),
        "target_kcal": float(profile.target_kcal or 0),
        "target_nutrients": nutrients,
        "warnings": extra.get("warnings", []) if extra else [],
        "is_excluded": profile.is_excluded,
        "exclude_reason": profile.exclude_reason,
        "health_flags": profile.health_flags or ["none"],
        "bmi": extra.get("bmi") if extra else None,
        "profile_completed": True,
    }
    return data


@router.get("")
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(UserProfile, user.id)
    if profile is None:
        raise NotFoundError("尚未填写基础信息")
    return ok(_serialize(profile))


@router.put("")
async def put_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now_year = datetime.now(UTC).year
    computed = compute_profile_targets(
        gender=body.gender,
        birth_year=body.birth_year,
        height_cm=body.height_cm,
        weight_kg=body.weight_kg,
        activity_level=body.activity_level,
        goal=body.goal,
        goal_rate_kg_wk=body.goal_rate_kg_wk,
        now_year=now_year,
        health_flags=body.health_flags,
    )
    profile = await db.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    profile.gender = body.gender
    profile.birth_year = body.birth_year
    profile.height_cm = body.height_cm
    profile.weight_kg = body.weight_kg
    profile.body_fat_pct = body.body_fat_pct
    profile.activity_level = body.activity_level
    profile.goal = body.goal
    profile.goal_rate_kg_wk = body.goal_rate_kg_wk
    profile.target_weight_kg = body.target_weight_kg
    profile.bmr_kcal = computed["bmr_kcal"]
    profile.tdee_kcal = computed["tdee_kcal"]
    profile.target_kcal = computed["target_kcal"]
    profile.target_nutrients = computed["target_nutrients"]
    profile.is_excluded = computed["is_excluded"]
    profile.exclude_reason = computed["exclude_reason"]
    profile.health_flags = body.health_flags

    today = date.today()
    weight_row = await db.scalar(
        select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.log_date == today)
    )
    if weight_row is None:
        db.add(WeightLog(user_id=user.id, log_date=today, weight_kg=body.weight_kg))
    else:
        weight_row.weight_kg = body.weight_kg

    await db.commit()
    await db.refresh(profile)
    return ok(_serialize(profile, extra=computed))
