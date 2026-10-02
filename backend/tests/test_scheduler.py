from datetime import datetime, timedelta, timezone

from app.services.sync_service import build_scheduler


def test_first_sync_runs_soon_after_boot():
    scheduler = build_scheduler()
    job = scheduler.get_job("daily_sync")
    assert job is not None
    first = getattr(job, "next_run_time", None)
    assert first is not None, "interval job without next_run_time waits a full interval after every deploy"
    assert first <= datetime.now(timezone.utc) + timedelta(minutes=10)
