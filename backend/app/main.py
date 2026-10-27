"""FastAPI application and the AWS Lambda entry point.

`app` is a normal ASGI app (run locally with uvicorn).
`handler` adapts API Gateway HTTP API events to ASGI via Mangum, so the exact
same code runs locally and in Lambda.
"""

import time

from aws_lambda_powertools.logging import correlation_paths
from fastapi import FastAPI, Request
from mangum import Mangum

from app.api.routes import health
from app.core.config import get_settings
from app.core.logging import logger

API_PREFIX = "/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AthletIQ API",
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        logger.info(
            "request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        return response

    app.include_router(health.router, prefix=API_PREFIX)
    return app


app = create_app()
_asgi_handler = Mangum(app, lifespan="off")


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_HTTP, clear_state=True
)
def handler(event: dict, context: object) -> dict:
    """Lambda entry point referenced by template.yaml (app.main.handler)."""
    return _asgi_handler(event, context)
