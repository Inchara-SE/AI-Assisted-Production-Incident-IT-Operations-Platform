"""Deterministic mock recommendation provider for offline reproducibility and CI."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.recommendation import (
    PossibleContributor,
    RecommendationOutput,
    SuggestedCheck,
)


class MockRecommendationProvider:
    """Deterministic recommendation provider.
    
    Guarantees:
    - Zero cost, zero network dependencies, 100% reproducible.
    - If evidence is empty: returns insufficient_evidence=True with zero citations.
    - If evidence is present: cites only IDs from the supplied candidate evidence passages.
    - Suggests hypotheses, never claims unproven root cause.
    """

    def generate(
        self,
        incident_context: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> RecommendationOutput:
        service_key = incident_context.get("service_key", "unknown-service")
        title = incident_context.get("title", "Service alert")
        severity = incident_context.get("severity", "medium")
        alert_type = incident_context.get("alert_type", "general_failure")

        # Scenario 1: Insufficient Evidence Fallback
        if not evidence:
            return RecommendationOutput(
                incident_summary=(
                    f"Elevated {severity} incident on service '{service_key}' ({title}). "
                    "No relevant approved runbooks were retrieved."
                ),
                possible_contributors=[
                    PossibleContributor(
                        hypothesis=f"Anomalous behavior detected in {service_key} ({alert_type}).",
                        confidence_label="low",
                    )
                ],
                suggested_checks=[],
                insufficient_evidence=True,
                limitations=[
                    "No approved troubleshooting runbooks matched the incident query.",
                    "No raw infrastructure telemetry was supplied directly to OpsPilot.",
                    "Guidance is advisory and requires human investigation.",
                ],
            )

        # Scenario 2: Grounded Recommendation with Valid Citations
        contributors = [
            PossibleContributor(
                hypothesis=(
                    f"Service '{service_key}' may be experiencing resource exhaustion or "
                    f"downstream latency causing {alert_type}."
                ),
                confidence_label="high" if severity in ("critical", "high") else "medium",
            )
        ]

        suggested_checks: list[SuggestedCheck] = []
        for rank, passage in enumerate(evidence[:3], start=1):
            passage_id_str = passage.get("passage_id")
            passage_id = UUID(str(passage_id_str)) if passage_id_str else None
            heading = passage.get("passage_heading") or f"Check #{rank}"

            suggested_checks.append(
                SuggestedCheck(
                    step=f"Execute verification for '{heading}'.",
                    reason=f"Approved runbook passage #{rank} details standard remediation for this alert signature.",
                    source_passage_id=passage_id,
                )
            )

        return RecommendationOutput(
            incident_summary=f"Investigating {severity} incident on '{service_key}': {title}.",
            possible_contributors=contributors,
            suggested_checks=suggested_checks,
            insufficient_evidence=False,
            limitations=[
                "Citations strictly reflect retrieved approved runbook passages.",
                "Advisory guidance only: does not execute production actions or changes.",
            ],
        )
