import asyncio
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from app.timeutil import ATHENS

# Dashboard YTD figures (and annualized tax) need every transaction since
# Jan 1 Athens time. Re-fetching is idempotent (INSERT OR IGNORE on txn id).
SYNC_LOOKBACK_SLACK_DAYS = 1
INCLUDED_BALANCE_TYPES = {"charge", "payment", "refund", "payment_refund"}


@dataclass
class SyncedTransaction:
    processor_txn_id: str
    amount_cents: int
    fee_cents: int
    net_cents: int
    currency: str
    description: str
    customer_name: str
    invoice_number: str
    txn_timestamp: str


def validate_stripe_key(api_key: str) -> None:
    import stripe

    stripe.Balance.retrieve(api_key=api_key)


def fetch_stripe_transactions(api_key: str, created_gte: int | None = None) -> list[SyncedTransaction]:
    import stripe

    # Pass the key per request: a module-global stripe.api_key is shared across
    # concurrent requests and threads, so one user's sync could use another's key.
    params: dict = {"limit": 100, "api_key": api_key}
    if created_gte:
        params["created"] = {"gte": created_gte}

    results: list[SyncedTransaction] = []
    for item in stripe.BalanceTransaction.list(**params).auto_paging_iter():
        item_type = getattr(item, "type", "charge") or "charge"
        if item_type not in INCLUDED_BALANCE_TYPES:
            continue
        created = datetime.fromtimestamp(item.created, tz=timezone.utc).astimezone(ATHENS).isoformat()
        source = getattr(item, "source", "") or ""
        results.append(
            SyncedTransaction(
                processor_txn_id=str(item.id),
                amount_cents=int(item.amount),
                fee_cents=int(item.fee or 0),
                net_cents=int(item.net),
                currency=(item.currency or "eur").upper(),
                description=item.description or "",
                customer_name="",
                invoice_number=str(source),
                txn_timestamp=created,
            )
        )
    return results


def _lookback_gte(now: datetime | None = None) -> int:
    current = (now or datetime.now(timezone.utc)).astimezone(ATHENS)
    jan1 = current.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return int((jan1 - timedelta(days=SYNC_LOOKBACK_SLACK_DAYS)).timestamp())


async def sync_connection(db, connection_id: int, user_id: int, api_key: str) -> int:
    # The Stripe SDK is synchronous; run it off the event loop.
    fetched = await asyncio.to_thread(fetch_stripe_transactions, api_key, _lookback_gte())
    inserted = 0
    for txn in fetched:
        cursor = await db.execute(
            """
            INSERT OR IGNORE INTO transactions (
                connection_id, user_id, processor_txn_id, amount_cents, fee_cents,
                net_cents, currency, description, customer_name, invoice_number, txn_timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                connection_id,
                user_id,
                txn.processor_txn_id,
                txn.amount_cents,
                txn.fee_cents,
                txn.net_cents,
                txn.currency,
                txn.description,
                txn.customer_name,
                txn.invoice_number,
                txn.txn_timestamp,
            ),
        )
        if cursor.rowcount:
            inserted += 1
    await db.execute(
        "UPDATE connections SET last_synced_at = datetime('now') WHERE id = ?",
        (connection_id,),
    )
    await db.execute(
        "INSERT INTO sync_log (connection_id, status, message) VALUES (?, ?, ?)",
        (connection_id, "ok", f"synced {inserted} new transactions"),
    )
    await db.commit()
    return inserted
