"""Configured LLM provider adapter with strict schema enforcement and fallback."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.providers.mock_provider import MockRecommendationProvider
from app.schemas.recommendation import RecommendationOutput


class ConfiguredLLMProvider:
    """LLM Provider adapter that uses OpenAI API if configured, falling back to mock provider."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._mock = MockRecommendationProvider()

    def generate(
        self,
        incident_context: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> RecommendationOutput:
        # If no API key or provider is mock, use deterministic mock
        if not self.settings.LLM_API_KEY or self.settings.LLM_PROVIDER == "mock":
            return self._mock.generate(incident_context, evidence)

        if not evidence:
            return self._mock.generate(incident_context, evidence)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.settings.LLM_API_KEY)

            system_prompt = (
                "You are an advisory IT operations triage assistant for OpsPilot.\n"
                "RULES:\n"
                "1. Output MUST be valid JSON adhering to the required schema.\n"
                "2. You MUST cite ONLY source_passage_id values present in the provided evidence.\n"
                "3. Never invent passage IDs or assume unproven root causes.\n"
                "4. All possible contributors are hypotheses, not confirmed facts.\n"
                "5. Never output shell scripts, remediation actions, or commands meant for execution.\n"
            )

            user_prompt = (
                f"Incident Context:\n{json.dumps(incident_context, indent=2)}\n\n"
                f"Retrieved Approved Runbook Evidence:\n{json.dumps(evidence, indent=2)}\n"
            )

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )

            content = completion.choices[0].message.content or "{}"
            parsed = json.loads(content)
            return RecommendationOutput.model_validate(parsed)
        except Exception:
            # Safe deterministic fallback
            return self._mock.generate(incident_context, evidence)
