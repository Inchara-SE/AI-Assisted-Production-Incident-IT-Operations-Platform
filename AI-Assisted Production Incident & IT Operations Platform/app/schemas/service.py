"""Service and service dependency schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    """Schema for creating a service (admin only)."""
    service_key: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    owner_team_id: UUID | None = None
    criticality: Literal["critical", "high", "medium", "low"] = "medium"
    environment: str = Field(default="demo", max_length=40)


class ServiceResponse(BaseModel):
    """Service representation schema."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_key: str
    name: str
    description: str | None = None
    owner_team_id: UUID | None = None
    owner_team_name: str | None = None
    criticality: str
    environment: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceDependencyCreate(BaseModel):
    """Schema for creating a directed dependency between two services."""
    upstream_service_id: UUID
    downstream_service_id: UUID
    dependency_type: str = Field(default="runtime", max_length=40)


class ServiceDependencyResponse(BaseModel):
    """Schema representing a directed dependency edge."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    upstream_service_id: UUID
    upstream_service_key: str | None = None
    downstream_service_id: UUID
    downstream_service_key: str | None = None
    dependency_type: str
    created_at: datetime


class ServiceDetailResponse(ServiceResponse):
    """Service detail including upstream and downstream dependencies."""
    upstream_dependencies: list[ServiceDependencyResponse] = Field(default_factory=list)
    downstream_dependencies: list[ServiceDependencyResponse] = Field(default_factory=list)
