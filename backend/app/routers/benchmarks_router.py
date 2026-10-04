from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import get_current_user
from app.database import get_db
from app.services.margin_calculator import calculate_margin
from app.services.expense_schedule import expand_expenses
from app.timeutil import athens_now

router = APIRouter(prefix="/api", tags=["reports"])


class MonthlyRow(BaseModel):
    month: str
    invoiced_cents: int
    fees_cents: int
    expenses_cents: int
    vat_cents: int
    income_tax_cents: int
    social_security_cents: int
    tax_prepayment_cents: int
    net_cents: int


BENCHMARKS = [
    {
        "profession": "Software developer",
        "city": "Athens",
        "min_rate": 35,
        "max_rate": 90,
        "median_rate": 55,
        "source": "MVP hardcoded reference — verify locally",
        "last_verified": "2026-09-19",
    },
    {
        "profession": "Product designer",
        "city": "Athens",
        "min_rate": 30,
        "max_rate": 70,
        "median_rate": 45,
        "source": "MVP hardcoded reference — verify locally",
        "last_verified": "2026-09-19",
    },
    {
        "profession": "Consultant",
        "city": "Thessaloniki",
        "min_rate": 25,
        "max_rate": 80,
        "median_rate": 40,
        "source": "MVP hardcoded reference — verify locally",
        "last_verified": "2026-09-19",
    },
]


@router.get("/benchmarks")
async def get_benchmarks(_user_id: int = Depends(get_current_user)):
    return BENCHMARKS


@router.get("/reports/monthly")
async def monthly_report(user_id: int = Depends(get_current_user), db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT efka_category, years_active, charges_vat FROM users WHERE id = ?",
        (user_id,),
    )
    user = await cursor.fetchone()
    efka_category = user["efka_category"] if user else 1
    years_active = user["years_active"] if user else 1
    charges_vat = bool(user["charges_vat"]) if user else False

    cursor = await db.execute(
        """
        SELECT substr(txn_timestamp, 1, 7) AS month,
               SUM(amount_cents) AS invoiced_cents,
               SUM(fee_cents) AS fees_cents,
               SUM(net_cents) AS net_after_fees_cents
        FROM transactions
        WHERE user_id = ? AND deleted_at IS NULL
        GROUP BY month
        ORDER BY month
        """,
        (user_id,),
    )
    txn_rows = {row["month"]: dict(row) for row in await cursor.fetchall()}

    cursor = await db.execute(
        "SELECT amount_cents, date, recurring, interval_days FROM expenses WHERE user_id = ? AND deleted_at IS NULL",
        (user_id,),
    )
    expense_rows: dict[str, int] = {}
    for exp in expand_expenses(
        [dict(row) for row in await cursor.fetchall()],
        "2000-01-01",
        athens_now().date().isoformat(),
    ):
        month_key = exp["date"][:7]
        expense_rows[month_key] = expense_rows.get(month_key, 0) + int(exp["amount_cents"])

    months = sorted(set(txn_rows) | set(expense_rows))
    result = []
    for month in months:
        invoiced = txn_rows.get(month, {}).get("invoiced_cents") or 0
        fees = txn_rows.get(month, {}).get("fees_cents") or 0
        net_after_fees = txn_rows.get(month, {}).get("net_after_fees_cents") or 0
        expenses = expense_rows.get(month) or 0
        txns = []
        if invoiced or fees or net_after_fees:
            txns = [{
                "amount_cents": invoiced,
                "fee_cents": fees,
                "net_cents": net_after_fees,
            }]
        expense_items = [{"amount_cents": expenses}] if expenses else []
        margin = calculate_margin(
            txns,
            expense_items,
            efka_category=efka_category,
            years_active=years_active,
            period_months=1,
            charges_vat=charges_vat,
        )
        result.append(
            MonthlyRow(
                month=month,
                invoiced_cents=margin.invoiced_cents,
                fees_cents=margin.fees_cents,
                expenses_cents=margin.expenses_cents,
                vat_cents=margin.vat_cents,
                income_tax_cents=margin.income_tax_cents,
                social_security_cents=margin.social_security_cents,
                tax_prepayment_cents=margin.tax_prepayment_cents,
                net_cents=margin.net_cents,
            )
        )
    return result
