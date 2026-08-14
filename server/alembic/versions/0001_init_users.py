"""Initial users / profiles / preferences

Revision ID: 0001_init_users
Revises:
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_init_users"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("openid", sa.String(64), nullable=False),
        sa.Column("unionid", sa.String(64), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("openid", name="uq_users_openid"),
    )
    op.create_index(
        "idx_users_unionid",
        "users",
        ["unionid"],
        postgresql_where=sa.text("unionid IS NOT NULL"),
    )

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("gender", sa.SmallInteger(), nullable=False),
        sa.Column("birth_year", sa.SmallInteger(), nullable=False),
        sa.Column("height_cm", sa.Numeric(5, 1), nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 1), nullable=False),
        sa.Column("body_fat_pct", sa.Numeric(4, 1), nullable=True),
        sa.Column("activity_level", sa.SmallInteger(), nullable=False),
        sa.Column("goal", sa.SmallInteger(), nullable=False),
        sa.Column("goal_rate_kg_wk", sa.Numeric(3, 2), server_default="0.5", nullable=False),
        sa.Column("target_weight_kg", sa.Numeric(5, 1), nullable=True),
        sa.Column("bmr_kcal", sa.Numeric(7, 1), nullable=True),
        sa.Column("tdee_kcal", sa.Numeric(7, 1), nullable=True),
        sa.Column("target_kcal", sa.Numeric(7, 1), nullable=True),
        sa.Column("target_nutrients", postgresql.JSONB(), nullable=True),
        sa.Column("is_excluded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("exclude_reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("allergens", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "avoid_ingredients", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column(
            "avoid_categories", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'"), nullable=False
        ),
        sa.Column("diet_type", sa.String(32), nullable=True),
        sa.Column("spice_level", sa.SmallInteger(), server_default="2", nullable=False),
        sa.Column("scene_default", sa.String(16), server_default="'takeout'", nullable=False),
        sa.Column("scene_by_meal", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_table("user_profiles")
    op.drop_index("idx_users_unionid", table_name="users")
    op.drop_table("users")
