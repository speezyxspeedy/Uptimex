import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError

from app.database import SessionLocal
from app.models import Monitor
from app.monitor_service import perform_monitor_check, prune_old_check_history
from app.config import settings

logger = logging.getLogger("uptimex.scheduler")

scheduler: Optional[AsyncIOScheduler] = None


async def _run_scheduled_check(monitor_id: int):
    try:
        await perform_monitor_check(monitor_id)
    except Exception as exc:
        logger.error(f"Error during scheduled check for monitor {monitor_id}: {exc}", exc_info=True)


async def _run_retention_cleanup():
    try:
        pruned = prune_old_check_history(settings.DATA_RETENTION_DAYS)
        logger.info(f"Data retention cleanup completed: {pruned} old check records pruned.")
    except Exception as exc:
        logger.error(f"Error during retention cleanup: {exc}", exc_info=True)


def get_job_id(monitor_id: int) -> str:
    return f"check_monitor_{monitor_id}"


def schedule_monitor(monitor_id: int, interval_seconds: int):
    """
    Adds or updates a monitor's periodic check in the scheduler.
    """
    if not scheduler or not scheduler.running:
        return

    job_id = get_job_id(monitor_id)
    try:
        scheduler.add_job(
            _run_scheduled_check,
            "interval",
            seconds=max(10, interval_seconds),
            args=[monitor_id],
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(timezone.utc)
        )
        logger.info(f"Scheduled monitor {monitor_id} with interval {interval_seconds}s")
    except Exception as exc:
        logger.error(f"Failed to schedule monitor {monitor_id}: {exc}")


def unschedule_monitor(monitor_id: int):
    """
    Removes a monitor's periodic check from the scheduler.
    """
    if not scheduler or not scheduler.running:
        return

    job_id = get_job_id(monitor_id)
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Unscheduled monitor {monitor_id}")
    except JobLookupError:
        pass
    except Exception as exc:
        logger.error(f"Failed to unschedule monitor {monitor_id}: {exc}")


def is_scheduler_running() -> bool:
    return scheduler is not None and scheduler.running


def start_scheduler():
    """
    Initializes and starts the AsyncIOScheduler, restoring jobs for all enabled monitors.
    """
    global scheduler
    if scheduler and scheduler.running:
        return

    scheduler = AsyncIOScheduler()

    # Load all enabled monitors and schedule them
    db = SessionLocal()
    try:
        enabled_monitors = db.query(Monitor).filter(Monitor.is_enabled == True).all()
        for mon in enabled_monitors:
            job_id = get_job_id(mon.id)
            scheduler.add_job(
                _run_scheduled_check,
                "interval",
                seconds=max(10, mon.interval_seconds),
                args=[mon.id],
                id=job_id,
                replace_existing=True,
                coalesce=True,
                max_instances=1
            )
        
        # Schedule daily data retention maintenance
        scheduler.add_job(
            _run_retention_cleanup,
            "interval",
            hours=24,
            id="retention_prune_job",
            replace_existing=True
        )

        scheduler.start()
        logger.info(f"UptimeX Scheduler started with {len(enabled_monitors)} active monitors restored.")
    except Exception as exc:
        logger.error(f"Error starting scheduler: {exc}", exc_info=True)
    finally:
        db.close()


def stop_scheduler():
    """
    Stops the scheduler gracefully.
    """
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("UptimeX Scheduler stopped.")
