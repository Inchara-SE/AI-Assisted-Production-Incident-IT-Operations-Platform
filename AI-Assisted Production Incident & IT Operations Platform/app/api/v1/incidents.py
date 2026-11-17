"""Incident management, detail, transitions, and timeline API endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import get_current_user_optional
from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.models.incident_transition import IncidentTransition
from app.models.service import Service
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.incident import (
    AlertEventSummary,
    IncidentDetailResponse,
    IncidentResponse,
    StatusTransitionRequest,
    TimelineEntry,
    TimelineResponse,
)
from app.services.incident_lifecycle import transition_incident

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=PaginatedResponse[IncidentResponse])
def list_incidents(
    status: str | None = Query(None, description="Filter by status (open/acknowledged/investigating/resolved)"),
    severity: str | None = Query(None, description="Filter by severity (critical/high/medium/low)"),
    service_key: str | None = Query(None, description="Filter by service key"),
    created_from: datetime | None = Query(None, description="Created timestamp from"),
    created_to: datetime | None = Query(None, description="Created timestamp to"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = Query("created_at_desc", description="Sorting option"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[IncidentResponse]:
    """Search and list incidents with filters and bounded pagination."""
    stmt = select(Incident).join(Service, Service.id == Incident.service_id)

    if status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if service_key:
        stmt = stmt.where(Service.service_key == service_key)
    if created_from:
        stmt = stmt.where(Incident.created_at >= created_from)
    if created_to:
        stmt = stmt.where(Incident.created_at <= created_to)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.execute(count_stmt).scalar() or 0

    # Sorting
    if sort == "created_at_asc":
        stmt = stmt.order_by(Incident.created_at.asc())
    elif sort == "severity_desc":
        stmt = stmt.order_by(Incident.severity.desc(), Incident.created_at.desc())
    else:
        stmt = stmt.order_by(Incident.created_at.desc())

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    incidents = db.execute(stmt).scalars().all()

    items = []
    for inc in incidents:
        svc_key = inc.service.service_key if inc.service else None
        item = IncidentResponse.model_validate(inc)
        item.service_key = svc_key
        items.append(item)

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return PaginatedResponse[IncidentResponse](
        items=items,
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    """Retrieve full incident details including associated alert events."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise AppError(
            code="incident_not_found",
            message=f"Incident '{incident_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    alert_events = db.execute(
        select(AlertEvent)
        .where(AlertEvent.incident_id == incident.id)
        .order_by(AlertEvent.occurred_at.asc())
    ).scalars().all()

    summaries = [AlertEventSummary.model_validate(e) for e in alert_events]

    res = IncidentDetailResponse.model_validate(incident)
    res.service_key = incident.service.service_key if incident.service else None
    res.alert_events = summaries
    res.alert_count = len(summaries)
    return res


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def patch_incident_status(
    incident_id: UUID,
    payload: StatusTransitionRequest,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> IncidentResponse:
    """Request an allowed incident lifecycle state transition per TAD Section 10.4.
    
    Derives actor identity from authentication and validates state under lock.
    """
    request_id = getattr(request.state, "request_id", None)
    actor_id = current_user.id if current_user else None
    actor_type = "user" if current_user else "system"

    incident = transition_incident(
        db=db,
        incident_id=incident_id,
        to_status=payload.to_status,
        actor_type=actor_type,
        actor_user_id=actor_id,
        notes=payload.notes,
        request_id=request_id,
    )
    db.commit()

    res = IncidentResponse.model_validate(incident)
    res.service_key = incident.service.service_key if incident.service else None
    return res


@router.get("/{incident_id}/timeline", response_model=TimelineResponse)
def get_incident_timeline(
    incident_id: UUID,
    db: Session = Depends(get_db),
) -> TimelineResponse:
    """Retrieve chronologically unified timeline of alerts and lifecycle transitions."""
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = db.execute(stmt).scalar_one_or_none()

    if not incident:
        raise AppError(
            code="incident_not_found",
            message=f"Incident '{incident_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Fetch alert events
    alerts = db.execute(
        select(AlertEvent)
        .where(AlertEvent.incident_id == incident.id)
        .order_by(AlertEvent.occurred_at.asc())
    ).scalars().all()

    # Fetch transitions
    transitions = db.execute(
        select(IncidentTransition)
        .where(IncidentTransition.incident_id == incident.id)
        .order_by(IncidentTransition.occurred_at.asc())
    ).scalars().all()

    entries: list[TimelineEntry] = []

    for a in alerts:
        entries.append(
            TimelineEntry(
                entry_type="alert",
                id=a.id,
                timestamp=a.occurred_at,
                summary=f"Alert: {a.alert_type} ({a.severity}) - {a.message}",
                actor_type="system",
                actor_name=a.source,
                details={
                    "source": a.source,
                    "source_event_id": a.source_event_id,
                    "is_repeat_alert": a.is_repeat_alert,
                    "resource": a.resource,
                },
            )
        )

    for t in transitions:
        actor_name = t.actor_user.display_name if t.actor_user else t.actor_type
        summary = (
            f"Status transition: {t.from_status or 'initial'} -> {t.to_status}"
            if t.from_status
            else f"Incident opened ({t.to_status})"
        )
        entries.append(
            TimelineEntry(
                entry_type="transition",
                id=t.id,
                timestamp=t.occurred_at,
                summary=summary,
                actor_type=t.actor_type,
                actor_name=actor_name,
                details={
                    "from_status": t.from_status,
                    "to_status": t.to_status,
                    "notes": t.notes,
                },
            )
        )

    # Sort chronological
    entries.sort(key=lambda x: x.timestamp)

    return TimelineResponse(
        incident_id=incident.id,
        incident_key=incident.incident_key,
        entries=entries,
    )
