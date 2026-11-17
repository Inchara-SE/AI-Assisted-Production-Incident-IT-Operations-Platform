"""Runbook management and search schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunbookCreate(BaseModel):
    """Create a logical runbook."""
    service_id: UUID | None = None
    slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None


class RunbookVersionCreate(BaseModel):
    """Create a new version draft for an existing runbook."""
    content_markdown: str = Field(min_length=10)


class RunbookPassageResponse(BaseModel):
    """Searchable passage chunk extracted from a runbook version."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordinal: int
    heading: str | None = None
    passage_text: str


class RunbookVersionResponse(BaseModel):
    """Runbook version with approval state and child passages."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    runbook_id: UUID
    version_number: int
    approval_status: Literal["draft", "approved", "retired"]
    created_by: UUID
    approved_by: UUID | None = None
    created_at: datetime
    approved_at: datetime | None = None
    passages: list[RunbookPassageResponse] = Field(default_factory=list)


class RunbookResponse(BaseModel):
    """Logical runbook schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID | None = None
    slug: str
    title: str
    description: str | None = None
    created_at: datetime
    versions: list[RunbookVersionResponse] = Field(default_factory=list)


class RunbookSearchResult(BaseModel):
    """Single full-text search match over approved runbook passages."""
    model_config = ConfigDict(from_attributes=True)

    runbook_id: UUID
    runbook_version_id: UUID
    runbook_slug: str
    title: str
    service_key: str | None = None
    passage_id: UUID
    passage_heading: str | None = None
    passage_text: str
    retrieval_rank: int
    score: float = Field(description="Diagnostic retrieval match score (not a probability)")


class RunbookSearchResponse(BaseModel):
    """Search results response."""
    query: str
    service_key: str | None = None
    total_matches: int
    results: list[RunbookSearchResult]
