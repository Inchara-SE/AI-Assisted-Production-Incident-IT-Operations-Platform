"""Incident lifecycle state machine and transitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.incident import Incident
from app.models.incident_transition import IncidentTransition
from app.models.audit import AuditEvent

# Strict transition rules per PRD Section 7 (FR-05) and TAD Section 9.1
ALLOWED_TRANSITIONS: dict[str | None, set[str]] = {
    None: {"open"},
    "open": {"acknowledged", "investigating"},
    "acknowledged": {"investigating", "resolved"},
    "investigating": {"resolved"},
    "resolved": {"open"},  # Explicit reopen
}


def can_transition(from_status: str | None, to_status: str) -> bool:
    """Return True if the requested transition is permitted."""
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    return to_status in allowed


def transition_incident(
    db: Session,
    incident_id: UUID,
    to_status: Literal["open", "acknowledged", "investigating", "resolved"],
    actor_type: Literal["user", "system"] = "user",
    actor_user_id: UUID | None = None,
    notes: str | None = None,
    request_id: str | None = None,
) -> Incident:
    """Execute lifecycle transition within a transaction.
    
    Validates state under row lock, updates timestamps and reopen counters,
    and appends an immutable transition and audit record.
    """
    stmt = select(Incident).where(Incident.id == incident_id).with_for_update()
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise AppError(
            code="incident_not_found",
            message=f"Incident '{incident_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    current_status = incident.status

    if not can_transition(current_status, to_status):
        raise AppError(
            code="invalid_status_transition",
            message=(
                f"Transition from '{current_status}' to '{to_status}' is not permitted. "
                f"Allowed transitions from '{current_status}': {list(ALLOWED_TRANSITIONS.get(current_status, []))}."
            ),
            status_code=status.HTTP_409_CONFLICT,
        )

    now = datetime.now(timezone.utc)

    # Lifecycle timestamp semantics per PRD Section 9.2-9.3 and TAD Section 9.2
    if to_status == "acknowledged" and incident.first_acknowledged_at is None:
        incident.first_acknowledged_at = now

    if to_status == "resolved":
        if incident.first_resolved_at is None:
            incident.first_resolved_at = now
        incident.resolved_at = now
    elif current_status == "resolved" and to_status == "open":
        # Reopening: clear current resolved_at, increment reopen_count, preserve first_resolved_at
        incident.resolved_at = None
        incident.reopen_count += 1

    incident.status = to_status
    incident.updated_at = now

    # Append immutable transition record
    transition = IncidentTransition(
        incident_id=incident.id,
        from_status=current_status,
        to_status=to_status,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        notes=notes,
        request_id=request_id,
        occurred_at=now,
    )
    db.add(transition)

    # Append audit event
    audit = AuditEvent(
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        action="incident.status_transition",
        entity_type="incident",
        entity_id=incident.id,
        request_id=request_id,
        metadata_={
            "from_status": current_status,
            "to_status": to_status,
            "reopen_count": incident.reopen_count,
            "notes": notes,
        },
        occurred_at=now,
    )
    db.add(audit)

    db.flush()
    return incident
