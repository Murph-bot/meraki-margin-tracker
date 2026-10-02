from types import SimpleNamespace
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.timeutil import ATHENS
from app.services.stripe_adapter import fetch_stripe_transactions, sync_connection


def _txn(txn_id: str, amount: int, fee: int, net: int, created: int = 1_700_000_000, txn_type: str = "charge"):
    return SimpleNamespace(
        id=txn_id,
        amount=amount,
        fee=fee,
        net=net,
        currency="eur",
        description="Invoice",
        source="ch_123",
        created=created,
        type=txn_type,
    )


def test_fetch_stripe_transactions_maps_fields():
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = [
        _txn("txn_1", 10000, 290, 9710),
    ]
    with patch("stripe.BalanceTransaction.list", return_value=fake_list):
        rows = fetch_stripe_transactions("sk_test_123")
    assert len(rows) == 1
    assert rows[0].processor_txn_id == "txn_1"
    assert rows[0].amount_cents == 10000
    assert rows[0].fee_cents == 290
    assert rows[0].net_cents == 9710
    assert rows[0].currency == "EUR"


def test_fetch_stripe_transactions_passes_created_gte():
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = []
    with patch("stripe.BalanceTransaction.list", return_value=fake_list) as listed:
        fetch_stripe_transactions("sk_test_123", created_gte=1_700_000_000)
    listed.assert_called_once()
    assert listed.call_args.kwargs["created"] == {"gte": 1_700_000_000}
    assert "type" not in listed.call_args.kwargs


def test_fetch_includes_payments_and_refunds_skips_payouts():
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = [
        _txn("pay_1", 8000, 200, 7800, txn_type="payment"),
        _txn("ref_1", -2000, 0, -2000, txn_type="refund"),
        _txn("po_1", -5000, 0, -5000, txn_type="payout"),
    ]
    with patch("stripe.BalanceTransaction.list", return_value=fake_list):
        rows = fetch_stripe_transactions("sk_test_123")
    assert [row.processor_txn_id for row in rows] == ["pay_1", "ref_1"]


async def test_sync_connection_inserts_and_is_idempotent(db):
    await db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        ("s@example.com", "hash", "S"),
    )
    await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (?, ?, ?, ?)",
        (1, "stripe", "main", "encrypted"),
    )
    await db.commit()

    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = [_txn("txn_1", 5000, 100, 4900)]
    with patch("stripe.BalanceTransaction.list", return_value=fake_list):
        first = await sync_connection(db, 1, 1, "sk_test_123")
        second = await sync_connection(db, 1, 1, "sk_test_123")
    assert first == 1
    assert second == 0
    cursor = await db.execute("SELECT COUNT(*) AS n FROM transactions")
    row = await cursor.fetchone()
    assert row["n"] == 1


async def test_sync_connection_requests_since_jan1_athens(db):
    await db.execute(
        "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
        ("t@example.com", "hash", "T"),
    )
    await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) VALUES (?, ?, ?, ?)",
        (1, "stripe", "main", "encrypted"),
    )
    await db.commit()
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = []
    with patch("stripe.BalanceTransaction.list", return_value=fake_list) as listed:
        await sync_connection(db, 1, 1, "sk_test_123")
    gte = listed.call_args.kwargs["created"]["gte"]
    # YTD figures need every transaction since Jan 1 (Athens), not just 90 days.
    jan1 = datetime.now(ATHENS).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    assert gte <= int(jan1.timestamp())
    assert gte >= int(jan1.timestamp()) - 86400


def test_fetch_does_not_truncate_at_500():
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = [
        _txn(f"txn_{i}", 1000, 30, 970) for i in range(750)
    ]
    with patch("stripe.BalanceTransaction.list", return_value=fake_list):
        rows = fetch_stripe_transactions("sk_test_123")
    assert len(rows) == 750



def test_fetch_passes_api_key_per_request_not_globally():
    import stripe

    stripe.api_key = None
    fake_list = MagicMock()
    fake_list.auto_paging_iter.return_value = []
    with patch("stripe.BalanceTransaction.list", return_value=fake_list) as listed:
        fetch_stripe_transactions("sk_test_abc")
    assert listed.call_args.kwargs["api_key"] == "sk_test_abc"
    assert stripe.api_key is None
