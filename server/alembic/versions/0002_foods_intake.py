"""Initial foods / portions / recipes / intake_logs

Revision ID: 0002_foods_intake
Revises: 0001_init_users
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_foods_intake"
down_revision: Union[str, Sequence[str], None] = "0001_init_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("scene_tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("meal_tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("cook_method", sa.String(16), nullable=True),
        sa.Column("role_tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("attr_tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("ingredient_tags", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("nutrients", postgresql.JSONB(), nullable=False),
        sa.Column("edible_pct", sa.Numeric(4, 1), server_default="100.0", nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_ref", sa.String(256), nullable=True),
        sa.Column("confidence", sa.SmallInteger(), server_default="3", nullable=False),
        sa.Column("review_status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("barcode", sa.String(32), nullable=True),
        sa.Column("popularity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_foods_code"),
    )
    op.create_index("idx_foods_category", "foods", ["category"])
    op.create_index("idx_foods_scene_tags", "foods", ["scene_tags"], postgresql_using="gin")
    op.create_index("idx_foods_role_tags", "foods", ["role_tags"], postgresql_using="gin")
    op.create_index("idx_foods_aliases", "foods", ["aliases"], postgresql_using="gin")
    op.create_index("idx_foods_barcode", "foods", ["barcode"], postgresql_where=sa.text("barcode IS NOT NULL"))

    op.create_table(
        "food_portions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(32), nullable=False),
        sa.Column("grams", sa.Numeric(7, 1), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.SmallInteger(), server_default="0", nullable=False),
    )
    op.create_index("idx_portions_food", "food_portions", ["food_id"])

    op.create_table(
        "food_recipes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "dish_food_id", sa.BigInteger(), sa.ForeignKey("foods.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("ingredient_id", sa.BigInteger(), sa.ForeignKey("foods.id"), nullable=False),
        sa.Column("grams", sa.Numeric(7, 1), nullable=False),
        sa.Column("note", sa.String(64), nullable=True),
    )
    op.create_index("idx_recipes_dish", "food_recipes", ["dish_food_id"])

    op.create_table(
        "intake_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(16), nullable=False),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id"), nullable=True),
        sa.Column("food_name", sa.String(128), nullable=False),
        sa.Column("grams", sa.Numeric(7, 1), nullable=False),
        sa.Column("portion_label", sa.String(32), nullable=True),
        sa.Column("nutrients_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("input_source", sa.String(16), nullable=False),
        sa.Column("from_rec_id", sa.BigInteger(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_intake_user_date", "intake_logs", ["user_id", "log_date"])
    op.create_index("idx_intake_user_food", "intake_logs", ["user_id", "food_id"])


def downgrade() -> None:
    op.drop_index("idx_intake_user_food", table_name="intake_logs")
    op.drop_index("idx_intake_user_date", table_name="intake_logs")
    op.drop_table("intake_logs")
    op.drop_index("idx_recipes_dish", table_name="food_recipes")
    op.drop_table("food_recipes")
    op.drop_index("idx_portions_food", table_name="food_portions")
    op.drop_table("food_portions")
    op.drop_index("idx_foods_barcode", table_name="foods")
    op.drop_index("idx_foods_aliases", table_name="foods")
    op.drop_index("idx_foods_role_tags", table_name="foods")
    op.drop_index("idx_foods_scene_tags", table_name="foods")
    op.drop_index("idx_foods_category", table_name="foods")
    op.drop_table("foods")
