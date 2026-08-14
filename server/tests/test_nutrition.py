from app.services.nutrition import (
    calc_bmr,
    calc_target_kcal,
    calc_tdee,
    compute_profile_targets,
    detect_exclusion,
)


def test_bmr_male():
    # 70kg / 175cm / 30 岁男性
    assert calc_bmr(1, 70, 175, 30) == 1648.8


def test_bmr_female():
    # 50kg / 150cm / 30 岁女性
    assert calc_bmr(2, 50, 150, 30) == 1126.5


def test_tdee_sedentary():
    assert calc_tdee(1126.5, 1) == 1351.8


def test_safety_floor_female_aggressive_cut():
    """极端减重速率必须被压到安全下限，并返回警告。"""
    tdee = calc_tdee(1126.5, 1)
    target, warnings = calc_target_kcal(
        tdee=tdee,
        bmr=1126.5,
        gender=2,
        goal=1,
        goal_rate_kg_wk=2.0,
    )
    assert target == 1200.0
    assert "rate_too_aggressive" in warnings
    assert "below_bmr" in warnings
    assert "below_floor" in warnings


def test_safety_floor_male():
    bmr = calc_bmr(1, 55, 160, 25)
    tdee = calc_tdee(bmr, 1)
    target, warnings = calc_target_kcal(tdee, bmr, 1, 1, 1.5)
    assert target >= 1500.0
    assert warnings


def test_maintain_goal_equals_tdee():
    target, warnings = calc_target_kcal(1800, 1400, 1, 2, 0.5)
    assert target == 1800
    assert warnings == []


def test_detect_underage():
    excluded, reason = detect_exclusion(
        birth_year=2012, now_year=2026, weight_kg=60, height_cm=165
    )
    assert excluded is True
    assert reason == "underage"


def test_detect_low_bmi():
    excluded, reason = detect_exclusion(
        birth_year=1995, now_year=2026, weight_kg=42, height_cm=165
    )
    assert excluded is True
    assert reason == "low_bmi"


def test_detect_chronic_flag():
    excluded, reason = detect_exclusion(
        birth_year=1990,
        now_year=2026,
        weight_kg=70,
        height_cm=170,
        health_flags=["diabetes"],
    )
    assert excluded is True
    assert reason == "diabetes"


def test_detect_kidney_flag():
    excluded, reason = detect_exclusion(
        birth_year=1990,
        now_year=2026,
        weight_kg=70,
        height_cm=170,
        health_flags=["kidney"],
    )
    assert excluded is True
    assert reason == "kidney"


def test_compute_profile_includes_nutrients():
    result = compute_profile_targets(
        gender=1,
        birth_year=1996,
        height_cm=175,
        weight_kg=70,
        activity_level=2,
        goal=1,
        goal_rate_kg_wk=0.5,
        now_year=2026,
    )
    assert result["is_excluded"] is False
    assert result["target_kcal"] < result["tdee_kcal"]
    nutrients = result["target_nutrients"]
    assert nutrients["protein_g"] == 126.0  # 70 * 1.8
    assert nutrients["fiber_g"] == 27.0
    assert nutrients["sodium_mg"] == 2000.0
    # 钠是上限型指标，不能被当成缺口去填
    assert nutrients["sodium_mg"] > 0
