from datetime import date
from app.services.expense_schedule import expand_expenses


def test_one_shot_expense_in_range():
    rows = expand_expenses(
        [{"amount_cents": 1000, "date": "2026-09-10", "recurring": 0}],
        "2026-09-01",
        "2026-09-30",
    )
    assert len(rows) == 1
    assert rows[0]["amount_cents"] == 1000


def test_one_shot_expense_outside_range_dropped():
    rows = expand_expenses(
        [{"amount_cents": 1000, "date": "2026-08-10", "recurring": 0}],
        "2026-09-01",
        "2026-09-30",
    )
    assert rows == []


def test_monthly_recurring_counts_occurrence_in_period():
    rows = expand_expenses(
        [{"amount_cents": 2500, "date": "2026-08-02", "recurring": 1, "interval_days": 30}],
        "2026-09-01",
        "2026-09-19",
    )
    assert [row["date"] for row in rows] == ["2026-09-01"]
    assert rows[0]["amount_cents"] == 2500


def test_recurring_defaults_interval_to_30():
    rows = expand_expenses(
        [{"amount_cents": 100, "date": "2026-08-02", "recurring": True, "interval_days": 0}],
        "2026-09-01",
        "2026-09-19",
    )
    assert any(row["date"] == "2026-09-01" for row in rows)


def test_recurring_does_not_mutate_source():
    source = [{"amount_cents": 100, "date": "2026-08-02", "recurring": 1, "interval_days": 30}]
    expand_expenses(source, "2026-09-01", "2026-09-19")
    assert source[0]["date"] == "2026-08-02"
    assert date.fromisoformat(source[0]["date"]) == date(2026, 8, 2)


def test_invalid_expense_dates_are_skipped():
    rows = expand_expenses(
        [
            {"amount_cents": 1000, "date": "not-a-date", "recurring": 0},
            {"amount_cents": 2000, "date": "2026-09-10", "recurring": 0},
        ],
        "2026-09-01",
        "2026-09-30",
    )
    assert [row["amount_cents"] for row in rows] == [2000]
