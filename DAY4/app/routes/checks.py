import csv
import io
from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import CheckResult, Monitor, utc_now
from app.schemas import CheckResultResponse

router = APIRouter(prefix="/api", tags=["checks"])


@router.get("/checks/recent", response_model=List[CheckResultResponse])
def get_recent_checks(
    limit: int = Query(20, ge=1, le=100),
    monitor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(CheckResult)
    if monitor_id:
        query = query.filter(CheckResult.monitor_id == monitor_id)
    return query.order_by(desc(CheckResult.checked_at)).limit(limit).all()


@router.get("/monitors/{monitor_id}/history", response_model=List[CheckResultResponse])
def get_monitor_history(
    monitor_id: int,
    hours: Optional[int] = Query(24, ge=1, le=720),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    query = db.query(CheckResult).filter(CheckResult.monitor_id == monitor_id)
    if hours:
        cutoff = utc_now() - timedelta(hours=hours)
        query = query.filter(CheckResult.checked_at >= cutoff)

    results = query.order_by(desc(CheckResult.checked_at)).offset(offset).limit(limit).all()
    return results


@router.get("/monitors/{monitor_id}/history/export")
def export_monitor_history_csv(
    monitor_id: int,
    hours: Optional[int] = Query(168, ge=1, le=720, description="Hours of history to export (default: 7 days)"),
    db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    query = db.query(CheckResult).filter(CheckResult.monitor_id == monitor_id)
    if hours:
        cutoff = utc_now() - timedelta(hours=hours)
        query = query.filter(CheckResult.checked_at >= cutoff)

    results = query.order_by(desc(CheckResult.checked_at)).all()

    # Generate CSV stream in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Check ID",
        "Monitor ID",
        "Monitor Name",
        "Timestamp (UTC)",
        "Status",
        "HTTP Status Code",
        "Response Time (ms)",
        "Error Category",
        "Error Message"
    ])

    for r in results:
        writer.writerow([
            r.id,
            monitor.id,
            monitor.name,
            r.checked_at.isoformat() if r.checked_at else "",
            "UP" if r.is_success else "DOWN",
            r.status_code if r.status_code is not None else "",
            r.response_time_ms,
            r.error_category or "",
            r.error_message or ""
        ])

    csv_data = output.getvalue()
    filename = f"uptimex_monitor_{monitor.id}_history.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
