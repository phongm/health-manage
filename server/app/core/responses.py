from typing import Any

from fastapi.responses import JSONResponse


def ok(data: Any = None, message: str = "ok") -> JSONResponse:
    return JSONResponse(status_code=200, content={"code": 0, "message": message, "data": data})
