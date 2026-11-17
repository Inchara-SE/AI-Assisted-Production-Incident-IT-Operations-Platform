"""Recommendation orchestration and human review service."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.audit import AuditEvent
from app.models.incident import Incident
from app.models.recommendation import (
    Recommendation,
    RecommendationReview,
    RecommendationSource,
)
from app.models.service import Service
from app.providers import get_recommendation_provider
from app.schemas.recommendation import RecommendationOutput
from app.services.citation_validation import validate_citations
from app.services.runbook_retrieval import search_approved_runbooks


def generate_recommendation_for_incident(
    db: Session,
    incident_id: UUID,
    top_k: int = 5,
    provider_name: str = "mock",
    request_id: str | None = None,
) -> Recommendation:
    """Generate advisory recommendation grounded in approved runbooks."""
    incident = db.execute(
        select(Incident).where(Incident.id == incident_id)
    ).scalar_one_or_none()

    if not incident:
        raise AppError(
            code="incident_not_found",
            message=f"Incident '{incident_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    service = db.execute(
        select(Service).where(Service.id == incident.service_id)
    ).scalar_one()

    # Step 1: Server-side approved runbook retrieval
    query_text = f"{service.service_key} {incident.title} {incident.description or ''}"
    retrieved_passages = search_approved_runbooks(
        db=db,
        query=query_text,
        service_id=service.id,
        limit=top_k,
    )

    incident_context = {
        "incident_id": str(incident.id),
        "incident_key": incident.incident_key,
        "service_key": service.service_key,
        "service_name": service.name,
        "title": incident.title,
        "description": incident.description,
        "severity": incident.severity,
        "status": incident.status,
    }

    # Step 2: Invoke provider
    provider = get_recommendation_provider(provider_name)
    start_time = time.perf_counter()

    try:
        output: RecommendationOutput = provider.generate(
            incident_context=incident_context,
            evidence=retrieved_passages,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        generation_status = "succeeded"
        error_code = None
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        output = RecommendationOutput(
            incident_summary="Provider invocation failed.",
            possible_contributors=[],
            suggested_checks=[],
            insufficient_evidence=True,
            limitations=[str(exc)],
        )
        generation_status = "failed"
        error_code = "provider_error"

    # Step 3: Citation validation
    validation_res = validate_citations(
        db=db,
        suggested_checks=output.suggested_checks,
        retrieved_candidate_passages=retrieved_passages,
    )

    now = datetime.now(timezone.utc)
    recommendation = Recommendation(
        incident_id=incident.id,
        provider=provider_name,
        model="mock-v1" if provider_name == "mock" else "gpt-4o-mini",
        prompt_version="1.0",
        generation_status=generation_status,
        response_json=output.model_dump(mode="json"),
        insufficient_evidence=output.insufficient_evidence,
        citation_validation_status=validation_res.status,
        latency_ms=latency_ms,
        error_code=error_code,
        request_id=request_id,
        generated_at=now,
    )
    db.add(recommendation)
    db.flush()

    # Step 4: Persist valid citation sources
    for cite in validation_res.valid_citations:
        rec_source = RecommendationSource(
            recommendation_id=recommendation.id,
            runbook_version_id=cite["runbook_version_id"],
            runbook_passage_id=cite["runbook_passage_id"],
            retrieval_rank=cite["retrieval_rank"],
            quoted_text_snapshot=cite["quoted_text_snapshot"],
            created_at=now,
        )
        db.add(rec_source)

    # Step 5: Audit record
    audit = AuditEvent(
        actor_type="system",
        action="recommendation.generated",
        entity_type="recommendation",
        entity_id=recommendation.id,
        request_id=request_id,
        metadata_={
            "incident_id": str(incident.id),
            "provider": provider_name,
            "status": generation_status,
            "citation_status": validation_res.status,
            "valid_citations_count": len(validation_res.valid_citations),
        },
        occurred_at=now,
    )
    db.add(audit)
    db.flush()

    return recommendation


def review_recommendation(
    db: Session,
    recommendation_id: UUID,
    reviewer_user_id: UUID,
    decision: Literal["approved", "rejected"],
    notes: str | None = None,
    request_id: str | None = None,
) -> RecommendationReview:
    """Record human approval or rejection of an advisory recommendation."""
    rec = db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    ).scalar_one_or_none()

    if not rec:
        raise AppError(
            code="recommendation_not_found",
            message=f"Recommendation '{recommendation_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Check for existing review (enforce 1 review per recommendation)
    existing_review = db.execute(
        select(RecommendationReview).where(
            RecommendationReview.recommendation_id == recommendation_id
        )
    ).scalar_one_or_none()

    if existing_review:
        raise AppError(
            code="already_reviewed",
            message=f"Recommendation '{recommendation_id}' has already been reviewed.",
            status_code=status.HTTP_409_CONFLICT,
        )

    now = datetime.now(timezone.utc)
    review = RecommendationReview(
        recommendation_id=recommendation_id,
        reviewer_user_id=reviewer_user_id,
        decision=decision,
        notes=notes,
        reviewed_at=now,
    )
    db.add(review)

    audit = AuditEvent(
        actor_type="user",
        actor_user_id=reviewer_user_id,
        action="recommendation.reviewed",
        entity_type="recommendation_review",
        entity_id=review.id,
        request_id=request_id,
        metadata_={
            "recommendation_id": str(recommendation_id),
            "decision": decision,
            "notes": notes,
        },
        occurred_at=now,
    )
    db.add(audit)
    db.flush()

    return review
