"""Alert intake and response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _check_depth(val: Any, current_depth: int = 1, max_depth: int = 2) -> None:
    if current_depth > max_depth:
        raise ValueError(f"Metadata nesting exceeds maximum depth of {max_depth}")
    if isinstance(val, dict):
        for v in val.values():
            _check_depth(v, current_depth + 1, max_depth)
    elif isinstance(val, list):
        for item in val:
            _check_depth(item, current_depth + 1, max_depth)


class AlertIngestRequest(BaseModel):
    """Canonical alert ingestion payload per PRD Section 8 and TAD Section 10.2."""
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=80, description="Stable alert source identifier")
    source_event_id: str = Field(min_length=1, max_length=160, description="Source logical event identifier")
    service_key: str = Field(min_length=1, max_length=80, description="Target service key")
    alert_type: str = Field(min_length=1, max_length=80, description="Normalized alert taxonomy/category")
    severity: Literal["critical", "high", "medium", "low"] = Field(description="Alert severity")
    occurred_at: datetime = Field(description="Timezone-aware event occurrence timestamp")
    resource: str | None = Field(default=None, max_length=160, description="Optional safe resource name")
    message: str = Field(min_length=1, max_length=1000, description="Sanitized human-readable alert message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Bounded, allow-listed key-value context")

    @field_validator("occurred_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("occurred_at must include an explicit timezone offset (e.g., UTC 'Z')")
        return v.astimezone(timezone.utc)

    @field_validator("metadata")
    @classmethod
    def validate_metadata_bounds(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > 20:
            raise ValueError("metadata exceeds maximum limit of 20 keys")
        _check_depth(v, current_depth=1, max_depth=2)
        return v


class AlertIngestResponse(BaseModel):
    """Response returned by POST /api/v1/alerts per TAD Section 10.2."""
    model_config = ConfigDict(from_attributes=True)

    ingestion_outcome: Literal["accepted", "duplicate_delivery", "rejected"]
    duplicate_delivery: bool
    alert_event_id: UUID
    incident_id: UUID
    incident_key: str
    correlation_outcome: Literal["new_incident", "matched_existing_incident", "existing_event_replayed"]
    is_repeat_alert: bool
