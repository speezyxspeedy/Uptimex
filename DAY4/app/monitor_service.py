import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, Set
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.config import settings
from app.database import SessionLocal
from app.models import Monitor, CheckResult, Incident, utc_now
from app.schemas import parse_status_code_spec
from app.security import (
    validate_target_url,
    validate_redirect_target,
    SecurityValidationError,
)

# In-memory lock to prevent overlapping checks for the same monitor
_running_checks: Set[int] = set()
_running_lock = asyncio.Lock()

# Global semaphore to limit concurrent outbound checks
_check_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_CHECKS)


async def execute_http_check(
    url: str,
    method: str,
    timeout_seconds: int,
    expected_status_codes: str
) -> Tuple[bool, Optional[int], float, Optional[str], Optional[str]]:
    """
    Executes a real server-side HTTP/HTTPS check with strict SSRF protection,
    redirect validation, and timing.

    Returns:
        (is_success, status_code, response_time_ms, error_category, error_message)
    """
    expected_codes = parse_status_code_spec(expected_status_codes)
    current_url = url
    max_redirects = 5
    redirect_count = 0
    start_time = time.perf_counter()

    # Step 1: Pre-request SSRF validation on initial URL
    try:
        current_url = validate_target_url(current_url)
    except SecurityValidationError as sve:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "SECURITY_BLOCKED_DESTINATION", str(sve)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "INVALID_URL", "Target URL could not be validated."

    # Step 2: Outbound HTTP request execution loop with manual redirect handling
    # We enforce verify=True (TLS check) and per-request timeout.
    timeout_config = httpx.Timeout(
        connect=min(5.0, float(timeout_seconds)),
        read=float(timeout_seconds),
        write=5.0,
        pool=5.0
    )

    headers = {
        "User-Agent": "UptimeX-Monitor/1.0 (+https://github.com/uptimex/monitor)",
        "Accept": "*/*",
        "Connection": "close"
    }

    try:
        async with httpx.AsyncClient(
            verify=True,
            follow_redirects=False,
            timeout=timeout_config
        ) as client:
            while True:
                req_method = method.upper() if redirect_count == 0 else "GET"
                
                req_start = time.perf_counter()
                response = await client.request(
                    method=req_method,
                    url=current_url,
                    headers=headers
                )
                
                # Check for redirects
                if response.is_redirect and "location" in response.headers:
                    redirect_count += 1
                    if redirect_count > max_redirects:
                        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        return False, response.status_code, elapsed_ms, "TOO_MANY_REDIRECTS", f"Exceeded maximum of {max_redirects} redirects."
                    
                    loc = response.headers["location"]
                    try:
                        # Re-validate destination IP of the redirect target
                        current_url = validate_redirect_target(current_url, loc)
                    except SecurityValidationError as sve:
                        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        return False, response.status_code, elapsed_ms, "SECURITY_BLOCKED_DESTINATION", f"Redirect to unsafe destination blocked: {sve}"
                    continue

                # Final response received
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                status = response.status_code

                if status in expected_codes:
                    return True, status, elapsed_ms, None, None
                else:
                    return False, status, elapsed_ms, "HTTP_STATUS_MISMATCH", f"Returned status {status}, expected {expected_status_codes}."

    except httpx.ConnectTimeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "CONNECTION_TIMEOUT", f"Connection timed out after {timeout_seconds}s."

    except httpx.ReadTimeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "READ_TIMEOUT", f"Read timed out after {timeout_seconds}s."

    except httpx.ConnectError:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "CONNECTION_REFUSED", "Failed to connect to host (connection refused or network unreachable)."

    except httpx.InvalidURL:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return False, None, elapsed_ms, "INVALID_URL", "URL syntax or domain name is invalid."

    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        err_type = type(exc).__name__
        if "ssl" in err_type.lower() or "certificate" in str(exc).lower():
            return False, None, elapsed_ms, "SSL_CERTIFICATE_ERROR", "TLS/SSL certificate verification failed."
        return False, None, elapsed_ms, "NETWORK_ERROR", "A network communication error occurred."


async def perform_monitor_check(monitor_id: int) -> Optional[CheckResult]:
    """
    Carries out a check for the given monitor, updates status, records history,
    and manages active/resolved incidents.
    Guarantees no overlapping check for the same monitor_id.
    """
    async with _running_lock:
        if monitor_id in _running_checks:
            return None
        _running_checks.add(monitor_id)

    db: Session = SessionLocal()
    try:
        async with _check_semaphore:
            monitor: Optional[Monitor] = db.query(Monitor).filter(Monitor.id == monitor_id).first()
            if not monitor or not monitor.is_enabled:
                return None

            url = monitor.url
            method = monitor.method
            timeout_sec = monitor.timeout_seconds
            expected_codes = monitor.expected_status_codes
            prev_status = monitor.current_status

        # Perform the actual HTTP check asynchronously
        is_success, status_code, elapsed_ms, err_cat, err_msg = await execute_http_check(
            url=url,
            method=method,
            timeout_seconds=timeout_sec,
            expected_status_codes=expected_codes
        )

        check_time = utc_now()

        # Record check result in database
        check_result = CheckResult(
            monitor_id=monitor.id,
            checked_at=check_time,
            status_code=status_code,
            response_time_ms=elapsed_ms,
            is_success=is_success,
            error_category=err_cat,
            error_message=err_msg
        )
        db.add(check_result)

        # Handle monitor status transitions & incident tracking
        if is_success:
            new_status = "UP"
            # If transitioning from DOWN to UP, resolve active incident
            if prev_status == "DOWN":
                active_incident = db.query(Incident).filter(
                    and_(Incident.monitor_id == monitor.id, Incident.status == "ACTIVE")
                ).first()
                if active_incident:
                    active_incident.resolved_at = check_time
                    active_incident.duration_seconds = max(
                        1, int((check_time - active_incident.started_at.replace(tzinfo=timezone.utc if active_incident.started_at.tzinfo is None else None)).total_seconds())
                    )
                    active_incident.status = "RESOLVED"
        else:
            new_status = "DOWN"
            # If transitioning to DOWN from UP or PENDING, open an incident if none currently active
            if prev_status in ("UP", "PENDING"):
                existing_active = db.query(Incident).filter(
                    and_(Incident.monitor_id == monitor.id, Incident.status == "ACTIVE")
                ).first()
                if not existing_active:
                    cause_desc = err_msg or err_cat or "Check failed"
                    incident = Incident(
                        monitor_id=monitor.id,
                        started_at=check_time,
                        cause=cause_desc[:255],
                        status="ACTIVE"
                    )
                    db.add(incident)

        # Update monitor state
        monitor.current_status = new_status
        monitor.last_check_at = check_time
        monitor.last_response_time_ms = elapsed_ms
        monitor.last_status_code = status_code
        monitor.last_error = err_cat
        monitor.updated_at = check_time

        db.commit()
        db.refresh(check_result)
        return check_result

    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()
        async with _running_lock:
            _running_checks.discard(monitor_id)


def prune_old_check_history(retention_days: int) -> int:
    """
    Deletes check results older than retention_days.
    """
    db: Session = SessionLocal()
    try:
        cutoff = utc_now() - timedelta(days=retention_days)
        deleted = db.query(CheckResult).filter(CheckResult.checked_at < cutoff).delete()
        db.commit()
        return deleted
    finally:
        db.close()
