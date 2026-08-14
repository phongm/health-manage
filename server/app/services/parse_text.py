"""把「两个鸡蛋一碗米饭」解析成食物条目。先走规则，不调用大模型。"""

from __future__ import annotations

import re
from dataclasses import dataclass

CN_NUM = {
    "半": 0.5,
    "一": 1.0,
    "二": 2.0,
    "两": 2.0,
    "三": 3.0,
    "四": 4.0,
    "五": 5.0,
    "六": 6.0,
    "七": 7.0,
    "八": 8.0,
    "九": 9.0,
    "十": 10.0,
}
UNITS = ("碗", "份", "个", "杯", "勺", "根", "片", "块", "袋", "条")
SKIP_CHARS = set(" ，,。.、和还有再加配带了的")


@dataclass
class CatalogFood:
    id: int
    name: str
    aliases: list[str]
    portions: list[tuple[str, float, bool]]  # label, grams, is_default


@dataclass
class ParsedItem:
    food_id: int
    name: str
    grams: float
    portion_label: str
    confidence: float


def default_portion(food: CatalogFood) -> tuple[str, float]:
    for label, grams, is_default in food.portions:
        if is_default:
            return label, grams
    if food.portions:
        return food.portions[0][0], food.portions[0][1]
    return "100克", 100.0


def _qty_from_prefix(prefix: str) -> tuple[float, str | None]:
    """从食物名前面的文本提取数量和单位。"""
    prefix = prefix.strip()
    gram_match = re.search(r"(\d+(?:\.\d+)?)\s*(克|g|G)$", prefix)
    if gram_match:
        return float(gram_match.group(1)), "克"

    unit = next((u for u in UNITS if prefix.endswith(u)), None)
    head = prefix[: -len(unit)] if unit else prefix

    if re.fullmatch(r"\d+(?:\.\d+)?", head):
        return float(head), unit

    if head in CN_NUM:
        return CN_NUM[head], unit

    if unit and not head:
        return 1.0, unit

    return 1.0, unit


def _portion_for_unit(food: CatalogFood, qty: float, unit: str | None) -> tuple[str, float]:
    if unit == "克":
        return f"{qty:g}克", qty

    if unit:
        for label, grams, _ in food.portions:
            if unit in label:
                return (label if qty == 1 else f"{qty:g}{label}"), grams * qty

    label, grams = default_portion(food)
    if qty == 1:
        return label, grams
    return f"{qty:g}×{label}", grams * qty


def parse_food_text(text: str, catalog: list[CatalogFood]) -> dict:
    names: list[tuple[str, CatalogFood]] = []
    for food in catalog:
        names.append((food.name, food))
        for alias in food.aliases:
            names.append((alias, food))
    names.sort(key=lambda item: len(item[0]), reverse=True)

    remaining = text.strip()
    items: list[ParsedItem] = []
    used_spans = 0

    while remaining:
        remaining = remaining.lstrip("".join(SKIP_CHARS) + " ")
        if not remaining:
            break
        hit: tuple[int, CatalogFood, str] | None = None
        for name, food in names:
            idx = remaining.find(name)
            if idx >= 0 and (hit is None or idx < hit[0] or (idx == hit[0] and len(name) > len(hit[2]))):
                hit = (idx, food, name)
        if hit is None:
            break
        idx, food, name = hit
        prefix = remaining[:idx]
        qty, unit = _qty_from_prefix(prefix)
        portion_label, grams = _portion_for_unit(food, qty, unit)
        items.append(
            ParsedItem(
                food_id=food.id,
                name=food.name,
                grams=round(grams, 1),
                portion_label=portion_label,
                confidence=0.95 if prefix.strip() else 0.8,
            )
        )
        remaining = remaining[idx + len(name) :]
        used_spans += 1
        if used_spans > 20:
            break

    leftover = remaining.strip("".join(SKIP_CHARS) + " ")
    return {
        "items": [
            {
                "food_id": item.food_id,
                "name": item.name,
                "grams": item.grams,
                "portion_label": item.portion_label,
                "confidence": item.confidence,
            }
            for item in items
        ],
        "unresolved": [leftover] if leftover else [],
        "parser": "rule",
    }
