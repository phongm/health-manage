from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ProfileUpdate(BaseModel):
    gender: Literal[1, 2]
    birth_year: int = Field(ge=1930, le=2010)
    height_cm: float = Field(gt=100, lt=250)
    weight_kg: float = Field(gt=30, lt=300)
    body_fat_pct: float | None = Field(default=None, ge=3, le=70)
    activity_level: Literal[1, 2, 3, 4, 5]
    goal: Literal[1, 2, 3]
    goal_rate_kg_wk: float = Field(default=0.5, ge=0.1, le=1.5)
    target_weight_kg: float | None = Field(default=None, gt=30, lt=300)
    health_flags: list[str] = Field(default_factory=lambda: ["none"])

    @field_validator("health_flags")
    @classmethod
    def validate_flags(cls, value: list[str]) -> list[str]:
        allowed = {
            "none",
            "diabetes",
            "hypertension",
            "kidney",
            "pregnant",
            "lactating",
            "eating_disorder",
        }
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"unknown health_flags: {sorted(unknown)}")
        return value


class ProfileData(BaseModel):
    gender: int
    birth_year: int
    height_cm: float
    weight_kg: float
    body_fat_pct: float | None
    activity_level: int
    goal: int
    goal_rate_kg_wk: float
    target_weight_kg: float | None
    bmr_kcal: float
    tdee_kcal: float
    target_kcal: float
    target_nutrients: dict[str, Any]
    warnings: list[str]
    is_excluded: bool
    exclude_reason: str | None = None
    health_flags: list[str] = Field(default_factory=list)
    bmi: float | None = None
    profile_completed: bool = True


class PreferencesUpdate(BaseModel):
    allergens: list[str] = Field(default_factory=list)
    avoid_ingredients: list[str] = Field(default_factory=list)
    avoid_categories: list[str] = Field(default_factory=list)
    diet_type: Literal["omnivore", "vegetarian", "vegan", "pescatarian"] | None = "omnivore"
    spice_level: Literal[0, 1, 2, 3] = 2
    scene_default: Literal["takeout", "canteen", "homecook"] = "takeout"
    scene_by_meal: dict[str, str] | None = None


class PreferencesData(PreferencesUpdate):
    pass
