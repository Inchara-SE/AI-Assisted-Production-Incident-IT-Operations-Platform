"""OpsPilot FastAPI application entrypoint."""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import api_v1_router
from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    _handle_app_error,
    _handle_generic_error,
    _handle_http_exception,
    _handle_validation_error,
)
from app.core.logging import configure_logging

logger = structlog.get_logger("app")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns an incoming or freshly minted UUID request_id to request.state and response headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = req_id

        # Bind request_id to structlog contextvars
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = req_id
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests whose Content-Length exceeds MAX_REQUEST_SIZE_BYTES."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_REQUEST_SIZE_BYTES:
                    req_id = getattr(request.state, "request_id", None)
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "code": "request_too_large",
                                "message": f"Payload size exceeds maximum limit of {settings.MAX_REQUEST_SIZE_BYTES} bytes.",
                                "request_id": req_id,
                            }
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


def create_app() -> FastAPI:
    """FastAPI application factory."""
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="OpsPilot",
        version="0.1.0",
        description="Analytics-first IT operations platform with AI-assisted incident triage.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)

    # Exception Handlers
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_generic_error)

    # Routers
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
