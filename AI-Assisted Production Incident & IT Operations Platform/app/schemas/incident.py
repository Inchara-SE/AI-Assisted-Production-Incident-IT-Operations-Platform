"""Incident response, detail, status transition, and timeline schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentResponse(BaseModel):
    """Incident summary schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_key: str
    service_id: UUID
    service_key: str | None = None
    title: str
    description: str | None = None
    normalized_fingerprint: str
    fingerprint_version: int
    severity: Literal["critical", "high", "medium", "low"]
    status: Literal["open", "acknowledged", "investigating", "resolved"]
    first_alert_occurred_at: datetime
    last_alert_occurred_at: datetime
    first_acknowledged_at: datetime | None = None
    first_resolved_at: datetime | None = None
    resolved_at: datetime | None = None
    reopen_count: int
    created_at: datetime
    updated_at: datetime


class AlertEventSummary(BaseModel):
    """Summary of an alert event correlated to an incident."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    source_event_id: str
    alert_type: str
    severity: str
    resource: str | None = None
    message: str
    occurred_at: datetime
    is_repeat_alert: bool


class IncidentDetailResponse(IncidentResponse):
    """Detailed incident response with correlated alerts and alert count."""
    alert_events: list[AlertEventSummary] = Field(default_factory=list)
    alert_count: int = 0


class StatusTransitionRequest(BaseModel):
    """Request to transition incident lifecycle state per TAD Section 10.4.
    
    The caller does NOT supply from_status; it is read server-side under lock.
    """
    to_status: Literal["open", "acknowledged", "investigating", "resolved"]
    notes: str | None = Field(default=None, max_length=1000)


class TimelineEntry(BaseModel):
    """Single item in the incident timeline (alert event or lifecycle transition)."""
    entry_type: Literal["alert", "transition"]
    id: UUID
    timestamp: datetime
    summary: str
    actor_type: str | None = None
    actor_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class TimelineResponse(BaseModel):
    """Ordered chronological timeline of all events and transitions for an incident."""
    incident_id: UUID
    incident_key: str
    entries: list[TimelineEntry]
