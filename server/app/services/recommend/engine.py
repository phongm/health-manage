from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.nutrition import (
    CAP_NUTRIENTS,
    CAP_TITLE,
    NEED_NUTRIENTS,
    alloc_for_meal,
    calc_gaps,
    remaining_meals_from,
    scale_nutrients,
    sum_nutrients,
)

ENGINE_VERSION = "v1.0"
SWAP_LIMIT = 3
RECOMMEND_DAILY_LIMIT = 20

ROLE_PLAN: dict[str, list[str]] = {
    "breakfast": ["protein", "staple", "dairy_or_fruit"],
    "lunch": ["protein", "staple", "vegetable"],
    "dinner": ["protein", "staple", "vegetable"],
    "snack": ["dairy_or_fruit"],
}

ROLE_KCAL_SHARE: dict[str, float] = {
    "staple": 0.35,
    "protein": 0.40,
    "vegetable": 0.20,
    "dairy_or_fruit": 0.25,
}

ROLE_MATCH: dict[str, set[str]] = {
    "staple": {"staple"},
    "protein": {"protein"},
    "vegetable": {"vegetable"},
    "dairy_or_fruit": {"dairy", "fruit"},
}

WEIGHTS = {
    "nutrition_fit": 0.35,
    "kcal_fit": 0.20,
    "affinity": 0.20,
    "repeat_penalty": -0.15,
    "rule_penalty": -0.10,
}

DIET_BLOCK: dict[str, set[str]] = {
    "vegetarian": {"livestock_meat", "poultry"},
    "vegan": {"livestock_meat", "poultry", "aquatic", "egg", "dairy"},
    "pescatarian": {"livestock_meat", "poultry"},
}


@dataclass
class Portion:
    label: str
    grams: float
    is_default: bool = False


@dataclass
class FoodView:
    id: int
    name: str
    category: str
    cook_method: str | None
    role_tags: list[str]
    attr_tags: list[str]
    ingredient_tags: list[str]
    scene_tags: list[str]
    meal_tags: list[str]
    nutrients: dict[str, float]
    portions: list[Portion]
    popularity: int = 0


@dataclass
class UserCtx:
    goal: int
    allergens: list[str]
    avoid_ingredients: list[str]
    avoid_categories: list[str]
    diet_type: str | None
    spice_level: int
    scene: str
    meal_type: str
    rec_date: date
    target: dict[str, float]
    today_intake: dict[str, float]
    remaining: dict[str, float]
    logged_meals: set[str]
    eaten_today: set[int]
    last_eaten: dict[int, date]
    affinity: dict[int, float]


@dataclass
class SelectedItem:
    food: FoodView
    role: str
    grams: float
    portion_label: str
    nutrients: dict[str, float]
    score: float
    swappable: bool = True


MVP_RULES: list[dict[str, Any]] = [
    {
        "code": "avoid_deepfry",
        "goal_scope": [1],
        "action": "downweight",
        "weight": 0.2,
        "message": "油炸类脂肪密度高，同样分量热量约为清蒸的 2-3 倍，减脂期建议减少",
        "title": "油炸类",
        "goal_level": True,
        "condition": {"all": [{"field": "food.cook_method", "op": "eq", "value": "deepfry"}]},
    },
    {
        "code": "avoid_sugary_drink",
        "goal_scope": [1],
        "action": "downweight",
        "weight": 0.1,
        "message": "含糖饮料提供热量但几乎不提供饱腹感，容易在不察觉中超出额度",
        "title": "含糖饮料",
        "goal_level": True,
        "condition": {
            "all": [
                {"field": "food.category", "op": "eq", "value": "beverage"},
                {"field": "food.nutrients.sugar_g", "op": "gt", "value": 5},
            ]
        },
    },
    {
        "code": "avoid_high_sodium",
        "goal_scope": [1, 2, 3],
        "action": "warn",
        "message": "高钠饮食容易导致水分滞留，会让体重读数波动，影响你判断进展",
        "title": "高钠食物",
        "goal_level": True,
        "condition": {"all": [{"field": "food.nutrients.sodium_mg", "op": "gt", "value": 800}]},
    },
    {
        "code": "avoid_alcohol",
        "goal_scope": [1],
        "action": "downweight",
        "weight": 0.1,
        "message": "酒精本身提供热量且会抑制脂肪氧化",
        "title": "酒精",
        "goal_level": True,
        "condition": {"all": [{"field": "food.category", "op": "eq", "value": "alcohol"}]},
    },
    {
        "code": "avoid_refined_snack",
        "goal_scope": [1],
        "action": "downweight",
        "weight": 0.2,
        "message": "精制糖零食升糖快、饱腹感低",
        "title": "精制零食",
        "goal_level": True,
        "condition": {
            "all": [
                {"field": "food.attr_tags", "op": "contains", "value": "processed"},
                {"field": "food.nutrients.sugar_g", "op": "gt", "value": 15},
            ]
        },
    },
    {
        "code": "cap_fat_exceeded",
        "goal_scope": [1, 2, 3],
        "action": "exclude",
        "message": "今日脂肪已接近目标，先避开高脂食物",
        "title": "高脂肉类",
        "goal_level": False,
        "condition": {
            "all": [
                {"field": "today.fat_ratio", "op": "gt", "value": 0.9},
                {"field": "food.nutrients.fat_g", "op": "gt", "value": 15},
            ]
        },
    },
    {
        "code": "cap_sodium_exceeded",
        "goal_scope": [1, 2, 3],
        "action": "downweight",
        "weight": 0.3,
        "message": "今日钠摄入已较高",
        "title": "高钠食物",
        "goal_level": False,
        "condition": {"all": [{"field": "today.sodium_ratio", "op": "gt", "value": 0.9}]},
    },
]


def _get_field(path: str, food: FoodView, ctx: UserCtx) -> Any:
    if path.startswith("food.nutrients."):
        return (food.nutrients or {}).get(path.split(".")[-1])
    if path == "food.cook_method":
        return food.cook_method
    if path == "food.category":
        return food.category
    if path == "food.attr_tags":
        return food.attr_tags
    if path == "food.ingredient_tags":
        return food.ingredient_tags
    if path == "user.goal":
        return ctx.goal
    if path == "today.fat_ratio":
        target = ctx.target.get("fat_g") or 1
        return ctx.today_intake.get("fat_g", 0) / target
    if path == "today.sodium_ratio":
        target = ctx.target.get("sodium_mg") or 2000
        return ctx.today_intake.get("sodium_mg", 0) / target
    return None


def _compare(op: str, left: Any, right: Any) -> bool:
    if left is None:
        return False
    if op == "eq":
        return left == right
    if op == "ne":
        return left != right
    if op == "gt":
        return left > right
    if op == "gte":
        return left >= right
    if op == "lt":
        return left < right
    if op == "lte":
        return left <= right
    if op == "in":
        return left in right
    if op == "nin":
        return left not in right
    if op == "contains":
        return isinstance(left, list) and right in left
    if op == "overlap":
        return bool(set(left or []) & set(right or []))
    return False


def eval_condition(condition: dict, food: FoodView, ctx: UserCtx) -> bool:
    if "all" in condition:
        return all(eval_condition(item, food, ctx) if "all" in item or "any" in item or "not" in item else _compare(item["op"], _get_field(item["field"], food, ctx), item["value"]) for item in condition["all"])
    if "any" in condition:
        return any(eval_condition(item, food, ctx) if "all" in item or "any" in item or "not" in item else _compare(item["op"], _get_field(item["field"], food, ctx), item["value"]) for item in condition["any"])
    if "not" in condition:
        return not eval_condition(condition["not"], food, ctx)
    return _compare(condition["op"], _get_field(condition["field"], food, ctx), condition["value"])


def default_portion(food: FoodView) -> Portion:
    for portion in food.portions:
        if portion.is_default:
            return portion
    if food.portions:
        return food.portions[0]
    return Portion("100克", 100.0, True)


def nearest_portion(food: FoodView, target_grams: float) -> Portion:
    if not food.portions:
        return Portion(f"{target_grams:g}克", target_grams, True)
    return min(food.portions, key=lambda p: abs(p.grams - target_grams))


def matches_role(food: FoodView, role: str) -> bool:
    wanted = ROLE_MATCH.get(role, {role})
    return bool(wanted & set(food.role_tags or []))


def hard_exclude(food: FoodView, ctx: UserCtx) -> bool:
    tags = set(food.ingredient_tags or [])
    if set(ctx.allergens) & tags:
        return True
    for item in ctx.avoid_ingredients:
        if item and (item in tags or item in food.name):
            return True
    if food.category in ctx.avoid_categories:
        return True
    blocked = DIET_BLOCK.get(ctx.diet_type or "", set())
    if food.category in blocked:
        return True
    if ctx.spice_level == 0 and "spicy" in (food.attr_tags or []):
        return True
    return False


def rule_factor(food: FoodView, ctx: UserCtx) -> tuple[float, list[str]]:
    factor = 1.0
    triggered: list[str] = []
    for rule in MVP_RULES:
        if ctx.goal not in rule["goal_scope"]:
            continue
        if not eval_condition(rule["condition"], food, ctx):
            continue
        triggered.append(rule["code"])
        if rule["action"] == "exclude":
            return 0.0, triggered
        if rule["action"] == "downweight":
            factor = min(factor, float(rule.get("weight", 0.5)))
        if rule["code"] == "low_protein_day":
            factor = max(factor, 1.2)
    if ctx.spice_level <= 1 and "spicy" in (food.attr_tags or []) and ctx.spice_level != 0:
        factor = min(factor, 0.4)
    return factor, triggered


def score_food(food: FoodView, ctx: UserCtx, gaps: dict[str, float], meal_budget: dict[str, float], role: str) -> float:
    portion = default_portion(food)
    nutrients = scale_nutrients(food.nutrients, portion.grams)
    fit = 0.0
    need_sum = sum(v for k, v in gaps.items() if k in NEED_NUTRIENTS) or 1e-6
    for key in NEED_NUTRIENTS:
        if gaps.get(key, 0) > 0:
            contribution = min(nutrients.get(key, 0) / max(meal_budget.get(key, 1e-6), 1e-6), 1.0)
            fit += contribution * gaps[key]
    fit = fit / need_sum

    expect = meal_budget.get("energy_kcal", 1) * ROLE_KCAL_SHARE.get(role, 0.3)
    kcal = nutrients.get("energy_kcal", 0)
    kcal_fit = 1 - min(abs(kcal - expect) / max(expect, 1), 1.0)

    affinity = ctx.affinity.get(food.id, 0.0)
    last = ctx.last_eaten.get(food.id)
    days = (ctx.rec_date - last).days if last else None
    repeat = max(0.0, 1 - days / 3) if days is not None else 0.0
    factor, _ = rule_factor(food, ctx)

    return (
        WEIGHTS["nutrition_fit"] * fit
        + WEIGHTS["kcal_fit"] * kcal_fit
        + WEIGHTS["affinity"] * affinity
        + WEIGHTS["repeat_penalty"] * repeat
        + WEIGHTS["rule_penalty"] * (1 - min(factor, 1.0))
    )


def recall(foods: list[FoodView], ctx: UserCtx, role: str, meal_budget: dict[str, float]) -> list[FoodView]:
    out: list[FoodView] = []
    for food in foods:
        if food.id in ctx.eaten_today:
            continue
        if ctx.scene not in (food.scene_tags or []):
            continue
        if food.meal_tags and ctx.meal_type not in food.meal_tags:
            continue
        if not matches_role(food, role):
            continue
        if hard_exclude(food, ctx):
            continue
        factor, _ = rule_factor(food, ctx)
        if factor == 0.0:
            continue
        portion = default_portion(food)
        kcal = scale_nutrients(food.nutrients, portion.grams).get("energy_kcal", 0)
        if kcal > meal_budget.get("energy_kcal", 0) * 1.2:
            continue
        out.append(food)
    out.sort(key=lambda f: f.popularity, reverse=True)
    return out[:50]


def adjust_portions(items: list[SelectedItem], budget_kcal: float) -> list[SelectedItem]:
    total = sum(item.nutrients.get("energy_kcal", 0) for item in items)
    if total <= 0 or not items:
        return items
    ratio = budget_kcal / total
    for item in items:
        target_g = item.grams * ratio
        portion = nearest_portion(item.food, target_g)
        item.grams = portion.grams
        item.portion_label = portion.label
        item.nutrients = scale_nutrients(item.food.nutrients, portion.grams)
    return items


def build_meal(foods: list[FoodView], ctx: UserCtx) -> tuple[list[SelectedItem], dict[str, Any]]:
    remaining_meals = remaining_meals_from(ctx.meal_type, ctx.logged_meals)
    meal_budget = alloc_for_meal(ctx.remaining, ctx.meal_type, remaining_meals)
    gaps = calc_gaps(meal_budget, ctx.target)
    plan = ROLE_PLAN.get(ctx.meal_type, ROLE_PLAN["lunch"])
    selected: list[SelectedItem] = []
    used_categories: set[str] = set()
    used_ids: set[int] = set()
    triggered: list[str] = []

    for role in plan:
        pool = recall(foods, ctx, role, meal_budget)
        ranked: list[tuple[float, FoodView]] = []
        for food in pool:
            if food.id in used_ids:
                continue
            if food.category in used_categories and food.category != "vegetable":
                continue
            ranked.append((score_food(food, ctx, gaps, meal_budget, role), food))
        ranked.sort(key=lambda x: x[0], reverse=True)
        if not ranked:
            continue
        score, food = ranked[0]
        portion = default_portion(food)
        nutrients = scale_nutrients(food.nutrients, portion.grams)
        _, codes = rule_factor(food, ctx)
        triggered.extend(codes)
        selected.append(
            SelectedItem(
                food=food,
                role=role,
                grams=portion.grams,
                portion_label=portion.label,
                nutrients=nutrients,
                score=score,
            )
        )
        used_ids.add(food.id)
        used_categories.add(food.category)

    budget_kcal = meal_budget.get("energy_kcal", 0)
    total = sum(item.nutrients.get("energy_kcal", 0) for item in selected)
    if selected and budget_kcal and total > budget_kcal * 1.05:
        selected = adjust_portions(selected, budget_kcal)
    elif selected and budget_kcal and total < budget_kcal * 0.85:
        selected = adjust_portions(selected, budget_kcal)

    if len(selected) == 1:
        selected[0].swappable = False

    context = {
        "remaining_kcal": ctx.remaining.get("energy_kcal"),
        "meal_budget": meal_budget,
        "gaps": gaps,
        "triggered_rules": sorted(set(triggered)),
        "scores": {item.food.id: round(item.score, 4) for item in selected},
    }
    return selected, context


def build_reasons(items: list[SelectedItem], ctx: UserCtx, meal_budget: dict[str, float]) -> list[str]:
    reasons: list[str] = []
    protein_gap = max((ctx.target.get("protein_g") or 0) - (ctx.today_intake.get("protein_g") or 0), 0)
    protein_contrib = sum(item.nutrients.get("protein_g", 0) for item in items)
    if protein_gap > 0:
        reasons.append(f"今天蛋白质还差 {protein_gap:.0f}g，这份约能补 {protein_contrib:.0f}g")
    total = sum(item.nutrients.get("energy_kcal", 0) for item in items)
    budget = meal_budget.get("energy_kcal", 0)
    reasons.append(f"热量约 {total:.0f} kcal，在你这餐的 {budget:.0f} kcal 额度内")
    return reasons


def build_avoid_list(ctx: UserCtx) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key in CAP_NUTRIENTS:
        target = ctx.target.get(key) or 0
        if target <= 0:
            continue
        ratio = (ctx.today_intake.get(key) or 0) / target
        if ratio > 0.9:
            items.append(
                {
                    "title": CAP_TITLE.get(key, key),
                    "reason": f"今日已达目标的 {ratio:.0%}",
                    "level": "alert",
                }
            )
    for rule in MVP_RULES:
        if ctx.goal not in rule["goal_scope"]:
            continue
        if rule.get("goal_level") and rule["action"] in {"warn", "downweight"}:
            items.append({"title": rule["title"], "reason": rule["message"], "level": "info"})
    # 动态项置顶
    items.sort(key=lambda x: 0 if x["level"] == "alert" else 1)
    # 去重 title
    seen: set[str] = set()
    unique = []
    for item in items:
        if item["title"] in seen:
            continue
        seen.add(item["title"])
        unique.append(item)
    return unique


def serialize_meal(items: list[SelectedItem], ctx: UserCtx, context: dict[str, Any], swaps_remaining: int) -> dict[str, Any]:
    total = sum_nutrients([item.nutrients for item in items])
    return {
        "meal_type": ctx.meal_type,
        "scene": ctx.scene,
        "items": [
            {
                "food_id": item.food.id,
                "name": item.food.name,
                "role": item.role,
                "grams": item.grams,
                "portion_label": item.portion_label,
                "nutrients": item.nutrients,
                "swappable": item.swappable,
            }
            for item in items
        ],
        "total": total,
        "budget": {"energy_kcal": context["meal_budget"].get("energy_kcal")},
        "reasons": build_reasons(items, ctx, context["meal_budget"]),
        "avoid_list": build_avoid_list(ctx),
        "swaps_remaining": swaps_remaining,
        "version": ENGINE_VERSION,
        "context": context,
    }


def swap_item(
    foods: list[FoodView],
    ctx: UserCtx,
    current: list[SelectedItem],
    food_id: int,
    reason: str,
) -> list[SelectedItem]:
    target = next((item for item in current if item.food.id == food_id), None)
    if target is None:
        raise ValueError("food_not_in_recommendation")

    if reason == "too_much":
        smaller = [p for p in target.food.portions if p.grams < target.grams]
        if smaller:
            portion = max(smaller, key=lambda p: p.grams)
            target.grams = portion.grams
            target.portion_label = portion.label
            target.nutrients = scale_nutrients(target.food.nutrients, portion.grams)
            return current

    meal_budget = alloc_for_meal(
        ctx.remaining, ctx.meal_type, remaining_meals_from(ctx.meal_type, ctx.logged_meals)
    )
    used = {item.food.id for item in current}
    kcal = target.nutrients.get("energy_kcal", 0)
    protein = target.nutrients.get("protein_g", 0)
    pool = recall(foods, ctx, target.role, meal_budget)
    gaps = calc_gaps(meal_budget, ctx.target)
    ranked = []
    for food in pool:
        if food.id in used:
            continue
        n = scale_nutrients(food.nutrients, default_portion(food).grams)
        if not (kcal * 0.7 <= n.get("energy_kcal", 0) <= kcal * 1.3):
            continue
        ranked.append((score_food(food, ctx, gaps, meal_budget, target.role), food))
    if not ranked:
        for food in pool:
            if food.id in used:
                continue
            ranked.append((score_food(food, ctx, gaps, meal_budget, target.role), food))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        raise ValueError("no_alternative")
    score, food = ranked[0]
    portion = default_portion(food)
    replacement = SelectedItem(
        food=food,
        role=target.role,
        grams=portion.grams,
        portion_label=portion.label,
        nutrients=scale_nutrients(food.nutrients, portion.grams),
        score=score,
    )
    return [replacement if item.food.id == food_id else item for item in current]
