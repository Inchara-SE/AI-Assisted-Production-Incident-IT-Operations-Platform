"""Base recommendation provider protocol."""

from __future__ import annotations

from typing import Any, Protocol
from app.schemas.recommendation import RecommendationOutput


class RecommendationProvider(Protocol):
    """Protocol for AI recommendation generation providers."""

    def generate(
        self,
        incident_context: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> RecommendationOutput:
        """Generate structured recommendation from incident context and approved evidence."""
        ...
