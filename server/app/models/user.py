from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    unionid: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False)
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    gender: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    birth_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    height_cm: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1))
    activity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goal: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    goal_rate_kg_wk: Mapped[float] = mapped_column(Numeric(3, 2), server_default=text("0.5"))
    target_weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1))
    bmr_kcal: Mapped[float | None] = mapped_column(Numeric(7, 1))
    tdee_kcal: Mapped[float | None] = mapped_column(Numeric(7, 1))
    target_kcal: Mapped[float | None] = mapped_column(Numeric(7, 1))
    target_nutrients: Mapped[dict | None] = mapped_column(JSONB)
    is_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    exclude_reason: Mapped[str | None] = mapped_column(String(64))
    health_flags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    allergens: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    avoid_ingredients: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    avoid_categories: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    diet_type: Mapped[str | None] = mapped_column(String(32))
    spice_level: Mapped[int] = mapped_column(SmallInteger, server_default=text("2"))
    scene_default: Mapped[str] = mapped_column(String(16), server_default=text("'takeout'"))
    scene_by_meal: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="preferences")
