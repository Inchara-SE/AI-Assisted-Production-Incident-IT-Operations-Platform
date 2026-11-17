"""Recommendation generation and human review API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import require_role
from app.models.recommendation import Recommendation, RecommendationReview
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationOutput,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationReviewResponse,
    RecommendationSourceResponse,
    ReviewRequest,
    ReviewResponse,
)
from app.services.recommendation import (
    generate_recommendation_for_incident,
    review_recommendation,
)

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/incidents/{incident_id}/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_incident_recommendation(
    incident_id: UUID,
    payload: RecommendationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Generate advisory recommendation grounded in approved runbooks per TAD Section 10.6."""
    request_id = getattr(request.state, "request_id", None)
    rec = generate_recommendation_for_incident(
        db=db,
        incident_id=incident_id,
        top_k=payload.top_k,
        provider_name=payload.provider,
        request_id=request_id,
    )
    db.commit()

    return _build_recommendation_response(rec)


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Retrieve an existing recommendation with its sources and human review."""
    rec = db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    ).scalar_one_or_none()

    if not rec:
        raise AppError(
            code="recommendation_not_found",
            message=f"Recommendation '{recommendation_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return _build_recommendation_response(rec)


@router.post(
    "/recommendations/{recommendation_id}/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_recommendation_review(
    recommendation_id: UUID,
    payload: ReviewRequest,
    request: Request,
    current_user: User = Depends(require_role("on_call_engineer")),
    db: Session = Depends(get_db),
) -> ReviewResponse:
    """Record human review approval or rejection per TAD Section 10.8.
    
    Reviewer identity is derived exclusively from authentication.
    """
    request_id = getattr(request.state, "request_id", None)
    review = review_recommendation(
        db=db,
        recommendation_id=recommendation_id,
        reviewer_user_id=current_user.id,
        decision=payload.decision,
        notes=payload.notes,
        request_id=request_id,
    )
    db.commit()

    return ReviewResponse(
        recommendation_id=review.recommendation_id,
        decision=review.decision,  # type: ignore[arg-type]
        notes=review.notes,
        reviewed_at=review.reviewed_at,
        reviewer_id=review.reviewer_user_id,
    )


def _build_recommendation_response(rec: Recommendation) -> RecommendationResponse:
    sources_resp = [
        RecommendationSourceResponse(
            runbook_version_id=s.runbook_version_id,
            runbook_passage_id=s.runbook_passage_id,
            retrieval_rank=s.retrieval_rank,
            quoted_text_snapshot=s.quoted_text_snapshot,
        )
        for s in rec.sources
    ]

    review_resp = None
    if rec.review:
        review_resp = RecommendationReviewResponse(
            id=rec.review.id,
            reviewer_user_id=rec.review.reviewer_user_id,
            decision=rec.review.decision,  # type: ignore[arg-type]
            notes=rec.review.notes,
            reviewed_at=rec.review.reviewed_at,
        )

    output = None
    if rec.response_json:
        output = RecommendationOutput.model_validate(rec.response_json)

    return RecommendationResponse(
        id=rec.id,
        incident_id=rec.incident_id,
        provider=rec.provider,
        model=rec.model,
        prompt_version=rec.prompt_version,
        generation_status=rec.generation_status,  # type: ignore[arg-type]
        response_json=output,
        insufficient_evidence=rec.insufficient_evidence,
        citation_validation_status=rec.citation_validation_status,  # type: ignore[arg-type]
        latency_ms=rec.latency_ms,
        generated_at=rec.generated_at,
        sources=sources_resp,
        review=review_resp,
    )
