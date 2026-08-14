"""导入种子食物库。用法：在 server/ 目录执行  uv run python -m app.tools.seed_foods"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.food import Food, FoodPortion, FoodRecipe
from app.models.tracking import Exercise
from app.services.nutrition import compute_recipe_nutrients
from data.seed_foods import INGREDIENTS, RECIPES

EXERCISES = [
    {"name": "步行", "aliases": ["走路", "散步"], "category": "cardio", "met_low": 3.5, "met_mid": 4.3, "met_high": 5.0},
    {"name": "跑步", "aliases": ["慢跑"], "category": "cardio", "met_low": 7.0, "met_mid": 9.8, "met_high": 11.5},
    {"name": "骑车", "aliases": ["自行车"], "category": "cardio", "met_low": 4.0, "met_mid": 6.8, "met_high": 10.0},
    {"name": "游泳", "aliases": [], "category": "cardio", "met_low": 5.0, "met_mid": 7.0, "met_high": 10.0},
    {"name": "力量训练", "aliases": ["健身", "举铁"], "category": "strength", "met_low": 3.5, "met_mid": 5.0, "met_high": 6.0},
    {"name": "瑜伽", "aliases": [], "category": "daily", "met_low": 2.5, "met_mid": 3.0, "met_high": 4.0},
    {"name": "跳绳", "aliases": [], "category": "cardio", "met_low": 8.0, "met_mid": 10.0, "met_high": 12.0},
]


def _apply_food_fields(food: Food, payload: dict, nutrients: dict) -> None:
    food.name = payload["name"]
    food.aliases = payload.get("aliases") or []
    food.category = payload["category"]
    food.scene_tags = payload.get("scene_tags") or []
    food.meal_tags = payload.get("meal_tags") or []
    food.cook_method = payload.get("cook_method")
    food.role_tags = payload.get("role_tags") or []
    food.attr_tags = payload.get("attr_tags") or []
    food.ingredient_tags = payload.get("ingredient_tags") or []
    food.nutrients = nutrients
    food.source = payload.get("source", "self_built")
    food.source_ref = payload.get("source_ref")
    food.review_status = 1


async def _upsert_food(db, payload: dict, nutrients: dict) -> Food:
    food = await db.scalar(select(Food).options(selectinload(Food.portions)).where(Food.code == payload["code"]))
    if food is None:
        food = Food(
            code=payload["code"],
            name=payload["name"],
            category=payload["category"],
            nutrients=nutrients,
            source=payload.get("source", "self_built"),
        )
        db.add(food)
        await db.flush()
    _apply_food_fields(food, payload, nutrients)
    food.portions.clear()
    for idx, portion in enumerate(payload.get("portions") or []):
        food.portions.append(
            FoodPortion(
                label=portion["label"],
                grams=portion["grams"],
                is_default=bool(portion.get("is_default")),
                sort_order=idx,
            )
        )
    return food


async def seed() -> None:
    async with SessionLocal() as db:
        by_code: dict[str, Food] = {}
        for payload in INGREDIENTS:
            food = await _upsert_food(db, payload, payload["nutrients"])
            by_code[food.code] = food
        await db.flush()

        for recipe in RECIPES:
            pairs = []
            for item in recipe["ingredients"]:
                ingredient = by_code[item["code"]]
                pairs.append((ingredient.nutrients, float(item["grams"])))
            nutrients, total_grams = compute_recipe_nutrients(pairs)
            payload = {**recipe, "source": "self_built", "source_ref": "recipe_from_seed_ingredients"}
            dish = await _upsert_food(db, payload, nutrients)
            by_code[dish.code] = dish
            await db.flush()
            await db.execute(delete(FoodRecipe).where(FoodRecipe.dish_food_id == dish.id))
            for item in recipe["ingredients"]:
                db.add(
                    FoodRecipe(
                        dish_food_id=dish.id,
                        ingredient_id=by_code[item["code"]].id,
                        grams=item["grams"],
                    )
                )
            if not recipe.get("portions"):
                dish.portions.append(
                    FoodPortion(label="一份", grams=total_grams, is_default=True, sort_order=0)
                )
        await db.commit()
        print(f"seeded {len(by_code)} foods")

        for payload in EXERCISES:
            row = await db.scalar(select(Exercise).where(Exercise.name == payload["name"]))
            if row is None:
                row = Exercise(name=payload["name"])
                db.add(row)
            row.aliases = payload["aliases"]
            row.category = payload["category"]
            row.met_low = payload["met_low"]
            row.met_mid = payload["met_mid"]
            row.met_high = payload["met_high"]
        await db.commit()
        print(f"seeded {len(EXERCISES)} exercises")


if __name__ == "__main__":
    asyncio.run(seed())
