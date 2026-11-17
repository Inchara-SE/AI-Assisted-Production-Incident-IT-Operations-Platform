"""Recommendation, RecommendationSource, and RecommendationReview models in ops schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
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
    from app.models.runbook import RunbookPassage, RunbookVersion
    from app.models.user import User


class Recommendation(Base, UUIDPrimaryKeyMixin):
    """Advisory recommendation generated for an incident."""
    __tablename__ = "recommendations"

    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.incidents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    insufficient_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    citation_validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="recommendations")
    sources: Mapped[list[RecommendationSource]] = relationship(
        "RecommendationSource",
        back_populates="recommendation",
        order_by="RecommendationSource.retrieval_rank",
    )
    review: Mapped[RecommendationReview | None] = relationship(
        "RecommendationReview",
        back_populates="recommendation",
        uselist=False,
    )

    __table_args__ = (
        CheckConstraint(
            "generation_status IN ('succeeded', 'failed')",
            name="ck_ops_recommendations_generation_status",
        ),
        CheckConstraint(
            "citation_validation_status IN ('valid', 'invalid', 'no_sources', 'not_applicable')",
            name="ck_ops_recommendations_citation_status",
        ),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_ops_recommendations_latency"),
        Index("ix_ops_recommendations_incident_generated", "incident_id", "generated_at"),
    )


class RecommendationSource(Base, UUIDPrimaryKeyMixin):
    """Citation link mapping a recommendation to an approved runbook passage."""
    __tablename__ = "recommendation_sources"

    recommendation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.recommendations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    runbook_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.runbook_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    runbook_passage_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.runbook_passages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    retrieval_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    quoted_text_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    recommendation: Mapped[Recommendation] = relationship("Recommendation", back_populates="sources")
    runbook_version: Mapped[RunbookVersion] = relationship("RunbookVersion")
    runbook_passage: Mapped[RunbookPassage] = relationship("RunbookPassage")

    __table_args__ = (
        CheckConstraint("retrieval_rank >= 1", name="ck_ops_recommendation_sources_rank"),
        Index("ix_ops_recommendation_sources_rec_id", "recommendation_id"),
    )


class RecommendationReview(Base, UUIDPrimaryKeyMixin):
    """Human decision approving or rejecting an advisory recommendation."""
    __tablename__ = "recommendation_reviews"

    recommendation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.recommendations.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    reviewer_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ops.users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # Relationships
    recommendation: Mapped[Recommendation] = relationship("Recommendation", back_populates="review")
    reviewer: Mapped[User] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_ops_recommendation_reviews_decision",
        ),
        Index("ix_ops_recommendation_reviews_reviewer", "reviewer_user_id"),
    )
