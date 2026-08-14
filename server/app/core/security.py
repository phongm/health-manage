from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import AuthError


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def parse_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            raise AuthError()
        return int(sub)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise AuthError() from exc
