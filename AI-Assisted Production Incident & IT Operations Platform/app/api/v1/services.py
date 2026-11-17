"""Service catalog and dependency API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import require_role
from app.models.service import Service, ServiceDependency
from app.schemas.service import (
    ServiceCreate,
    ServiceDependencyCreate,
    ServiceDependencyResponse,
    ServiceDetailResponse,
    ServiceResponse,
)
from app.services.catalog import add_service_dependency, create_service

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("", response_model=list[ServiceResponse])
def list_services(
    environment: str | None = Query(None),
    is_active: bool = Query(True),
    db: Session = Depends(get_db),
) -> list[ServiceResponse]:
    """List services registered in the catalog."""
    stmt = select(Service).where(Service.is_active == is_active)
    if environment:
        stmt = stmt.where(Service.environment == environment)
    stmt = stmt.order_by(Service.name.asc())

    services = db.execute(stmt).scalars().all()
    results = []
    for s in services:
        res = ServiceResponse.model_validate(s)
        res.owner_team_name = s.owner_team.name if s.owner_team else None
        results.append(res)
    return results


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def post_service(
    payload: ServiceCreate,
    _auth=Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> ServiceResponse:
    """Create a new service in the catalog (admin only)."""
    service = create_service(
        db=db,
        service_key=payload.service_key,
        name=payload.name,
        description=payload.description,
        owner_team_id=payload.owner_team_id,
        criticality=payload.criticality,
        environment=payload.environment,
    )
    db.commit()
    res = ServiceResponse.model_validate(service)
    res.owner_team_name = service.owner_team.name if service.owner_team else None
    return res


@router.get("/{service_id}", response_model=ServiceDetailResponse)
def get_service(
    service_id: UUID,
    db: Session = Depends(get_db),
) -> ServiceDetailResponse:
    """Retrieve service detail including directed dependencies."""
    service = db.execute(
        select(Service).where(Service.id == service_id)
    ).scalar_one_or_none()

    if not service:
        raise AppError(
            code="service_not_found",
            message=f"Service '{service_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Fetch dependencies
    up_deps = db.execute(
        select(ServiceDependency).where(ServiceDependency.downstream_service_id == service.id)
    ).scalars().all()
    down_deps = db.execute(
        select(ServiceDependency).where(ServiceDependency.upstream_service_id == service.id)
    ).scalars().all()

    upstream_responses = [
        ServiceDependencyResponse(
            id=d.id,
            upstream_service_id=d.upstream_service_id,
            upstream_service_key=d.upstream_service.service_key if d.upstream_service else None,
            downstream_service_id=d.downstream_service_id,
            downstream_service_key=d.downstream_service.service_key if d.downstream_service else None,
            dependency_type=d.dependency_type,
            created_at=d.created_at,
        )
        for d in up_deps
    ]

    downstream_responses = [
        ServiceDependencyResponse(
            id=d.id,
            upstream_service_id=d.upstream_service_id,
            upstream_service_key=d.upstream_service.service_key if d.upstream_service else None,
            downstream_service_id=d.downstream_service_id,
            downstream_service_key=d.downstream_service.service_key if d.downstream_service else None,
            dependency_type=d.dependency_type,
            created_at=d.created_at,
        )
        for d in down_deps
    ]

    res = ServiceDetailResponse.model_validate(service)
    res.owner_team_name = service.owner_team.name if service.owner_team else None
    res.upstream_dependencies = upstream_responses
    res.downstream_dependencies = downstream_responses
    return res
