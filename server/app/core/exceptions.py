from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, message: str = "未登录或登录已过期"):
        super().__init__(code=2001, message=message, status_code=401)


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=3002, message=message, status_code=404)


class ExcludedUserError(AppError):
    def __init__(self, message: str = "当前版本暂不为该情况提供饮食建议，建议咨询专业人士"):
        super().__init__(code=3001, message=message, status_code=403)


class QuotaError(AppError):
    def __init__(self, message: str = "今日次数已用完"):
        super().__init__(code=4001, message=message, status_code=429)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": 9001, "message": "服务暂时不可用", "data": None},
    )
