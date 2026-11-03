from app.core.config import Settings
from app.sync.scheduler import shutdown_scheduler, start_scheduler


def test_daily_scheduler_registers_job() -> None:
    settings = Settings(
        sync_scheduler_enabled=True,
        sync_schedule_hour=3,
        sync_schedule_minute=30,
    )
    scheduler = start_scheduler(settings)
    try:
        assert scheduler is not None
        job = scheduler.get_job("daily-standard-sync")
        assert job is not None
        assert job.id == "daily-standard-sync"
    finally:
        shutdown_scheduler()


def test_scheduler_can_be_disabled() -> None:
    assert (
        start_scheduler(Settings(sync_scheduler_enabled=False)) is None
    )
