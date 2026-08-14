from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    category: Mapped[str | None] = mapped_column(String(32))
    met_low: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    met_mid: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    met_high: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)


class ExerciseLog(Base):
    __tablename__ = "exercise_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"))
    exercise_name: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    intensity: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("2"))
    kcal_burned: Mapped[float] = mapped_column(Numeric(7, 1), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_weight_user_date"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 1))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rec_date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    scene: Mapped[str] = mapped_column(String(16), nullable=False)
    items: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rec_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserFoodAffinity(Base):
    __tablename__ = "user_food_affinity"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True)
    eat_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    accept_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    dislike_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    last_eaten_at: Mapped[date | None] = mapped_column(Date)
    affinity: Mapped[float] = mapped_column(Numeric(5, 3), nullable=False, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FoodContribution(Base):
    __tablename__ = "food_contributions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(128))
    image_url: Mapped[str | None] = mapped_column(String(512))
    parsed: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    merged_food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeletedRecord(Base):
    __tablename__ = "deleted_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    entity: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClientOp(Base):
    __tablename__ = "client_ops"

    client_op_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
