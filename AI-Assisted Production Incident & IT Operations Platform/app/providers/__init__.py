"""Provider abstractions and implementations."""

from __future__ import annotations

from app.providers.base import RecommendationProvider
from app.providers.configured_provider import ConfiguredLLMProvider
from app.providers.mock_provider import MockRecommendationProvider


def get_recommendation_provider(name: str = "mock") -> RecommendationProvider:
    """Factory returning the requested or configured provider."""
    if name == "mock":
        return MockRecommendationProvider()
    return ConfiguredLLMProvider()


__all__ = [
    "ConfiguredLLMProvider",
    "MockRecommendationProvider",
    "RecommendationProvider",
    "get_recommendation_provider",
]
