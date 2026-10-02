from datetime import datetime
from app.timeutil import ATHENS, period_start_iso


def test_month_period_uses_athens_calendar_not_utc():
    now = datetime(2026, 10, 1, 0, 30, tzinfo=ATHENS)
    assert period_start_iso("month", now) == "2026-10-01"


def test_ytd_period_starts_january_first():
    now = datetime(2026, 9, 19, 21, 0, tzinfo=ATHENS)
    assert period_start_iso("ytd", now) == "2026-01-01"
