import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if os.environ.get("TESTING") == "1":
        return
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        sync_all_connections,
        "interval",
        hours=settings.sync_interval_hours,
        id="daily_sync",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None


async def record_daily_snapshots(db) -> None:
    from app.services.margin_calculator import calculate_margin
    from app.services.expense_schedule import expand_expenses
    from app.timeutil import athens_now, period_start_iso

    today = athens_now().date().isoformat()
    start = period_start_iso("month")
    cursor = await db.execute("SELECT id, efka_category, years_active, charges_vat FROM users")
    users = await cursor.fetchall()
    for user in users:
        user_id = user["id"]
        tx_cursor = await db.execute(
            """
            SELECT amount_cents, fee_cents, net_cents
            FROM transactions
            WHERE user_id = ? AND txn_timestamp >= ?
            """,
            (user_id, start),
        )
        transactions = [dict(row) for row in await tx_cursor.fetchall()]
        exp_cursor = await db.execute(
            "SELECT amount_cents, date, recurring, interval_days FROM expenses WHERE user_id = ?",
            (user_id,),
        )
        expenses = expand_expenses(
            [dict(row) for row in await exp_cursor.fetchall()],
            start[:10],
            today,
        )
        margin = calculate_margin(
            transactions,
            expenses,
            efka_category=user["efka_category"],
            years_active=user["years_active"],
            period_months=1,
            charges_vat=bool(user["charges_vat"]),
        )
        await db.execute(
            "DELETE FROM margin_snapshots WHERE user_id = ? AND date = ?",
            (user_id, today),
        )
        await db.execute(
            """
            INSERT INTO margin_snapshots (
                user_id, date, gross_cents, fees_cents, expenses_cents,
                estimated_tax_cents, social_security_cents, net_cents, effective_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                today,
                margin.invoiced_cents,
                margin.fees_cents,
                margin.expenses_cents,
                margin.income_tax_cents,
                margin.social_security_cents,
                margin.net_cents,
                margin.keep_percent,
            ),
        )
    await db.commit()


async def sync_all_connections() -> None:
    from app.database import get_db
    from app.services.stripe_adapter import sync_connection
    from app.crypto import decrypt_secret

    agen = get_db()
    db = await agen.__anext__()
    try:
        cursor = await db.execute(
            "SELECT id, user_id, processor, api_key_encrypted FROM connections"
        )
        rows = await cursor.fetchall()
        for row in rows:
            if row["processor"] != "stripe":
                continue
            try:
                api_key = decrypt_secret(row["api_key_encrypted"])
                await sync_connection(db, row["id"], row["user_id"], api_key)
            except Exception as exc:
                await db.execute(
                    "INSERT INTO sync_log (connection_id, status, message) VALUES (?, ?, ?)",
                    (row["id"], "error", str(exc)[:500]),
                )
        await db.commit()
        await record_daily_snapshots(db)
    finally:
        await agen.aclose()
