"""Runbook management, versioning, approval, and search API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import require_role
from app.models.runbook import Runbook, RunbookPassage, RunbookVersion
from app.models.service import Service
from app.models.user import User
from app.schemas.runbook import (
    RunbookCreate,
    RunbookPassageResponse,
    RunbookResponse,
    RunbookSearchResponse,
    RunbookSearchResult,
    RunbookVersionCreate,
    RunbookVersionResponse,
)
from app.services.runbook_retrieval import (
    extract_passages_from_markdown,
    search_approved_runbooks,
)

router = APIRouter(tags=["Runbooks"])


@router.get("/runbooks/search", response_model=RunbookSearchResponse)
def search_runbooks(
    q: str = Query(..., min_length=1, max_length=200, description="Keyword search query"),
    service_key: str | None = Query(None, description="Optional target service key for boost"),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
) -> RunbookSearchResponse:
    """Full-text search over approved runbook passages with service relevance weighting."""
    service_id = None
    if service_key:
        svc = db.execute(
            select(Service).where(Service.service_key == service_key)
        ).scalar_one_or_none()
        if svc:
            service_id = svc.id

    raw_results = search_approved_runbooks(
        db=db,
        query=q,
        service_id=service_id,
        limit=limit,
    )

    results = []
    for r in raw_results:
        results.append(
            RunbookSearchResult(
                runbook_id=r["runbook_id"],
                runbook_version_id=r["runbook_version_id"],
                runbook_slug=r["runbook_slug"],
                title=r["title"],
                service_key=service_key if r.get("service_id") else None,
                passage_id=r["passage_id"],
                passage_heading=r["passage_heading"],
                passage_text=r["passage_text"],
                retrieval_rank=r["retrieval_rank"],
                score=r["score"],
            )
        )

    return RunbookSearchResponse(
        query=q,
        service_key=service_key,
        total_matches=len(results),
        results=results,
    )


@router.post("/runbooks", response_model=RunbookResponse, status_code=status.HTTP_201_CREATED)
def post_runbook(
    payload: RunbookCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> RunbookResponse:
    """Create a new logical runbook (admin only)."""
    # Check slug uniqueness
    existing = db.execute(
        select(Runbook).where(Runbook.slug == payload.slug)
    ).scalar_one_or_none()
    if existing:
        raise AppError(
            code="runbook_slug_exists",
            message=f"Runbook with slug '{payload.slug}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    runbook = Runbook(
        service_id=payload.service_id,
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(runbook)
    db.commit()
    db.refresh(runbook)

    return RunbookResponse.model_validate(runbook)


@router.post("/runbooks/{runbook_id}/versions", response_model=RunbookVersionResponse, status_code=status.HTTP_201_CREATED)
def post_runbook_version(
    runbook_id: UUID,
    payload: RunbookVersionCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> RunbookVersionResponse:
    """Create a draft version for an existing runbook (admin only)."""
    runbook = db.execute(
        select(Runbook).where(Runbook.id == runbook_id)
    ).scalar_one_or_none()
    if not runbook:
        raise AppError(
            code="runbook_not_found",
            message=f"Runbook '{runbook_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Determine next version number
    max_ver = db.execute(
        select(func.max(RunbookVersion.version_number))
        .where(RunbookVersion.runbook_id == runbook_id)
    ).scalar() or 0
    next_ver = max_ver + 1

    version = RunbookVersion(
        runbook_id=runbook.id,
        version_number=next_ver,
        content_markdown=payload.content_markdown,
        approval_status="draft",
        created_by=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    return RunbookVersionResponse.model_validate(version)


@router.post("/runbook-versions/{version_id}/approve", response_model=RunbookVersionResponse)
def approve_runbook_version(
    version_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> RunbookVersionResponse:
    """Approve and publish a runbook version, extracting immutable passage chunks."""
    version = db.execute(
        select(RunbookVersion).where(RunbookVersion.id == version_id)
    ).scalar_one_or_none()

    if not version:
        raise AppError(
            code="version_not_found",
            message=f"Runbook version '{version_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if version.approval_status == "approved":
        return RunbookVersionResponse.model_validate(version)

    now = datetime.now(timezone.utc)
    version.approval_status = "approved"
    version.approved_by = current_user.id
    version.approved_at = now

    # Extract passages from Markdown
    passages_data = extract_passages_from_markdown(version.content_markdown)
    for p in passages_data:
        passage = RunbookPassage(
            runbook_version_id=version.id,
            ordinal=p["ordinal"],
            heading=p["heading"],
            passage_text=p["passage_text"],
        )
        db.add(passage)

    db.commit()
    db.refresh(version)

    return RunbookVersionResponse.model_validate(version)
