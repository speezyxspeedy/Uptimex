from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Incident, Monitor
from app.schemas import IncidentResponse

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[str] = Query(None, description="ACTIVE, RESOLVED, or ALL"),
    limit: int = Query(50, ge=1, le=200),
    monitor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Incident).join(Monitor, Incident.monitor_id == Monitor.id)

    if status and status.upper() in ("ACTIVE", "RESOLVED"):
        query = query.filter(Incident.status == status.upper())

    if monitor_id:
        query = query.filter(Incident.monitor_id == monitor_id)

    incidents = query.order_by(desc(Incident.started_at)).limit(limit).all()

    # Populate monitor metadata for rich UI display
    responses = []
    for inc in incidents:
        resp = IncidentResponse(
            id=inc.id,
            monitor_id=inc.monitor_id,
            monitor_name=inc.monitor.name if inc.monitor else None,
            monitor_url=inc.monitor.url if inc.monitor else None,
            started_at=inc.started_at,
            resolved_at=inc.resolved_at,
            duration_seconds=inc.duration_seconds,
            cause=inc.cause,
            status=inc.status
        )
        responses.append(resp)

    return responses
