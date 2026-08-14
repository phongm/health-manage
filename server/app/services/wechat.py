from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import AppError


@dataclass
class WeChatSession:
    openid: str
    unionid: str | None = None
    session_key: str | None = None


class WeChatClient:
    token_url = "https://api.weixin.qq.com/sns/jscode2session"

    async def code2session(self, code: str) -> WeChatSession:
        if settings.wechat_mock_login:
            return WeChatSession(openid=settings.wechat_mock_openid)

        if not settings.wechat_app_id or not settings.wechat_app_secret:
            raise AppError(5001, "微信登录未配置", status_code=500)

        params = {
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.token_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if "openid" not in data:
            err = data.get("errmsg", "微信登录失败")
            raise AppError(2002, err, status_code=401)
        return WeChatSession(
            openid=data["openid"],
            unionid=data.get("unionid"),
            session_key=data.get("session_key"),
        )


wechat_client = WeChatClient()
