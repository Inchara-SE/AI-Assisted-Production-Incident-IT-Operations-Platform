"""Runbook passage extraction and full-text search retrieval."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.runbook import Runbook, RunbookPassage, RunbookVersion


def extract_passages_from_markdown(content: str) -> list[dict[str, Any]]:
    """Parse Markdown content into bounded passages with headings and ordinals."""
    lines = content.splitlines()
    passages: list[dict[str, Any]] = []

    current_heading: str | None = None
    current_paragraphs: list[str] = []
    ordinal = 1

    for line in lines:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Flush existing passage if any
            if current_paragraphs:
                text_block = "\n".join(current_paragraphs).strip()
                if text_block:
                    passages.append({
                        "ordinal": ordinal,
                        "heading": current_heading,
                        "passage_text": text_block,
                    })
                    ordinal += 1
                current_paragraphs = []
            current_heading = heading_match.group(2).strip()
        else:
            if line.strip():
                current_paragraphs.append(line.strip())
            elif current_paragraphs:
                # Blank line indicates end of paragraph
                text_block = "\n".join(current_paragraphs).strip()
                if text_block:
                    passages.append({
                        "ordinal": ordinal,
                        "heading": current_heading,
                        "passage_text": text_block,
                    })
                    ordinal += 1
                current_paragraphs = []

    if current_paragraphs:
        text_block = "\n".join(current_paragraphs).strip()
        if text_block:
            passages.append({
                "ordinal": ordinal,
                "heading": current_heading,
                "passage_text": text_block,
            })

    return passages


def search_approved_runbooks(
    db: Session,
    query: str,
    service_id: UUID | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search approved runbook passages matching query terms.
    
    Filters strictly to approval_status = 'approved'.
    Supports service-specific relevance boost.
    """
    if not query.strip():
        return []

    # Query all approved passages with their versions and runbooks
    stmt = (
        select(RunbookPassage, RunbookVersion, Runbook)
        .join(RunbookVersion, RunbookVersion.id == RunbookPassage.runbook_version_id)
        .join(Runbook, Runbook.id == RunbookVersion.runbook_id)
        .where(RunbookVersion.approval_status == "approved")
    )
    if service_id is not None:
        stmt = stmt.where((Runbook.service_id == service_id) | (Runbook.service_id.is_(None)))

    rows = db.execute(stmt).all()

    query_words = set(re.findall(r"\w+", query.lower()))
    scored_results: list[dict[str, Any]] = []

    for passage, version, runbook in rows:
        passage_text_lower = passage.passage_text.lower()
        heading_lower = (passage.heading or "").lower()
        title_lower = runbook.title.lower()

        # Score matching words
        matches = sum(
            1 for w in query_words
            if w in passage_text_lower or w in heading_lower or w in title_lower
        )
        if matches > 0:
            # Service boost: 2.0x if runbook matches target service
            service_boost = 2.0 if (service_id and runbook.service_id == service_id) else 1.0
            score = float(matches) * service_boost

            scored_results.append({
                "runbook_id": runbook.id,
                "runbook_version_id": version.id,
                "runbook_slug": runbook.slug,
                "title": runbook.title,
                "service_id": runbook.service_id,
                "passage_id": passage.id,
                "passage_heading": passage.heading,
                "passage_text": passage.passage_text,
                "score": round(score, 2),
            })

    # Sort descending by score, deterministic tie-break by passage_id
    scored_results.sort(key=lambda x: (x["score"], str(x["passage_id"])), reverse=True)

    # Assign retrieval rank
    final_results = scored_results[:limit]
    for rank, item in enumerate(final_results, start=1):
        item["retrieval_rank"] = rank

    return final_results
