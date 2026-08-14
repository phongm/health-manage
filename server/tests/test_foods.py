from app.services.nutrition import calc_remaining, compute_recipe_nutrients, scale_nutrients
from app.services.parse_text import CatalogFood, parse_food_text


def test_scale_nutrients_skips_missing():
    scaled = scale_nutrients({"energy_kcal": 130, "protein_g": 2.7}, 150)
    assert scaled["energy_kcal"] == 195.0
    assert scaled["protein_g"] == 4.05
    assert "fiber_g" not in scaled


def test_recipe_per_100g():
    nutrients, total = compute_recipe_nutrients(
        [
            ({"energy_kcal": 165, "protein_g": 31}, 120),
            ({"energy_kcal": 53, "protein_g": 8.1}, 5),
        ]
    )
    assert total == 125
    # (165*1.2 + 53*0.05) / 125 * 100
    assert nutrients["energy_kcal"] == 160.52
    assert nutrients["protein_g"] == 30.09


def test_remaining_energy_credits_70_percent_exercise():
    remaining = calc_remaining(
        {"energy_kcal": 1500, "protein_g": 100},
        {"energy_kcal": 500, "protein_g": 40},
        today_exercise_kcal=200,
    )
    assert remaining["energy_kcal"] == 1140.0
    assert remaining["protein_g"] == 60.0


def _catalog() -> list[CatalogFood]:
    return [
        CatalogFood(
            id=1,
            name="鸡蛋",
            aliases=["煮鸡蛋"],
            portions=[("一个", 50, True), ("两个", 100, False)],
        ),
        CatalogFood(
            id=2,
            name="米饭",
            aliases=["白米饭"],
            portions=[("一碗", 150, True), ("半碗", 75, False)],
        ),
        CatalogFood(
            id=3,
            name="豆浆",
            aliases=[],
            portions=[("一杯", 250, True)],
        ),
    ]


def test_parse_common_breakfast_sentence():
    result = parse_food_text("两个鸡蛋一碗米饭还有一杯豆浆", _catalog())
    names = [item["name"] for item in result["items"]]
    assert names == ["鸡蛋", "米饭", "豆浆"]
    grams = {item["name"]: item["grams"] for item in result["items"]}
    assert grams["鸡蛋"] == 100
    assert grams["米饭"] == 150
    assert grams["豆浆"] == 250
    assert result["parser"] == "rule"
    assert result["unresolved"] == []


def test_parse_grams_and_alias():
    result = parse_food_text("150克白米饭", _catalog())
    assert result["items"][0]["name"] == "米饭"
    assert result["items"][0]["grams"] == 150
