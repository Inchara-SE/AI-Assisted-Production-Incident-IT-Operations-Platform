"""Service and ServiceDependency models in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident
    from app.models.runbook import Runbook
    from app.models.team import Team


class Service(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Monitored application or infrastructure service."""
    __tablename__ = "services"

    service_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_team_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.teams.id", ondelete="RESTRICT"),
        nullable=True,
    )
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), default="demo", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    owner_team: Mapped[Team | None] = relationship("Team", back_populates="services")
    incidents: Mapped[list[Incident]] = relationship("Incident", back_populates="service")
    runbooks: Mapped[list[Runbook]] = relationship("Runbook", back_populates="service")
    downstream_dependencies: Mapped[list[ServiceDependency]] = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.upstream_service_id",
        back_populates="upstream_service",
    )
    upstream_dependencies: Mapped[list[ServiceDependency]] = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.downstream_service_id",
        back_populates="downstream_service",
    )

    __table_args__ = (
        CheckConstraint(
            "criticality IN ('critical', 'high', 'medium', 'low')",
            name="ck_ops_services_criticality",
        ),
        Index("ix_ops_services_owner_team_id", "owner_team_id"),
    )


class ServiceDependency(Base, UUIDPrimaryKeyMixin):
    """Directed dependency edge: downstream depends on upstream."""
    __tablename__ = "service_dependencies"

    upstream_service_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    downstream_service_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.services.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dependency_type: Mapped[str] = mapped_column(String(40), nullable=False, default="runtime")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    upstream_service: Mapped[Service] = relationship(
        "Service",
        foreign_keys=[upstream_service_id],
        back_populates="downstream_dependencies",
    )
    downstream_service: Mapped[Service] = relationship(
        "Service",
        foreign_keys=[downstream_service_id],
        back_populates="upstream_dependencies",
    )

    __table_args__ = (
        UniqueConstraint(
            "upstream_service_id",
            "downstream_service_id",
            name="uq_ops_service_dependencies_upstream_downstream",
        ),
        CheckConstraint(
            "upstream_service_id != downstream_service_id",
            name="ck_ops_service_dependencies_no_self_reference",
        ),
        Index("ix_ops_service_dependencies_upstream", "upstream_service_id"),
        Index("ix_ops_service_dependencies_downstream", "downstream_service_id"),
    )
