"""Runbook, RunbookVersion, and RunbookPassage models in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.service import Service
    from app.models.user import User


class Runbook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical troubleshooting guide/runbook."""
    __tablename__ = "runbooks"

    service_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.services.id", ondelete="RESTRICT"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    # Relationships
    service: Mapped[Service | None] = relationship("Service", back_populates="runbooks")
    versions: Mapped[list[RunbookVersion]] = relationship(
        "RunbookVersion",
        back_populates="runbook",
        order_by="RunbookVersion.version_number.desc()",
    )
    creator: Mapped[User | None] = relationship("User")

    __table_args__ = (
        Index("ix_ops_runbooks_service_id", "service_id"),
    )


class RunbookVersion(Base, UUIDPrimaryKeyMixin):
    """Immutable version of a runbook. Content cannot be edited once approved."""
    __tablename__ = "runbook_versions"

    runbook_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.runbooks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    # Relationships
    runbook: Mapped[Runbook] = relationship("Runbook", back_populates="versions")
    passages: Mapped[list[RunbookPassage]] = relationship(
        "RunbookPassage",
        back_populates="runbook_version",
        order_by="RunbookPassage.ordinal",
    )
    author: Mapped[User] = relationship("User", foreign_keys=[created_by])
    approver: Mapped[User | None] = relationship("User", foreign_keys=[approved_by])

    __table_args__ = (
        UniqueConstraint("runbook_id", "version_number", name="uq_ops_runbook_versions_runbook_version"),
        CheckConstraint(
            "approval_status IN ('draft', 'approved', 'retired')",
            name="ck_ops_runbook_versions_approval_status",
        ),
        CheckConstraint("version_number >= 1", name="ck_ops_runbook_versions_version_number"),
        Index("ix_ops_runbook_versions_runbook_version_desc", "runbook_id", "version_number"),
    )


class RunbookPassage(Base, UUIDPrimaryKeyMixin):
    """Searchable passage chunk extracted from a runbook version."""
    __tablename__ = "runbook_passages"

    runbook_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.runbook_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(200), nullable=True)
    passage_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    runbook_version: Mapped[RunbookVersion] = relationship("RunbookVersion", back_populates="passages")

    __table_args__ = (
        UniqueConstraint(
            "runbook_version_id",
            "ordinal",
            name="uq_ops_runbook_passages_version_ordinal",
        ),
        Index("ix_ops_runbook_passages_version", "runbook_version_id"),
    )
