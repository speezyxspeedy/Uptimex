import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.database import get_db
from app.models import Monitor, CheckResult, utc_now
from app.schemas import (
    MonitorCreate,
    MonitorUpdate,
    MonitorResponse,
    CheckResultResponse,
)
from app.scheduler import schedule_monitor, unschedule_monitor
from app.monitor_service import perform_monitor_check

router = APIRouter(prefix="/api/monitors", tags=["monitors"])


@router.get("", response_model=List[MonitorResponse])
def list_monitors(
    q: Optional[str] = Query(None, description="Search query by name or URL"),
    status: Optional[str] = Query(None, description="Filter by status: UP, DOWN, PAUSED, PENDING"),
    sort_by: str = Query("created_at", description="Sort field: created_at, name, response_time, last_check, status"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(get_db)
):
    query = db.query(Monitor)

    if q:
        search = f"%{q.strip()}%"
        query = query.filter((Monitor.name.ilike(search)) | (Monitor.url.ilike(search)))

    if status:
        stat_upper = status.strip().upper()
        if stat_upper == "PAUSED":
            query = query.filter(Monitor.is_enabled == False)
        elif stat_upper in ("UP", "DOWN", "PENDING"):
            query = query.filter(Monitor.current_status == stat_upper, Monitor.is_enabled == True)

    order_col = Monitor.created_at
    if sort_by == "name":
        order_col = Monitor.name
    elif sort_by == "response_time":
        order_col = Monitor.last_response_time_ms
    elif sort_by == "last_check":
        order_col = Monitor.last_check_at
    elif sort_by == "status":
        order_col = Monitor.current_status

    if sort_order.lower() == "asc":
        query = query.order_by(asc(order_col))
    else:
        query = query.order_by(desc(order_col))

    return query.all()


@router.post("", response_model=MonitorResponse, status_code=status.HTTP_201_CREATED)
async def create_monitor(
    payload: MonitorCreate,
    db: Session = Depends(get_db)
):
    monitor = Monitor(
        name=payload.name.strip(),
        url=payload.url.strip(),
        interval_seconds=payload.interval_seconds,
        timeout_seconds=payload.timeout_seconds,
        method=payload.method,
        expected_status_codes=payload.expected_status_codes,
        is_enabled=True,
        current_status="PENDING",
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    # Schedule periodic checks in background
    schedule_monitor(monitor.id, monitor.interval_seconds)

    # Trigger initial check asynchronously right away so user sees instant result
    try:
        asyncio.create_task(perform_monitor_check(monitor.id))
    except RuntimeError:
        pass

    return monitor


@router.get("/{monitor_id}", response_model=MonitorResponse)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.put("/{monitor_id}", response_model=MonitorResponse)
def update_monitor(
    monitor_id: int,
    payload: MonitorUpdate,
    db: Session = Depends(get_db)
):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    if payload.name is not None:
        monitor.name = payload.name.strip()
    if payload.url is not None:
        monitor.url = payload.url.strip()
    if payload.interval_seconds is not None:
        monitor.interval_seconds = payload.interval_seconds
    if payload.timeout_seconds is not None:
        monitor.timeout_seconds = payload.timeout_seconds
    if payload.method is not None:
        monitor.method = payload.method
    if payload.expected_status_codes is not None:
        monitor.expected_status_codes = payload.expected_status_codes
    if payload.is_enabled is not None:
        monitor.is_enabled = payload.is_enabled
        if not monitor.is_enabled:
            monitor.current_status = "PAUSED"
            unschedule_monitor(monitor.id)
        else:
            if monitor.current_status == "PAUSED":
                monitor.current_status = "PENDING"
            schedule_monitor(monitor.id, monitor.interval_seconds)

    monitor.updated_at = utc_now()
    db.commit()
    db.refresh(monitor)

    # Reschedule with updated interval if enabled
    if monitor.is_enabled:
        schedule_monitor(monitor.id, monitor.interval_seconds)

    return monitor


@router.delete("/{monitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    unschedule_monitor(monitor.id)
    db.delete(monitor)
    db.commit()
    return None


@router.post("/{monitor_id}/check", response_model=CheckResultResponse)
async def trigger_manual_check(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    result = await perform_monitor_check(monitor_id)
    if not result:
        # Check might already be running, fetch latest check result
        latest = db.query(CheckResult).filter(CheckResult.monitor_id == monitor_id).order_by(desc(CheckResult.checked_at)).first()
        if latest:
            return latest
        raise HTTPException(status_code=409, detail="A check is currently in progress for this monitor.")

    return result


@router.post("/{monitor_id}/toggle", response_model=MonitorResponse)
async def toggle_monitor_status(monitor_id: int, db: Session = Depends(get_db)):
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor.is_enabled = not monitor.is_enabled
    if not monitor.is_enabled:
        monitor.current_status = "PAUSED"
        unschedule_monitor(monitor.id)
    else:
        monitor.current_status = "PENDING"
        schedule_monitor(monitor.id, monitor.interval_seconds)
        try:
            asyncio.create_task(perform_monitor_check(monitor.id))
        except RuntimeError:
            pass

    monitor.updated_at = utc_now()
    db.commit()
    db.refresh(monitor)
    return monitor
