from app.services.quota import IMAGE_PARSE_DAILY_LIMIT
from app.services.report import calc_achievement, calc_micros, calc_structure


def test_image_parse_daily_limit():
    assert IMAGE_PARSE_DAILY_LIMIT == 3


def test_achievement_and_sodium_cap():
    rows = calc_achievement(
        {"energy_kcal": 1500, "protein_g": 80, "cho_g": 160, "fiber_g": 13.5, "fat_g": 40, "sodium_mg": 2400},
        {"energy_kcal": 1500, "protein_g": 100, "cho_g": 160, "fiber_g": 27, "fat_g": 40, "sodium_mg": 2000},
    )
    by_key = {row["key"]: row for row in rows}
    assert by_key["protein_g"]["ratio"] == 0.8
    assert by_key["fiber_g"]["ratio"] == 0.5
    assert by_key["sodium_mg"]["cap"] is True
    assert by_key["sodium_mg"]["ratio"] == 1.2


def test_micros_skip_unknown_keys():
    rows = calc_micros({"fiber_g": 10, "sodium_mg": 800}, {"fiber_g": 27, "sodium_mg": 2000})
    keys = {row["key"] for row in rows}
    assert keys == {"fiber_g", "sodium_mg"}
    assert all(row["unknown"] is False for row in rows)


def test_structure_pct_sums_to_one():
    rows = calc_structure({"poultry": 2, "grain": 2})
    assert sum(row["pct"] for row in rows) == 1
    assert rows[0]["label"] in {"禽肉", "主食"}
