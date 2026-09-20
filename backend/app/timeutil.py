from datetime import datetime
from zoneinfo import ZoneInfo

ATHENS = ZoneInfo("Europe/Athens")


def athens_now() -> datetime:
    return datetime.now(ATHENS)


def period_start_iso(period: str, now: datetime | None = None) -> str:
    current = now or athens_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=ATHENS)
    else:
        current = current.astimezone(ATHENS)
    if period == "ytd":
        return f"{current.year}-01-01"
    return f"{current.year}-{current.month:02d}-01"
