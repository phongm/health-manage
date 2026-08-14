from __future__ import annotations

CATEGORY_LABEL = {
    "grain": "主食",
    "tuber": "薯类",
    "poultry": "禽肉",
    "livestock_meat": "畜肉",
    "aquatic": "水产",
    "egg": "蛋类",
    "dairy": "乳制品",
    "vegetable": "蔬菜",
    "fruit": "水果",
    "legume": "豆类",
    "nut": "坚果",
    "mushroom_algae": "菌藻",
    "beverage": "饮料",
    "alcohol": "酒精",
    "oil_fat": "油脂",
    "condiment": "调味",
    "snack": "零食",
}

ACHIEVE_KEYS = ("energy_kcal", "protein_g", "cho_g", "fiber_g", "fat_g")
MICRO_KEYS = ("fiber_g", "sodium_mg", "calcium_mg", "iron_mg", "vitamin_a_ug", "vitamin_c_mg")


def calc_achievement(avg_intake: dict[str, float], target: dict[str, float]) -> list[dict]:
    rows: list[dict] = []
    for key in ACHIEVE_KEYS:
        goal = float(target.get(key) or 0)
        if goal <= 0:
            continue
        intake = float(avg_intake.get(key) or 0)
        rows.append(
            {
                "key": key,
                "intake": round(intake, 1),
                "target": round(goal, 1),
                "ratio": round(intake / goal, 2),
                "cap": False,
            }
        )
    sodium_goal = float(target.get("sodium_mg") or 0)
    if sodium_goal > 0:
        intake = float(avg_intake.get("sodium_mg") or 0)
        rows.append(
            {
                "key": "sodium_mg",
                "intake": round(intake, 1),
                "target": round(sodium_goal, 1),
                "ratio": round(intake / sodium_goal, 2),
                "cap": True,
            }
        )
    return rows


def calc_micros(avg_intake: dict[str, float], target: dict[str, float]) -> list[dict]:
    rows: list[dict] = []
    for key in MICRO_KEYS:
        has_intake = key in avg_intake
        has_target = key in target
        if not has_intake and not has_target:
            continue
        rows.append(
            {
                "key": key,
                "intake": round(float(avg_intake.get(key) or 0), 1) if has_intake else None,
                "target": round(float(target[key]), 1) if has_target else None,
                "unknown": not has_intake,
            }
        )
    return rows


def calc_structure(category_counts: dict[str, int]) -> list[dict]:
    total = sum(category_counts.values()) or 1
    rows = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "category": key,
            "label": CATEGORY_LABEL.get(key, key),
            "count": count,
            "pct": round(count / total, 2),
        }
        for key, count in rows
    ]
