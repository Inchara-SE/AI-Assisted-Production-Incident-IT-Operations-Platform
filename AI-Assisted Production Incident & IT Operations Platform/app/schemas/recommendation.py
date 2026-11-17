"""Recommendation, provider output, and human review schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationRequest(BaseModel):
    """Trigger recommendation generation for an incident."""
    top_k: int = Field(default=5, ge=1, le=10, description="Max approved passages to retrieve")
    provider: str = Field(default="mock", description="Provider adapter (mock or configured)")


class PossibleContributor(BaseModel):
    """Hypothesis regarding potential failure contributor. Not a confirmed root cause."""
    hypothesis: str
    confidence_label: Literal["high", "medium", "low"] = "medium"


class SuggestedCheck(BaseModel):
    """Actionable diagnostic verification step citing an approved runbook passage."""
    step: str
    reason: str
    source_passage_id: UUID | None = None


class RecommendationOutput(BaseModel):
    """Structured provider output per TAD Section 10.7."""
    model_config = ConfigDict(extra="forbid")

    incident_summary: str
    possible_contributors: list[PossibleContributor] = Field(default_factory=list)
    suggested_checks: list[SuggestedCheck] = Field(default_factory=list)
    insufficient_evidence: bool = False
    limitations: list[str] = Field(default_factory=list)


class RecommendationSourceResponse(BaseModel):
    """Evidence citation linking recommendation to an approved passage."""
    model_config = ConfigDict(from_attributes=True)

    runbook_version_id: UUID
    runbook_passage_id: UUID
    retrieval_rank: int
    quoted_text_snapshot: str


class RecommendationReviewResponse(BaseModel):
    """Human review decision."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reviewer_user_id: UUID
    decision: Literal["approved", "rejected"]
    notes: str | None = None
    reviewed_at: datetime


class RecommendationResponse(BaseModel):
    """Complete advisory recommendation record."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    provider: str
    model: str | None = None
    prompt_version: str
    generation_status: Literal["succeeded", "failed"]
    response_json: RecommendationOutput | None = None
    insufficient_evidence: bool
    citation_validation_status: Literal["valid", "invalid", "no_sources", "not_applicable"]
    latency_ms: int | None = None
    generated_at: datetime
    sources: list[RecommendationSourceResponse] = Field(default_factory=list)
    review: RecommendationReviewResponse | None = None


class ReviewRequest(BaseModel):
    """Human review submission. Reviewer is derived from authenticated user."""
    decision: Literal["approved", "rejected"]
    notes: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    """Confirmation of recorded human review."""
    recommendation_id: UUID
    decision: Literal["approved", "rejected"]
    notes: str | None = None
    reviewed_at: datetime
    reviewer_id: UUID
