"""Alert ingestion API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.alert import AlertIngestRequest, AlertIngestResponse
from app.services.alert_ingestion import ingest_alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("", response_model=AlertIngestResponse)
def post_alert(
    payload: AlertIngestRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AlertIngestResponse:
    """Ingest a canonical simulated alert payload per PRD Section 8 and TAD Section 10.2.
    
    Returns 201 Created for new canonical events.
    Returns 200 OK for exact delivery replays with zero duplicate event creation.
    """
    request_id = getattr(request.state, "request_id", None)
    result, status_code = ingest_alert(db=db, payload=payload, request_id=request_id)
    response.status_code = status_code
    db.commit()
    return result
