from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler, unhandled_error_handler
from app.core.rate_limit import RateLimitMiddleware
from app.core.responses import ok

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(api_router, prefix="/api/health/v1")


@app.get("/healthz")
async def healthz():
    return ok({"status": "ok"})
