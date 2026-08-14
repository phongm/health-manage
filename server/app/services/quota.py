from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import QuotaError
from app.models.tracking import UsageEvent

IMAGE_PARSE_DAILY_LIMIT = 3


async def count_usage_today(db: AsyncSession, user_id: int, kind: str, day: date | None = None) -> int:
    day = day or datetime.now(UTC).date()
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    value = await db.scalar(
        select(func.count()).where(
            UsageEvent.user_id == user_id,
            UsageEvent.kind == kind,
            UsageEvent.created_at >= start,
            UsageEvent.created_at < end,
        )
    )
    return int(value or 0)


async def consume_usage(
    db: AsyncSession,
    user_id: int,
    kind: str,
    limit: int,
    message: str,
) -> None:
    used = await count_usage_today(db, user_id, kind)
    if used >= limit:
        raise QuotaError(message)
    db.add(UsageEvent(user_id=user_id, kind=kind))
    await db.commit()
