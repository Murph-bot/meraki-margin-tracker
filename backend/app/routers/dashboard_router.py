from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.auth import get_current_user
from app.database import get_db
from app.services.margin_calculator import TAX_DISCLAIMER, calculate_margin
from app.services.expense_schedule import expand_expenses
from app.timeutil import athens_now, period_start_iso

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class TrendPoint(BaseModel):
    date: str
    net_cents: int


class DashboardResponse(BaseModel):
    period: str
    invoiced_cents: int
    fees_cents: int
    expenses_cents: int
    income_tax_cents: int
    tax_prepayment_cents: int
    social_security_cents: int
    vat_cents: int
    net_cents: int
    keep_percent: float
    effective_hourly_cents: int | None
    trend: list[TrendPoint]
    missing_processors: list[str]
    disclaimer: str


def _period_start(period: str) -> str:
    return period_start_iso(period)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    period: Literal["month", "ytd"] = Query(default="month"),
    hours: float = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user),
    db=Depends(get_db),
):
    start = _period_start(period)
    cursor = await db.execute(
        """
        SELECT amount_cents, fee_cents, net_cents, txn_timestamp
        FROM transactions
        WHERE user_id = ? AND txn_timestamp >= ? AND deleted_at IS NULL
        """,
        (user_id, start),
    )
    transactions = [dict(row) for row in await cursor.fetchall()]

    cursor = await db.execute(
        "SELECT amount_cents, date, recurring, interval_days FROM expenses WHERE user_id = ? AND deleted_at IS NULL",
        (user_id,),
    )
    expenses = expand_expenses(
        [dict(row) for row in await cursor.fetchall()],
        start[:10],
        athens_now().date().isoformat(),
    )

    cursor = await db.execute(
        "SELECT efka_category, years_active, charges_vat FROM users WHERE id = ?", (user_id,)
    )
    user = await cursor.fetchone()
    efka_category = user["efka_category"] if user else 1
    years_active = user["years_active"] if user else 1
    charges_vat = bool(user["charges_vat"]) if user else False

    now = athens_now()
    period_months = 1 if period == "month" else max(1, now.month)
    margin = calculate_margin(
        transactions,
        expenses,
        hours_worked=hours,
        efka_category=efka_category,
        years_active=years_active,
        period_months=period_months,
        charges_vat=charges_vat,
    )

    cursor = await db.execute(
        "SELECT processor FROM connections WHERE user_id = ? AND deleted_at IS NULL", (user_id,)
    )
    connected = {row["processor"] for row in await cursor.fetchall()}
    missing = [name for name in ("stripe", "viva") if name not in connected]

    trend_map: dict[str, int] = {}
    for txn in transactions:
        day = str(txn["txn_timestamp"])[:10]
        trend_map[day] = trend_map.get(day, 0) + int(txn["net_cents"])
    trend = [TrendPoint(date=day, net_cents=cents) for day, cents in sorted(trend_map.items())][-30:]

    return DashboardResponse(
        period=period,
        invoiced_cents=margin.invoiced_cents,
        fees_cents=margin.fees_cents,
        expenses_cents=margin.expenses_cents,
        income_tax_cents=margin.income_tax_cents,
        tax_prepayment_cents=margin.tax_prepayment_cents,
        social_security_cents=margin.social_security_cents,
        vat_cents=margin.vat_cents,
        net_cents=margin.net_cents,
        keep_percent=margin.keep_percent,
        effective_hourly_cents=margin.effective_hourly_cents,
        trend=trend,
        missing_processors=missing,
        disclaimer=TAX_DISCLAIMER,
    )
