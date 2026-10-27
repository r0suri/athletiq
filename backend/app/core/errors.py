"""One error format for every failure.

Every error response has the shape:
    {"error": {"code": ..., "message": ..., "details": [...], "request_id": ...}}
so clients handle errors in one place and support can trace a request by id.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationAppError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


def _envelope(
    request: Request, status: int, code: str, message: str, details: list | None = None
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }
    }
    headers = {"X-Request-Id": request_id} if request_id else None
    return JSONResponse(status_code=status, content=body, headers=headers)


def _field_path(loc: tuple) -> str:
    # ("body", "exercises", 0, "reps") -> "exercises.0.reps"; drop the source prefix
    # and pydantic's discriminator tags like "run"/"strength".
    parts = [str(p) for p in loc if p not in ("body", "query", "path")]
    if len(parts) > 1 and parts[0] in ("run", "ride", "strength"):
        parts = parts[1:]
    return ".".join(parts)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": _field_path(tuple(e.get("loc", ()))), "issue": e.get("msg", "invalid")}
            for e in exc.errors()
        ]
        return _envelope(request, 422, "VALIDATION_ERROR", "Request validation failed.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        code = codes.get(exc.status_code, "HTTP_ERROR")
        message = "Resource not found." if exc.status_code == 404 else str(exc.detail)
        return _envelope(request, exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the full exception server-side; never leak internals to the client.
        logger.exception("unhandled error", path=request.url.path)
        return _envelope(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
