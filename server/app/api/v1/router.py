from fastapi import APIRouter

from app.api.v1.activity import router as activity_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import dashboard_router, parse_router
from app.api.v1.foods import router as foods_router
from app.api.v1.intake import router as intake_router
from app.api.v1.preferences import router as preferences_router
from app.api.v1.profile import router as profile_router
from app.api.v1.membership import router as membership_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.report import router as report_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(preferences_router)
api_router.include_router(foods_router)
api_router.include_router(intake_router)
api_router.include_router(dashboard_router)
api_router.include_router(parse_router)
api_router.include_router(recommend_router)
api_router.include_router(activity_router)
api_router.include_router(report_router)
api_router.include_router(membership_router)
