"""OpsPilot Pydantic request and response schemas."""

from __future__ import annotations

from app.schemas.alert import AlertIngestRequest, AlertIngestResponse
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.incident import (
    IncidentDetailResponse,
    IncidentResponse,
    StatusTransitionRequest,
    TimelineEntry,
    TimelineResponse,
)
from app.schemas.recommendation import (
    PossibleContributor,
    RecommendationOutput,
    RecommendationRequest,
    RecommendationResponse,
    RecommendationReviewResponse,
    RecommendationSourceResponse,
    ReviewRequest,
    ReviewResponse,
    SuggestedCheck,
)
from app.schemas.runbook import (
    RunbookCreate,
    RunbookPassageResponse,
    RunbookResponse,
    RunbookSearchResponse,
    RunbookSearchResult,
    RunbookVersionCreate,
    RunbookVersionResponse,
)
from app.schemas.service import (
    ServiceCreate,
    ServiceDependencyCreate,
    ServiceDependencyResponse,
    ServiceDetailResponse,
    ServiceResponse,
)

__all__ = [
    "AlertIngestRequest",
    "AlertIngestResponse",
    "ErrorDetail",
    "ErrorResponse",
    "IncidentDetailResponse",
    "IncidentResponse",
    "LoginRequest",
    "PaginatedResponse",
    "PaginationParams",
    "PossibleContributor",
    "RecommendationOutput",
    "RecommendationRequest",
    "RecommendationResponse",
    "RecommendationReviewResponse",
    "RecommendationSourceResponse",
    "ReviewRequest",
    "ReviewResponse",
    "RunbookCreate",
    "RunbookPassageResponse",
    "RunbookResponse",
    "RunbookSearchResponse",
    "RunbookSearchResult",
    "RunbookVersionCreate",
    "RunbookVersionResponse",
    "ServiceCreate",
    "ServiceDependencyCreate",
    "ServiceDependencyResponse",
    "ServiceDetailResponse",
    "ServiceResponse",
    "StatusTransitionRequest",
    "SuggestedCheck",
    "TimelineEntry",
    "TimelineResponse",
    "TokenResponse",
    "UserResponse",
]
