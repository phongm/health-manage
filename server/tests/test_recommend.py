from datetime import date

from app.services.nutrition import calc_gaps
from app.services.recommend.engine import (
    FoodView,
    Portion,
    SelectedItem,
    UserCtx,
    build_avoid_list,
    build_meal,
    hard_exclude,
    swap_item,
)


def food(**kwargs) -> FoodView:
    defaults = dict(
        id=1,
        name="米饭",
        category="grain",
        cook_method="steam",
        role_tags=["staple"],
        attr_tags=[],
        ingredient_tags=["rice"],
        scene_tags=["takeout", "canteen", "homecook"],
        meal_tags=["lunch", "dinner"],
        nutrients={"energy_kcal": 130, "protein_g": 2.7, "fat_g": 0.3, "cho_g": 28, "fiber_g": 0.4, "sodium_mg": 1},
        portions=[Portion("一碗", 150, True), Portion("半碗", 75)],
    )
    defaults.update(kwargs)
    return FoodView(**defaults)


def ctx(**kwargs) -> UserCtx:
    defaults = dict(
        goal=1,
        allergens=[],
        avoid_ingredients=[],
        avoid_categories=[],
        diet_type="omnivore",
        spice_level=2,
        scene="canteen",
        meal_type="lunch",
        rec_date=date(2026, 8, 13),
        target={"energy_kcal": 1500, "protein_g": 100, "fat_g": 40, "cho_g": 160, "fiber_g": 27, "sodium_mg": 2000},
        today_intake={"energy_kcal": 400, "protein_g": 20, "fat_g": 10, "cho_g": 50, "fiber_g": 4, "sodium_mg": 400},
        remaining={"energy_kcal": 1100, "protein_g": 80, "fat_g": 30, "cho_g": 110, "fiber_g": 23, "sodium_mg": 1600},
        logged_meals={"breakfast"},
        eaten_today=set(),
        last_eaten={},
        affinity={},
    )
    defaults.update(kwargs)
    return UserCtx(**defaults)


CATALOG = [
    food(id=1, name="米饭", role_tags=["staple"], category="grain"),
    food(
        id=2,
        name="清蒸鸡胸",
        role_tags=["protein"],
        category="poultry",
        ingredient_tags=["chicken"],
        nutrients={"energy_kcal": 165, "protein_g": 31, "fat_g": 3.6, "cho_g": 0, "fiber_g": 0, "sodium_mg": 74},
        portions=[Portion("一份", 120, True), Portion("半份", 60)],
        meal_tags=["lunch", "dinner"],
    ),
    food(
        id=3,
        name="清炒时蔬",
        role_tags=["vegetable"],
        category="vegetable",
        nutrients={"energy_kcal": 35, "protein_g": 1.3, "fat_g": 5, "cho_g": 5, "fiber_g": 2, "sodium_mg": 80},
        portions=[Portion("一份", 150, True)],
        meal_tags=["lunch", "dinner"],
    ),
    food(
        id=4,
        name="白灼虾",
        role_tags=["protein"],
        category="aquatic",
        ingredient_tags=["shrimp"],
        nutrients={"energy_kcal": 99, "protein_g": 24, "fat_g": 0.3, "cho_g": 0.2, "fiber_g": 0, "sodium_mg": 111},
        portions=[Portion("一份", 100, True)],
        meal_tags=["lunch", "dinner"],
    ),
    food(
        id=5,
        name="瘦牛肉",
        role_tags=["protein"],
        category="livestock_meat",
        ingredient_tags=["beef"],
        nutrients={"energy_kcal": 184, "protein_g": 29, "fat_g": 6.4, "cho_g": 0, "fiber_g": 0, "sodium_mg": 54},
        portions=[Portion("一份", 100, True)],
        meal_tags=["lunch", "dinner"],
    ),
    food(
        id=6,
        name="可乐",
        role_tags=["dairy"],
        category="beverage",
        cook_method="raw",
        attr_tags=["high_sugar", "processed"],
        nutrients={"energy_kcal": 42, "protein_g": 0, "fat_g": 0, "cho_g": 10.6, "fiber_g": 0, "sodium_mg": 4, "sugar_g": 10.6},
        portions=[Portion("一杯", 330, True)],
        meal_tags=["snack"],
        scene_tags=["takeout", "canteen", "homecook"],
    ),
    food(
        id=7,
        name="麻辣香锅",
        role_tags=["protein"],
        category="livestock_meat",
        attr_tags=["spicy"],
        ingredient_tags=["pork"],
        nutrients={"energy_kcal": 180, "protein_g": 18, "fat_g": 10, "cho_g": 6, "fiber_g": 1, "sodium_mg": 600},
        portions=[Portion("一份", 150, True)],
        meal_tags=["lunch", "dinner"],
    ),
]


def test_allergen_never_recommended():
    user = ctx(allergens=["shrimp"])
    assert hard_exclude(CATALOG[3], user) is True
    items, _ = build_meal(CATALOG, user)
    assert all(item.food.id != 4 for item in items)


def test_sodium_is_not_a_need_gap():
    budget = {"energy_kcal": 500, "protein_g": 40, "sodium_mg": 800, "fat_g": 20}
    gaps = calc_gaps(budget, {"energy_kcal": 1500, "protein_g": 100, "sodium_mg": 2000, "fat_g": 40})
    assert gaps["sodium_mg"] == 0.0
    assert gaps["protein_g"] > 0


def test_meal_kcal_within_budget_band():
    items, context = build_meal(CATALOG, ctx())
    assert items
    total = sum(i.nutrients["energy_kcal"] for i in items)
    budget = context["meal_budget"]["energy_kcal"]
    assert total > 0
    assert total <= budget * 1.20


def test_avoid_list_puts_alerts_first():
    user = ctx(today_intake={"energy_kcal": 400, "protein_g": 20, "fat_g": 38, "cho_g": 50, "fiber_g": 4, "sodium_mg": 400})
    avoid = build_avoid_list(user)
    assert avoid[0]["level"] == "alert"
    assert any(item["title"] == "油炸类" for item in avoid)


def test_swap_keeps_role_and_no_allergen():
    user = ctx(allergens=["shrimp"])
    items, _ = build_meal(CATALOG, user)
    protein = next(i for i in items if i.role == "protein")
    swapped = swap_item(CATALOG, user, items, protein.food.id, "dont_like")
    new_protein = next(i for i in swapped if i.role == "protein")
    assert new_protein.food.id != protein.food.id
    assert new_protein.food.id != 4


def test_too_much_reduces_portion():
    item = SelectedItem(
        food=CATALOG[1],
        role="protein",
        grams=120,
        portion_label="一份",
        nutrients={"energy_kcal": 198, "protein_g": 37},
        score=1,
    )
    result = swap_item(CATALOG, ctx(), [item], 2, "too_much")
    assert result[0].grams == 60
    assert result[0].food.id == 2


def test_no_spice_hard_excludes_spicy():
    spicy = CATALOG[-1]
    assert hard_exclude(spicy, ctx(spice_level=0)) is True
    assert hard_exclude(spicy, ctx(spice_level=2)) is False
    items, _ = build_meal(CATALOG, ctx(spice_level=0))
    assert all(item.food.id != 7 for item in items)
