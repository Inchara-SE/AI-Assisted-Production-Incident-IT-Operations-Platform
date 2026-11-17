"""AlertEvent and AlertIngestionAttempt models in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.service import Service


class AlertEvent(Base, UUIDPrimaryKeyMixin):
    """Canonical distinct accepted logical alert event."""
    __tablename__ = "alert_events"

    source: Mapped[str] = mapped_column(String(80), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    fingerprint_version: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(160), nullable=True)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    is_repeat_alert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    correlation_reason: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="alert_events")
    service: Mapped[Service] = relationship("Service")
    ingestion_attempts: Mapped[list[AlertIngestionAttempt]] = relationship(
        "AlertIngestionAttempt",
        back_populates="alert_event",
    )

    __table_args__ = (
        UniqueConstraint("source", "source_event_id", name="uq_ops_alert_events_source_event_id"),
        CheckConstraint(
            "severity IN ('critical', 'high', 'medium', 'low')",
            name="ck_ops_alert_events_severity",
        ),
        Index("ix_ops_alert_events_incident_occurred", "incident_id", "occurred_at"),
        Index("ix_ops_alert_events_svc_fp_occurred", "service_id", "fingerprint", "occurred_at"),
    )


class AlertIngestionAttempt(Base, UUIDPrimaryKeyMixin):
    """Delivery attempt for tracking intake, idempotency replays, and rejections."""
    __tablename__ = "alert_ingestion_attempts"

    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    alert_event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.alert_events.id", ondelete="RESTRICT"),
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    validation_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    alert_event: Mapped[AlertEvent | None] = relationship(
        "AlertEvent",
        back_populates="ingestion_attempts",
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('accepted', 'duplicate_delivery', 'rejected')",
            name="ck_ops_alert_ingestion_attempts_outcome",
        ),
        Index("ix_ops_alert_ingestion_attempts_received", "received_at"),
        Index("ix_ops_alert_ingestion_attempts_outcome_received", "outcome", "received_at"),
    )
