from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.responses import ok
from app.db.session import get_db
from app.models.user import User, UserPreference
from app.schemas.profile import PreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


def _serialize(prefs: UserPreference) -> dict:
    return {
        "allergens": prefs.allergens or [],
        "avoid_ingredients": prefs.avoid_ingredients or [],
        "avoid_categories": prefs.avoid_categories or [],
        "diet_type": prefs.diet_type,
        "spice_level": prefs.spice_level,
        "scene_default": prefs.scene_default,
        "scene_by_meal": prefs.scene_by_meal,
    }


@router.get("")
async def get_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.get(UserPreference, user.id)
    if prefs is None:
        return ok(
            {
                "allergens": [],
                "avoid_ingredients": [],
                "avoid_categories": [],
                "diet_type": "omnivore",
                "spice_level": 2,
                "scene_default": "takeout",
                "scene_by_meal": None,
            }
        )
    return ok(_serialize(prefs))


@router.put("")
async def put_preferences(
    body: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await db.get(UserPreference, user.id)
    if prefs is None:
        prefs = UserPreference(user_id=user.id)
        db.add(prefs)

    prefs.allergens = body.allergens
    prefs.avoid_ingredients = body.avoid_ingredients
    prefs.avoid_categories = body.avoid_categories
    prefs.diet_type = body.diet_type
    prefs.spice_level = body.spice_level
    prefs.scene_default = body.scene_default
    prefs.scene_by_meal = body.scene_by_meal

    await db.commit()
    await db.refresh(prefs)
    return ok(_serialize(prefs))
