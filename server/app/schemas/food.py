from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class FoodPortionOut(BaseModel):
    label: str
    grams: float
    is_default: bool


class FoodOut(BaseModel):
    food_id: int
    name: str
    category: str
    nutrients_per_100g: dict
    portions: list[FoodPortionOut]
    role_tags: list[str] = []
    scene_tags: list[str] = []


class IntakeItemIn(BaseModel):
    food_id: int
    grams: float = Field(gt=0, le=5000)
    portion_label: str | None = None


class IntakeCreate(BaseModel):
    log_date: date
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    items: list[IntakeItemIn] = Field(min_length=1, max_length=20)
    input_source: Literal["text", "voice", "image", "recommend"] = "text"
    from_rec_id: int | None = None


class ParseTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=200)
