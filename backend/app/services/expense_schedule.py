from datetime import date, timedelta


def _parse_day(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def expand_expenses(expenses: list[dict], range_start: str, range_end: str) -> list[dict]:
    start = _parse_day(range_start)
    end = _parse_day(range_end)
    if start is None or end is None:
        return []
    result: list[dict] = []
    for exp in expenses:
        origin = _parse_day(str(exp.get("date", "")))
        if origin is None:
            continue
        if not bool(exp.get("recurring")):
            if start <= origin <= end:
                result.append(dict(exp))
            continue
        interval = int(exp.get("interval_days") or 0) or 30
        if interval < 1:
            interval = 30
        current = origin
        if current < start:
            steps = (start - current).days // interval
            current = current + timedelta(days=steps * interval)
            if current < start:
                current = current + timedelta(days=interval)
        while current <= end:
            item = dict(exp)
            item["date"] = current.isoformat()
            result.append(item)
            current = current + timedelta(days=interval)
    return result
