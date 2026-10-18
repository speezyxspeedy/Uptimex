from datetime import timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.database import get_db
from app.models import Monitor, CheckResult, Incident, utc_now
from app.schemas import (
    DashboardSummary,
    AnalyticsResponse,
    TimeseriesPoint,
)

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns high-level operational metrics calculated from actual real-time database state.
    """
    total_monitors = db.query(Monitor).count()
    up_count = db.query(Monitor).filter(Monitor.current_status == "UP", Monitor.is_enabled == True).count()
    down_count = db.query(Monitor).filter(Monitor.current_status == "DOWN", Monitor.is_enabled == True).count()
    paused_count = db.query(Monitor).filter(Monitor.is_enabled == False).count()
    pending_count = db.query(Monitor).filter(Monitor.current_status == "PENDING", Monitor.is_enabled == True).count()
    active_incidents_count = db.query(Incident).filter(Incident.status == "ACTIVE").count()

    # Calculate overall average response time from monitors with recorded check times
    avg_resp = db.query(func.avg(Monitor.last_response_time_ms)).filter(
        and_(Monitor.is_enabled == True, Monitor.last_response_time_ms.isnot(None))
    ).scalar()

    # Calculate aggregate 24-hour uptime percentage across all monitors
    cutoff_24h = utc_now() - timedelta(hours=24)
    total_checks_24h = db.query(func.count(CheckResult.id)).filter(CheckResult.checked_at >= cutoff_24h).scalar() or 0
    success_checks_24h = db.query(func.count(CheckResult.id)).filter(
        and_(CheckResult.checked_at >= cutoff_24h, CheckResult.is_success == True)
    ).scalar() or 0

    overall_uptime = None
    if total_checks_24h > 0:
        overall_uptime = round((success_checks_24h / total_checks_24h) * 100, 2)

    return DashboardSummary(
        total_monitors=total_monitors,
        up_count=up_count,
        down_count=down_count,
        paused_count=paused_count,
        pending_count=pending_count,
        overall_avg_response_time=round(avg_resp, 2) if avg_resp is not None else None,
        overall_uptime_24h=overall_uptime,
        active_incidents_count=active_incidents_count
    )


@router.get("/monitors/{monitor_id}/analytics", response_model=AnalyticsResponse)
def get_monitor_analytics(
    monitor_id: int,
    hours: int = Query(24, ge=1, le=720, description="Analytics time window in hours (1, 6, 24, 168, 720)"),
    db: Session = Depends(get_db)
):
    """
    Returns analytical calculations for a specific monitor within the selected time window.
    Strictly reports real recorded checks. If insufficient history exists, states 'Insufficient data'.
    """
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    cutoff = utc_now() - timedelta(hours=hours)
    
    # Query all checks in time window, ordered chronologically
    checks = db.query(CheckResult).filter(
        and_(CheckResult.monitor_id == monitor_id, CheckResult.checked_at >= cutoff)
    ).order_by(CheckResult.checked_at.asc()).all()

    total_checks = len(checks)
    success_checks = sum(1 for c in checks if c.is_success)
    failed_checks = total_checks - success_checks

    if total_checks > 0:
        uptime_pct = round((success_checks / total_checks) * 100, 2)
        uptime_display = f"{uptime_pct:.2f}%"
        
        response_times = [c.response_time_ms for c in checks if c.response_time_ms is not None]
        avg_resp = round(sum(response_times) / len(response_times), 2) if response_times else None
        min_resp = round(min(response_times), 2) if response_times else None
        max_resp = round(max(response_times), 2) if response_times else None
    else:
        uptime_pct = None
        uptime_display = "Insufficient data"
        avg_resp = None
        min_resp = None
        max_resp = None

    # Sample timeseries points for clean chart rendering (up to 120 points)
    timeseries: List[TimeseriesPoint] = []
    if checks:
        step = max(1, len(checks) // 120)
        sampled = checks[::step]
        # Always ensure latest check is included
        if checks[-1] not in sampled:
            sampled.append(checks[-1])
            
        timeseries = [
            TimeseriesPoint(
                timestamp=c.checked_at,
                response_time_ms=c.response_time_ms,
                is_success=c.is_success,
                status_code=c.status_code
            )
            for c in sampled
        ]

    return AnalyticsResponse(
        monitor_id=monitor.id,
        monitor_name=monitor.name,
        time_window_hours=hours,
        uptime_percentage=uptime_pct,
        uptime_display=uptime_display,
        avg_response_time_ms=avg_resp,
        min_response_time_ms=min_resp,
        max_response_time_ms=max_resp,
        total_checks=total_checks,
        success_checks=success_checks,
        failed_checks=failed_checks,
        latest_status_code=monitor.last_status_code,
        timeseries=timeseries
    )
