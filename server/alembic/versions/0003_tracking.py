"""tracking / recommend / contributions

Revision ID: 0003_tracking
Revises: 0002_foods_intake
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_tracking"
down_revision: Union[str, Sequence[str], None] = "0002_foods_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exercises",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("category", sa.String(32)),
        sa.Column("met_low", sa.Numeric(4, 2), nullable=False),
        sa.Column("met_mid", sa.Numeric(4, 2), nullable=False),
        sa.Column("met_high", sa.Numeric(4, 2), nullable=False),
    )
    op.create_table(
        "exercise_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("exercise_id", sa.BigInteger(), sa.ForeignKey("exercises.id")),
        sa.Column("exercise_name", sa.String(64), nullable=False),
        sa.Column("duration_min", sa.SmallInteger(), nullable=False),
        sa.Column("intensity", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column("kcal_burned", sa.Numeric(7, 1), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_exercise_user_date", "exercise_logs", ["user_id", "log_date"])
    op.create_table(
        "weight_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 1), nullable=False),
        sa.Column("body_fat_pct", sa.Numeric(4, 1)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "log_date", name="uq_weight_user_date"),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rec_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(16), nullable=False),
        sa.Column("scene", sa.String(16), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_rec_user_date", "recommendations", ["user_id", "rec_date"])
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "rec_id", sa.BigInteger(), sa.ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id")),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "user_food_affinity",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("eat_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accept_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dislike_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_eaten_at", sa.Date()),
        sa.Column("affinity", sa.Numeric(5, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "food_contributions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("barcode", sa.String(32)),
        sa.Column("name", sa.String(128)),
        sa.Column("image_url", sa.String(512)),
        sa.Column("parsed", postgresql.JSONB()),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("merged_food_id", sa.BigInteger(), sa.ForeignKey("foods.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "deleted_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "deleted_records",
        "food_contributions",
        "user_food_affinity",
        "recommendation_feedback",
        "recommendations",
        "weight_logs",
        "exercise_logs",
        "exercises",
    ]:
        op.drop_table(table)
