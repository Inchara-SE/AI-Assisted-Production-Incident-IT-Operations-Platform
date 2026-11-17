"""Service catalog, teams, and dependency graph service."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.service import Service, ServiceDependency
from app.models.team import Team


def get_service_by_key(db: Session, service_key: str) -> Service | None:
    """Retrieve service by unique service key."""
    stmt = select(Service).where(Service.service_key == service_key)
    return db.execute(stmt).scalar_one_or_none()


def create_service(
    db: Session,
    service_key: str,
    name: str,
    description: str | None = None,
    owner_team_id: UUID | None = None,
    criticality: str = "medium",
    environment: str = "demo",
) -> Service:
    """Create a new service in the catalog."""
    existing = get_service_by_key(db, service_key)
    if existing:
        raise AppError(
            code="service_already_exists",
            message=f"Service with key '{service_key}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    service = Service(
        service_key=service_key,
        name=name,
        description=description,
        owner_team_id=owner_team_id,
        criticality=criticality,
        environment=environment,
    )
    db.add(service)
    db.flush()
    return service


def add_service_dependency(
    db: Session,
    upstream_service_id: UUID,
    downstream_service_id: UUID,
    dependency_type: str = "runtime",
) -> ServiceDependency:
    """Add directed dependency edge: downstream depends on upstream."""
    if upstream_service_id == downstream_service_id:
        raise AppError(
            code="invalid_dependency",
            message="A service cannot depend on itself.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Check for existing dependency
    stmt = select(ServiceDependency).where(
        ServiceDependency.upstream_service_id == upstream_service_id,
        ServiceDependency.downstream_service_id == downstream_service_id,
    )
    if db.execute(stmt).scalar_one_or_none():
        raise AppError(
            code="dependency_already_exists",
            message="This directed dependency edge already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )

    dep = ServiceDependency(
        upstream_service_id=upstream_service_id,
        downstream_service_id=downstream_service_id,
        dependency_type=dependency_type,
    )
    db.add(dep)
    db.flush()
    return dep
