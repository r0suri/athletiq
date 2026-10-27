"""FastAPI application and the AWS Lambda entry point.

`app` is a normal ASGI app (run locally with uvicorn).
`handler` adapts API Gateway HTTP API events to ASGI via Mangum, so the exact
same code runs locally and in Lambda.
"""

import time
import uuid

from aws_lambda_powertools.logging import correlation_paths
from fastapi import FastAPI, Request
from mangum import Mangum

from app.api.routes import checkins, health, workouts
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import logger

API_PREFIX = "/v1"


def create_app() -> FastAPI:
    # Loading settings here means a forbidden configuration (e.g. AUTH_MODE=local in
    # AWS) fails at startup, before any request is served.
    settings = get_settings()
    app = FastAPI(
        title="AthletIQ API",
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        event = request.scope.get("aws.event") or {}
        request_id = event.get("requestContext", {}).get("requestId") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-Id"] = request_id
            return response
        finally:
            # Metadata only: never log request bodies (they contain health-related data).
            logger.info(
                "request completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                request_id=request_id,
            )

    register_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(workouts.router, prefix=API_PREFIX)
    app.include_router(checkins.router, prefix=API_PREFIX)
    return app


app = create_app()
_asgi_handler = Mangum(app, lifespan="off")


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_HTTP, clear_state=True
)
def handler(event: dict, context: object) -> dict:
    """Lambda entry point referenced by template.yaml (app.main.handler)."""
    return _asgi_handler(event, context)
