from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.responses import ok
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.wechat import wechat_client

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    session = await wechat_client.code2session(body.code)
    user = await db.scalar(
        select(User).options(selectinload(User.profile)).where(User.openid == session.openid)
    )
    is_new = user is None
    if is_new:
        user = User(openid=session.openid, unionid=session.unionid)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return ok(
        {
            "token": create_access_token(user.id),
            "is_new_user": is_new,
            "profile_completed": False if is_new else user.profile is not None,
        }
    )
