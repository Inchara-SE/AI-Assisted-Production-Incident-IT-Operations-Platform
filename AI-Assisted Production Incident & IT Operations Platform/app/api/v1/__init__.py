"""API v1 router aggregator."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.runbooks import router as runbooks_router
from app.api.v1.services import router as services_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(runbooks_router)
api_v1_router.include_router(recommendations_router)

__all__ = ["api_v1_router"]
