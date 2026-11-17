"""Alert intake, exact delivery idempotency, fingerprinting, and correlation engine."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.alert_event import AlertEvent, AlertIngestionAttempt
from app.models.audit import AuditEvent
from app.models.incident import Incident
from app.models.incident_transition import IncidentTransition
from app.models.service import Service
from app.schemas.alert import AlertIngestRequest, AlertIngestResponse
from app.services.fingerprint import generate_fingerprint

# Severity rank order per PRD §7 (FR-04) and TAD §9.3
SEVERITY_ORDER = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def compute_max_severity(current: str, incoming: str) -> str:
    """Return the highest severity between current and incoming."""
    current_rank = SEVERITY_ORDER.get(current.lower(), 1)
    incoming_rank = SEVERITY_ORDER.get(incoming.lower(), 1)
    return incoming if incoming_rank > current_rank else current


def generate_incident_key(db: Session) -> str:
    """Generate sequential, collision-safe incident key (e.g. INC-000101)."""
    count = db.execute(select(func.count(Incident.id))).scalar() or 0
    return f"INC-{(count + 1):06d}"


def ingest_alert(
    db: Session,
    payload: AlertIngestRequest,
    request_id: str | None = None,
) -> tuple[AlertIngestResponse, int]:
    """Ingest, validate, deduplicate, and correlate an incoming alert.
    
    Returns (response_schema, http_status_code).
    """
    settings = get_settings()

    # Step 1: Compute deterministic SHA-256 payload hash
    raw_bytes = payload.model_dump_json(exclude_none=True).encode("utf-8")
    payload_hash = hashlib.sha256(raw_bytes).hexdigest()

    # Step 2: Validate service exists
    service = db.execute(
        select(Service).where(Service.service_key == payload.service_key)
    ).scalar_one_or_none()

    if not service:
        # Record rejected attempt
        attempt = AlertIngestionAttempt(
            source=payload.source,
            source_event_id=payload.source_event_id,
            payload_hash=payload_hash,
            outcome="rejected",
            request_id=request_id,
            validation_error_code="unknown_service",
        )
        db.add(attempt)
        db.flush()
        raise AppError(
            code="unknown_service",
            message=f"Service with key '{payload.service_key}' does not exist.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Step 3: Exact Delivery Idempotency Check via (source, source_event_id)
    existing_event = db.execute(
        select(AlertEvent).where(
            AlertEvent.source == payload.source,
            AlertEvent.source_event_id == payload.source_event_id,
        )
    ).scalar_one_or_none()

    if existing_event:
        # Record duplicate delivery replay attempt
        attempt = AlertIngestionAttempt(
            source=payload.source,
            source_event_id=payload.source_event_id,
            payload_hash=payload_hash,
            outcome="duplicate_delivery",
            alert_event_id=existing_event.id,
            request_id=request_id,
        )
        db.add(attempt)

        # Fetch parent incident
        incident = db.execute(
            select(Incident).where(Incident.id == existing_event.incident_id)
        ).scalar_one()

        db.flush()
        response = AlertIngestResponse(
            ingestion_outcome="duplicate_delivery",
            duplicate_delivery=True,
            alert_event_id=existing_event.id,
            incident_id=incident.id,
            incident_key=incident.incident_key,
            correlation_outcome="existing_event_replayed",
            is_repeat_alert=False,
        )
        return response, status.HTTP_200_OK

    # Step 4: New Logical Event — Generate normalized fingerprint
    fingerprint = generate_fingerprint(
        service_key=payload.service_key,
        alert_type=payload.alert_type,
        severity=payload.severity,
        resource=payload.resource,
    )

    # Step 5: Incident Correlation Search
    # Criteria: matching service, matching fingerprint, active status, within 15 min window
    window_minutes = settings.CORRELATION_WINDOW_MINUTES
    active_statuses = ("open", "acknowledged", "investigating")

    candidate_incidents = db.execute(
        select(Incident).where(
            Incident.service_id == service.id,
            Incident.normalized_fingerprint == fingerprint,
            Incident.status.in_(active_statuses),
        ).order_by(Incident.last_alert_occurred_at.desc())
    ).scalars().all()

    matched_incident: Incident | None = None
    for cand in candidate_incidents:
        time_diff = abs((payload.occurred_at - cand.last_alert_occurred_at).total_seconds())
        if time_diff <= (window_minutes * 60):
            matched_incident = cand
            break

    now = datetime.now(timezone.utc)
    is_repeat = False
    correlation_outcome = "new_incident"

    if matched_incident:
        # Correlate to existing incident
        is_repeat = True
        correlation_outcome = "matched_existing_incident"
        incident = matched_incident

        # Update last alert time and retain maximum severity
        if payload.occurred_at > incident.last_alert_occurred_at:
            incident.last_alert_occurred_at = payload.occurred_at
        incident.severity = compute_max_severity(incident.severity, payload.severity)
        incident.updated_at = now
    else:
        # Create brand new incident
        incident_key = generate_incident_key(db)
        incident = Incident(
            incident_key=incident_key,
            service_id=service.id,
            title=f"{service.name}: {payload.alert_type.replace('_', ' ').capitalize()}",
            description=payload.message,
            normalized_fingerprint=fingerprint,
            fingerprint_version=1,
            severity=payload.severity,
            status="open",
            first_alert_occurred_at=payload.occurred_at,
            last_alert_occurred_at=payload.occurred_at,
            reopen_count=0,
        )
        db.add(incident)
        db.flush()

        # Initial creation transition
        initial_trans = IncidentTransition(
            incident_id=incident.id,
            from_status=None,
            to_status="open",
            actor_type="system",
            request_id=request_id,
            notes="Incident automatically opened upon initial alert ingestion.",
            occurred_at=now,
        )
        db.add(initial_trans)

    # Step 6: Persist canonical alert event
    alert_event = AlertEvent(
        source=payload.source,
        source_event_id=payload.source_event_id,
        incident_id=incident.id,
        service_id=service.id,
        fingerprint=fingerprint,
        fingerprint_version=1,
        alert_type=payload.alert_type,
        severity=payload.severity,
        resource=payload.resource,
        message=payload.message,
        occurred_at=payload.occurred_at,
        payload_hash=payload_hash,
        normalized_metadata=payload.metadata,
        is_repeat_alert=is_repeat,
        correlation_reason="matched_fingerprint_window" if is_repeat else "new_incident",
    )
    db.add(alert_event)
    db.flush()

    # Step 7: Record accepted attempt
    attempt = AlertIngestionAttempt(
        source=payload.source,
        source_event_id=payload.source_event_id,
        payload_hash=payload_hash,
        outcome="accepted",
        alert_event_id=alert_event.id,
        request_id=request_id,
    )
    db.add(attempt)

    # Step 8: Append audit event
    audit = AuditEvent(
        actor_type="system",
        action="alert.ingested",
        entity_type="alert_event",
        entity_id=alert_event.id,
        request_id=request_id,
        metadata_={
            "source": payload.source,
            "source_event_id": payload.source_event_id,
            "incident_id": str(incident.id),
            "is_repeat": is_repeat,
            "correlation_outcome": correlation_outcome,
        },
        occurred_at=now,
    )
    db.add(audit)
    db.flush()

    response = AlertIngestResponse(
        ingestion_outcome="accepted",
        duplicate_delivery=False,
        alert_event_id=alert_event.id,
        incident_id=incident.id,
        incident_key=incident.incident_key,
        correlation_outcome=correlation_outcome,  # type: ignore[arg-type]
        is_repeat_alert=is_repeat,
    )
    return response, status.HTTP_201_CREATED
