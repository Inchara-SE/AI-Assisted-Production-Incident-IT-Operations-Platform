"""Common Pydantic models for error envelopes and pagination."""

from __future__ import annotations

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Inner error payload with machine code and request correlation ID."""
    model_config = ConfigDict(from_attributes=True)

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    model_config = ConfigDict(from_attributes=True)

    error: ErrorDetail


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    page: int = Field(default=1, ge=1, description="1-based page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Items per page (max 100)")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated items envelope."""
    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    page: int
    page_size: int
    total_count: int
    total_pages: int
