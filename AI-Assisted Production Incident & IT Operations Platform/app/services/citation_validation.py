"""Citation validation for grounded advisory recommendations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.runbook import RunbookPassage, RunbookVersion


class CitationValidationResult:
    def __init__(
        self,
        status: str,
        valid_citations: list[dict[str, Any]],
        invalid_citations: list[dict[str, Any]],
    ) -> None:
        self.status = status  # 'valid' | 'invalid' | 'no_sources' | 'not_applicable'
        self.valid_citations = valid_citations
        self.invalid_citations = invalid_citations


def validate_citations(
    db: Session,
    suggested_checks: list[Any],
    retrieved_candidate_passages: list[dict[str, Any]],
) -> CitationValidationResult:
    """Validate that every cited source passage:
    1. Exists in database.
    2. Belongs to an approved runbook version.
    3. Was present in the retrieved candidate passages supplied to the provider.
    """
    cited_passage_ids: list[UUID] = []
    for check in suggested_checks:
        pid = getattr(check, "source_passage_id", None)
        if pid:
            try:
                cited_passage_ids.append(UUID(str(pid)))
            except (ValueError, TypeError):
                pass

    if not cited_passage_ids:
        return CitationValidationResult(
            status="no_sources",
            valid_citations=[],
            invalid_citations=[],
        )

    retrieved_id_map = {
        UUID(str(p["passage_id"])): p for p in retrieved_candidate_passages if "passage_id" in p
    }

    # Query DB for passage and version status
    stmt = (
        select(RunbookPassage, RunbookVersion)
        .join(RunbookVersion, RunbookVersion.id == RunbookPassage.runbook_version_id)
        .where(RunbookPassage.id.in_(cited_passage_ids))
    )
    rows = db.execute(stmt).all()

    found_map = {passage.id: (passage, version) for passage, version in rows}

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    for pid in cited_passage_ids:
        # Check 1: In candidate set
        if pid not in retrieved_id_map:
            invalid.append({"passage_id": pid, "reason": "Not in retrieved candidate set"})
            continue

        # Check 2: Exists in DB
        if pid not in found_map:
            invalid.append({"passage_id": pid, "reason": "Passage not found in database"})
            continue

        passage, version = found_map[pid]

        # Check 3: Version is approved
        if version.approval_status != "approved":
            invalid.append({
                "passage_id": pid,
                "reason": f"Runbook version status is '{version.approval_status}', not 'approved'",
            })
            continue

        candidate_info = retrieved_id_map[pid]
        valid.append({
            "runbook_version_id": version.id,
            "runbook_passage_id": passage.id,
            "retrieval_rank": candidate_info.get("retrieval_rank", 1),
            "quoted_text_snapshot": passage.passage_text[:500],
        })

    status_str = "invalid" if invalid else "valid"
    return CitationValidationResult(
        status=status_str,
        valid_citations=valid,
        invalid_citations=invalid,
    )
