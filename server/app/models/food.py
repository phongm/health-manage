from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Food(Base):
    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    scene_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    meal_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    cook_method: Mapped[str | None] = mapped_column(String(16))
    role_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    attr_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    ingredient_tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    nutrients: Mapped[dict] = mapped_column(JSONB, nullable=False)
    edible_pct: Mapped[float] = mapped_column(Numeric(4, 1), server_default=text("100.0"))
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(256))
    confidence: Mapped[int] = mapped_column(SmallInteger, server_default=text("3"))
    review_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    barcode: Mapped[str | None] = mapped_column(String(32))
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    portions: Mapped[list["FoodPortion"]] = relationship(
        back_populates="food", cascade="all, delete-orphan"
    )


class FoodPortion(Base):
    __tablename__ = "food_portions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    grams: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))

    food: Mapped[Food] = relationship(back_populates="portions")


class FoodRecipe(Base):
    __tablename__ = "food_recipes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dish_food_id: Mapped[int] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("foods.id"), nullable=False)
    grams: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    note: Mapped[str | None] = mapped_column(String(64))


class IntakeLog(Base):
    __tablename__ = "intake_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    food_name: Mapped[str] = mapped_column(String(128), nullable=False)
    grams: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    portion_label: Mapped[str | None] = mapped_column(String(32))
    nutrients_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_source: Mapped[str] = mapped_column(String(16), nullable=False)
    from_rec_id: Mapped[int | None] = mapped_column(BigInteger)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = ()
