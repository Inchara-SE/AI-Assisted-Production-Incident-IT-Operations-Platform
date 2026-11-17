"""Centralised error envelope and FastAPI exception handlers.

Error responses follow the contract::

    {
      "error": {
        "code": "stable_machine_code",
        "message": "Human-readable explanation.",
        "request_id": "<request-id>"
      }
    }
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ── Error schema ─────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    """Inner detail of the error envelope."""
    code: str
    message: str
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    """Standard error envelope returned by every error handler."""
    error: ErrorDetail


# ── Custom application exception ─────────────────────────────────────────────

class AppError(Exception):
    """Raise from service/repository layers with a machine code and HTTP status."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _build_envelope(code: str, message: str, request: Request) -> dict:
    return ErrorEnvelope(
        error=ErrorDetail(code=code, message=message, request_id=_request_id(request)),
    ).model_dump(mode="json")


# ── Exception handlers ──────────────────────────────────────────────────────

logger = structlog.get_logger("errors")


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "app_error",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_envelope(exc.code, exc.message, request),
    )


async def _handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    code = "http_error"
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_envelope(code, message, request),
    )


async def _handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    # Build a safe human-readable summary — do not expose raw payload.
    summary_parts: list[str] = []
    for err in errors:
        loc = " -> ".join(str(p) for p in err.get("loc", []))
        msg = err.get("msg", "validation error")
        summary_parts.append(f"{loc}: {msg}")
    summary = "; ".join(summary_parts) if summary_parts else "Validation error."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_envelope("validation_error", summary, request),
    )


async def _handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        request_id=_request_id(request),
        error=str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_envelope(
            "internal_error",
            "An unexpected error occurred.",
            request,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to the FastAPI application."""
    app.add_exception_handler(AppError, _handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, _handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unhandled_exception)  # type: ignore[arg-type]
