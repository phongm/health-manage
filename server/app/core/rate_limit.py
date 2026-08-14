from collections import defaultdict
from time import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

WINDOW_SECONDS = 60
MAX_HITS = 60

_hits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in {"/healthz", "/docs", "/openapi.json"}:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time()
        recent = [stamp for stamp in _hits[ip] if now - stamp < WINDOW_SECONDS]
        if len(recent) >= MAX_HITS:
            _hits[ip] = recent
            return JSONResponse(
                status_code=429,
                content={"code": 4001, "message": "请求过于频繁，请稍后再试", "data": None},
            )
        recent.append(now)
        _hits[ip] = recent
        return await call_next(request)
