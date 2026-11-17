"""Health check endpoint distinguishing application readiness without leaking DSN."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.database import check_database_connection

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(response: Response) -> dict[str, str]:
    """Verify application readiness and database connectivity."""
    db_ok = check_database_connection()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database": "disconnected",
        }
    return {
        "status": "healthy",
        "database": "connected",
    }
