import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.sync.service import (
    SyncAlreadyRunning,
    SyncInitializationRequired,
    SyncMode,
    has_completed_sync,
    source_name_for,
    start_sync,
)

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def run_scheduled_sync(settings: Settings | None = None) -> None:
    """Daily job: incremental after the admin-triggered initial load."""
    settings = settings or get_settings()
    db = SessionLocal()
    try:
        source = source_name_for(settings)
        if not has_completed_sync(db, source):
            logger.warning(
                "scheduled sync skipped: no successful initial load; "
                "call POST /api/admin/sync/standards once"
            )
            return
        result = start_sync(db, mode=SyncMode.INCREMENTAL, settings=settings)
        logger.info(
            "scheduled sync started: task=%s source=%s mode=%s",
            result.task_id,
            result.source,
            result.mode.value,
        )
    except SyncAlreadyRunning:
        logger.info("scheduled sync skipped: another sync is already running")
    except SyncInitializationRequired as exc:
        logger.warning("scheduled sync skipped: %s", exc)
    except Exception:  # noqa: BLE001 - scheduler must keep running
        logger.exception("scheduled sync failed to start")
    finally:
        db.close()


def start_scheduler(settings: Settings | None = None) -> BackgroundScheduler | None:
    global _scheduler
    settings = settings or get_settings()
    if not settings.sync_scheduler_enabled:
        logger.info("standard sync scheduler is disabled")
        return None
    if _scheduler is not None and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_scheduled_sync,
        CronTrigger(
            hour=settings.sync_schedule_hour,
            minute=settings.sync_schedule_minute,
        ),
        id="daily-standard-sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info(
        "standard sync scheduler started: daily at %02d:%02d (server local time)",
        settings.sync_schedule_hour,
        settings.sync_schedule_minute,
    )
    return scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("standard sync scheduler stopped")
