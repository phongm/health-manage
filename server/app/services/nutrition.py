"""能量与营养目标计算。纯函数，不依赖数据库或外部服务。"""

from __future__ import annotations

from typing import Any

ACTIVITY_FACTOR: dict[int, float] = {
    1: 1.2,
    2: 1.375,
    3: 1.55,
    4: 1.725,
    5: 1.9,
}

KCAL_PER_KG_FAT = 7700
SAFETY_FLOOR: dict[int, int] = {1: 1500, 2: 1200}
MAX_DEFICIT_RATIO = 0.25
EXERCISE_CREDIT_RATIO = 0.7

NEED_NUTRIENTS = ("protein_g", "fiber_g", "cho_g")
CAP_NUTRIENTS = ("sodium_mg", "sugar_g", "fat_g")
CAP_TITLE = {"sodium_mg": "高钠食物", "sugar_g": "高糖食物", "fat_g": "高脂食物"}

MEAL_RATIO: dict[str, float] = {
    "breakfast": 0.25,
    "lunch": 0.40,
    "dinner": 0.30,
    "snack": 0.05,
}

EXCLUDE_HEALTH_FLAGS = {
    "diabetes",
    "hypertension",
    "kidney",
    "pregnant",
    "lactating",
    "eating_disorder",
}


def calc_age(birth_year: int, now_year: int) -> int:
    return max(now_year - birth_year, 1)


def calc_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    if height_m <= 0:
        raise ValueError("height_cm must be positive")
    return round(weight_kg / (height_m * height_m), 1)


def calc_bmr(gender: int, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor。gender: 1 男 / 2 女。"""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    offset = 5 if gender == 1 else -161
    return round(base + offset, 1)


def calc_tdee(bmr: float, activity_level: int) -> float:
    factor = ACTIVITY_FACTOR.get(activity_level)
    if factor is None:
        raise ValueError(f"invalid activity_level: {activity_level}")
    return round(bmr * factor, 1)


def calc_target_kcal(
    tdee: float,
    bmr: float,
    gender: int,
    goal: int,
    goal_rate_kg_wk: float,
) -> tuple[float, list[str]]:
    """返回 (目标热量, 安全边界警告列表)。"""
    warnings: list[str] = []

    if goal == 2:
        return round(tdee, 1), warnings
    if goal == 3:
        return round(tdee * 1.1, 1), warnings
    if goal != 1:
        raise ValueError(f"invalid goal: {goal}")

    deficit = goal_rate_kg_wk * KCAL_PER_KG_FAT / 7

    if deficit > tdee * MAX_DEFICIT_RATIO:
        deficit = tdee * MAX_DEFICIT_RATIO
        warnings.append("rate_too_aggressive")

    target = tdee - deficit

    if target < bmr:
        target = bmr
        warnings.append("below_bmr")

    floor = SAFETY_FLOOR.get(gender, SAFETY_FLOOR[2])
    if target < floor:
        target = float(floor)
        warnings.append("below_floor")

    return round(target, 1), warnings


def calc_target_nutrients(target_kcal: float, weight_kg: float, goal: int) -> dict[str, float]:
    protein_g = weight_kg * (1.8 if goal == 1 else 1.4)
    fat_g = target_kcal * 0.25 / 9
    cho_kcal = target_kcal - protein_g * 4 - fat_g * 9
    cho_g = max(cho_kcal / 4, weight_kg * 1.5)

    return {
        "energy_kcal": round(target_kcal, 1),
        "protein_g": round(protein_g, 1),
        "fat_g": round(fat_g, 1),
        "cho_g": round(cho_g, 1),
        "fiber_g": 27.0,
        "sodium_mg": 2000.0,
    }


def calc_remaining(
    target_nutrients: dict[str, float],
    today_intake: dict[str, float],
    today_exercise_kcal: float = 0.0,
) -> dict[str, float]:
    credit = today_exercise_kcal * EXERCISE_CREDIT_RATIO
    remaining: dict[str, float] = {}
    for key, target in target_nutrients.items():
        consumed = today_intake.get(key, 0.0)
        if key == "energy_kcal":
            remaining[key] = round(target + credit - consumed, 1)
        else:
            remaining[key] = round(target - consumed, 1)
    return remaining


def alloc_for_meal(
    remaining: dict[str, float],
    meal_type: str,
    remaining_meals: list[str],
) -> dict[str, float]:
    total_ratio = sum(MEAL_RATIO[m] for m in remaining_meals)
    if total_ratio <= 0:
        raise ValueError("remaining_meals is empty or invalid")
    share = MEAL_RATIO[meal_type] / total_ratio
    return {k: round(v * share, 1) for k, v in remaining.items()}


def detect_exclusion(
    *,
    birth_year: int,
    now_year: int,
    weight_kg: float,
    height_cm: float,
    health_flags: list[str] | None = None,
) -> tuple[bool, str | None]:
    flags = {f for f in (health_flags or []) if f and f != "none"}
    hit = flags & EXCLUDE_HEALTH_FLAGS
    if hit:
        return True, sorted(hit)[0]

    age = calc_age(birth_year, now_year)
    if age < 18:
        return True, "underage"

    if calc_bmi(weight_kg, height_cm) < 18.5:
        return True, "low_bmi"

    return False, None


def compute_profile_targets(
    *,
    gender: int,
    birth_year: int,
    height_cm: float,
    weight_kg: float,
    activity_level: int,
    goal: int,
    goal_rate_kg_wk: float = 0.5,
    now_year: int,
    health_flags: list[str] | None = None,
) -> dict[str, Any]:
    is_excluded, exclude_reason = detect_exclusion(
        birth_year=birth_year,
        now_year=now_year,
        weight_kg=weight_kg,
        height_cm=height_cm,
        health_flags=health_flags,
    )
    age = calc_age(birth_year, now_year)
    bmr = calc_bmr(gender, weight_kg, height_cm, age)
    tdee = calc_tdee(bmr, activity_level)
    target_kcal, warnings = calc_target_kcal(tdee, bmr, gender, goal, goal_rate_kg_wk)
    target_nutrients = calc_target_nutrients(target_kcal, weight_kg, goal)

    return {
        "bmr_kcal": bmr,
        "tdee_kcal": tdee,
        "target_kcal": target_kcal,
        "target_nutrients": target_nutrients,
        "warnings": warnings,
        "is_excluded": is_excluded,
        "exclude_reason": exclude_reason,
        "bmi": calc_bmi(weight_kg, height_cm),
        "age": age,
    }


def scale_nutrients(per_100g: dict[str, float], grams: float) -> dict[str, float]:
    """把每 100g 营养值缩放到实际克数。缺失字段不补 0。"""
    scaled: dict[str, float] = {}
    for key, value in per_100g.items():
        if value is None:
            continue
        scaled[key] = round(float(value) * grams / 100.0, 2)
    return scaled


def sum_nutrients(items: list[dict[str, float]]) -> dict[str, float]:
    acc: dict[str, float] = {}
    for item in items:
        for key, value in item.items():
            if value is None:
                continue
            acc[key] = round(acc.get(key, 0.0) + float(value), 2)
    return acc


def to_per_100g(total: dict[str, float], total_grams: float) -> dict[str, float]:
    if total_grams <= 0:
        raise ValueError("total_grams must be positive")
    return {key: round(value * 100.0 / total_grams, 2) for key, value in total.items()}


def compute_recipe_nutrients(
    ingredients: list[tuple[dict[str, float], float]],
) -> tuple[dict[str, float], float]:
    """返回 (每100g营养, 配方总克数)。"""
    parts = [scale_nutrients(nutrients, grams) for nutrients, grams in ingredients]
    total_grams = sum(grams for _, grams in ingredients)
    return to_per_100g(sum_nutrients(parts), total_grams), total_grams


MEAL_ORDER = ("breakfast", "lunch", "dinner", "snack")


def next_meal(logged_meals: set[str]) -> str:
    for meal in MEAL_ORDER:
        if meal not in logged_meals:
            return meal
    return "snack"


def remaining_meals_from(meal_type: str, logged: set[str]) -> list[str]:
    start = MEAL_ORDER.index(meal_type) if meal_type in MEAL_ORDER else 0
    return [m for m in MEAL_ORDER[start:] if m not in logged or m == meal_type]


def calc_gaps(meal_budget: dict[str, float], target_nutrients: dict[str, float]) -> dict[str, float]:
    gaps: dict[str, float] = {}
    for key, value in meal_budget.items():
        if key in CAP_NUTRIENTS:
            gaps[key] = -1.0 if value <= 0 else 0.0
        else:
            denom = target_nutrients.get(key) or 1
            gaps[key] = max(value, 0) / denom
    return gaps
