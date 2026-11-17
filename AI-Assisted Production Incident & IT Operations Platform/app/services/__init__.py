"""OpsPilot business logic services."""

from __future__ import annotations

from app.services.alert_ingestion import ingest_alert
from app.services.catalog import (
    add_service_dependency,
    create_service,
    get_service_by_key,
)
from app.services.citation_validation import validate_citations
from app.services.fingerprint import generate_fingerprint
from app.services.incident_lifecycle import can_transition, transition_incident
from app.services.recommendation import (
    generate_recommendation_for_incident,
    review_recommendation,
)
from app.services.runbook_retrieval import (
    extract_passages_from_markdown,
    search_approved_runbooks,
)

__all__ = [
    "add_service_dependency",
    "can_transition",
    "create_service",
    "extract_passages_from_markdown",
    "generate_fingerprint",
    "generate_recommendation_for_incident",
    "get_service_by_key",
    "ingest_alert",
    "review_recommendation",
    "search_approved_runbooks",
    "transition_incident",
    "validate_citations",
]
