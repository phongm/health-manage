"""usage events and client op idempotency

Revision ID: 0004_usage
Revises: 0003_tracking
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_usage"
down_revision: Union[str, Sequence[str], None] = "0003_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_usage_user_kind_created", "usage_events", ["user_id", "kind", "created_at"])
    op.create_table(
        "client_ops",
        sa.Column("client_op_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("client_ops")
    op.drop_index("idx_usage_user_kind_created", table_name="usage_events")
    op.drop_table("usage_events")
