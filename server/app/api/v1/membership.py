from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.exceptions import QuotaError
from app.core.responses import ok
from app.models.user import User
from app.services.quota import IMAGE_PARSE_DAILY_LIMIT
from app.services.recommend.engine import RECOMMEND_DAILY_LIMIT, SWAP_LIMIT

router = APIRouter(prefix="/membership", tags=["membership"])


@router.get("")
async def get_membership(_user: User = Depends(get_current_user)):
    return ok(
        {
            "plan": "free",
            "payment_enabled": False,
            "quotas": {
                "recommend_daily": RECOMMEND_DAILY_LIMIT,
                "swap_per_meal": SWAP_LIMIT,
                "parse_image_daily": IMAGE_PARSE_DAILY_LIMIT,
                "plan_days": 3,
            },
            "note": "虚拟支付尚未接入。当前全部功能可免费使用，配额用于防刷。",
        }
    )


@router.post("/checkout")
async def checkout(_user: User = Depends(get_current_user)):
    raise QuotaError("虚拟支付尚未开通，当前全部功能可免费使用")
