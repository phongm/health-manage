from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import parse_access_token
from app.db.session import get_db
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AuthError()
    user_id = parse_access_token(creds.credentials)
    user = await db.scalar(select(User).where(User.id == user_id, User.status == 1))
    if user is None:
        raise AuthError("用户不存在或已禁用")
    return user
