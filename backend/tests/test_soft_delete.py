import sqlite3
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest

from app.config import settings
from app.database import _column_names, init_db
from app.scripts.purge_deleted import main as purge_main, purge_deleted
from app.services.soft_delete import restore_connection, soft_delete_connection
from app.services.sync_service import sync_all_connections
from app.timeutil import athens_now

TABLES = ("connections", "transactions", "expenses")


def _noon() -> str:
    return athens_now().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()


async def _auth(client, email):
    response = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "secret123", "name": "U"},
    )
    body = response.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["user"]["id"]


async def _add_connection(db, user_id, label="Main"):
    cursor = await db.execute(
        "INSERT INTO connections (user_id, processor, label, api_key_encrypted) "
        "VALUES (?, 'stripe', ?, 'x')",
        (user_id, label),
    )
    await db.commit()
    return cursor.lastrowid


async def _add_txn(db, conn_id, user_id, txn_id, amount=100_000, deleted_at=None):
    cursor = await db.execute(
        """INSERT INTO transactions (connection_id, user_id, processor_txn_id, amount_cents,
               fee_cents, net_cents, txn_timestamp, deleted_at)
           VALUES (?, ?, ?, ?, 0, ?, ?, ?)""",
        (conn_id, user_id, txn_id, amount, amount, _noon(), deleted_at),
    )
    await db.commit()
    return cursor.lastrowid


async def _deleted_at(db, table, row_id):
    row = await (await db.execute(f"SELECT deleted_at FROM {table} WHERE id = ?", (row_id,))).fetchone()
    return row["deleted_at"]


# ---------------------------------------------------------------- migration

async def test_fresh_db_has_deleted_at_and_indexes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "fresh.db"))
    await init_db()
    async with aiosqlite.connect(settings.database_path) as db:
        for table in TABLES:
            assert "deleted_at" in await _column_names(db, table)
        names = {r[0] for r in await db.execute_fetchall("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"idx_expenses_user_live", "idx_connections_user_live"} <= names


async def test_migration_adds_deleted_at_to_old_schema_and_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, name TEXT NOT NULL DEFAULT '');
        CREATE TABLE connections (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            processor TEXT NOT NULL, label TEXT DEFAULT '', api_key_encrypted TEXT NOT NULL,
            last_synced_at TEXT, created_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, connection_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL, processor_txn_id TEXT, amount_cents INTEGER NOT NULL,
            fee_cents INTEGER DEFAULT 0, net_cents INTEGER NOT NULL, currency TEXT DEFAULT 'EUR',
            description TEXT DEFAULT '', customer_name TEXT DEFAULT '', invoice_number TEXT DEFAULT '',
            txn_timestamp TEXT NOT NULL, synced_at TEXT DEFAULT (datetime('now')),
            UNIQUE (connection_id, processor_txn_id));
        CREATE TABLE expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount_cents INTEGER NOT NULL, category TEXT DEFAULT 'other', description TEXT DEFAULT '',
            date TEXT NOT NULL, recurring INTEGER DEFAULT 0, interval_days INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')));
        INSERT INTO users (email, password_hash) VALUES ('a@b.c', 'h');
        INSERT INTO connections (user_id, processor, api_key_encrypted) VALUES (1, 'stripe', 'k');
        INSERT INTO transactions (connection_id, user_id, processor_txn_id, amount_cents, net_cents, txn_timestamp)
            VALUES (1, 1, 't1', 500, 500, '2026-01-01');
        INSERT INTO expenses (user_id, amount_cents, date) VALUES (1, 200, '2026-01-01');
        """
    )
    old.commit()
    old.close()

    monkeypatch.setattr(settings, "database_path", str(path))
    await init_db()
    await init_db()  # second run must be a no-op

    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        for table in TABLES:
            assert "deleted_at" in await _column_names(db, table)
            row = await (await db.execute(f"SELECT deleted_at FROM {table}")).fetchone()
            assert row["deleted_at"] is None  # existing rows stay live


async def test_column_names_rejects_unknown_table(db):
    with pytest.raises(ValueError):
        await _column_names(db, "sqlite_master; DROP TABLE users")


# ------------------------------------------------------------ expenses API

async def _create_expense(client, headers, amount=2500, date="2026-09-01"):
    r = await client.post(
        "/api/expenses",
        headers=headers,
        json={"amount_cents": amount, "category": "software", "date": date},
    )
    return r.json()["id"]


async def test_expense_soft_delete_keeps_row_and_hides_it(client, db):
    headers, _ = await _auth(client, "e1@example.com")
    exp_id = await _create_expense(client, headers)

    assert (await client.delete(f"/api/expenses/{exp_id}", headers=headers)).status_code == 200

    assert (await client.get("/api/expenses", headers=headers)).json() == []
    assert await _deleted_at(db, "expenses", exp_id) is not None
    # Second delete: nothing live to delete.
    assert (await client.delete(f"/api/expenses/{exp_id}", headers=headers)).status_code == 404


async def test_deleted_expense_excluded_from_dashboard_and_report(client, db):
    headers, _ = await _auth(client, "e2@example.com")
    today = athens_now().date().isoformat()
    exp_id = await _create_expense(client, headers, amount=4000, date=today)
    assert (await client.get("/api/dashboard", headers=headers)).json()["expenses_cents"] == 4000

    await client.delete(f"/api/expenses/{exp_id}", headers=headers)

    assert (await client.get("/api/dashboard", headers=headers)).json()["expenses_cents"] == 0
    assert (await client.get("/api/reports/monthly", headers=headers)).json() == []

    assert (await client.post(f"/api/expenses/{exp_id}/restore", headers=headers)).status_code == 200
    assert (await client.get("/api/dashboard", headers=headers)).json()["expenses_cents"] == 4000
    assert len((await client.get("/api/expenses", headers=headers)).json()) == 1


async def test_expense_restore_404s(client):
    headers, _ = await _auth(client, "e3@example.com")
    exp_id = await _create_expense(client, headers)
    # Not deleted -> 404; unknown -> 404.
    assert (await client.post(f"/api/expenses/{exp_id}/restore", headers=headers)).status_code == 404
    assert (await client.post("/api/expenses/9999/restore", headers=headers)).status_code == 404
    assert (await client.delete("/api/expenses/9999", headers=headers)).status_code == 404


async def test_expense_user_scoping(client):
    h1, _ = await _auth(client, "owner@example.com")
    h2, _ = await _auth(client, "other@example.com")
    exp_id = await _create_expense(client, h1)

    assert (await client.delete(f"/api/expenses/{exp_id}", headers=h2)).status_code == 404
    assert len((await client.get("/api/expenses", headers=h1)).json()) == 1

    await client.delete(f"/api/expenses/{exp_id}", headers=h1)
    assert (await client.post(f"/api/expenses/{exp_id}/restore", headers=h2)).status_code == 404
    assert (await client.get("/api/expenses", headers=h1)).json() == []
    assert (await client.post(f"/api/expenses/{exp_id}/restore", headers=h1)).status_code == 200


async def test_restore_requires_auth(client):
    assert (await client.post("/api/expenses/1/restore")).status_code in (401, 403)
    assert (await client.post("/api/connections/1/restore")).status_code in (401, 403)


# --------------------------------------------------------- connections API

async def test_connection_delete_cascades_with_same_timestamp_and_restores(client, db):
    headers, uid = await _auth(client, "c1@example.com")
    conn_id = await _add_connection(db, uid)
    t1 = await _add_txn(db, conn_id, uid, "a")
    t2 = await _add_txn(db, conn_id, uid, "b")
    assert (await client.get("/api/dashboard", headers=headers)).json()["invoiced_cents"] == 200_000

    assert (await client.delete(f"/api/connections/{conn_id}", headers=headers)).status_code == 200

    stamps = {await _deleted_at(db, "connections", conn_id),
              await _deleted_at(db, "transactions", t1),
              await _deleted_at(db, "transactions", t2)}
    assert len(stamps) == 1 and None not in stamps
    assert (await client.get("/api/connections", headers=headers)).json() == []
    assert (await client.get("/api/transactions", headers=headers)).json() == []
    dash = (await client.get("/api/dashboard", headers=headers)).json()
    assert dash["invoiced_cents"] == 0
    assert dash["missing_processors"] == ["stripe", "viva"]
    assert (await client.get("/api/reports/monthly", headers=headers)).json() == []
    assert (await client.delete(f"/api/connections/{conn_id}", headers=headers)).status_code == 404
    assert (await client.post(f"/api/connections/{conn_id}/sync", headers=headers)).status_code == 404

    assert (await client.post(f"/api/connections/{conn_id}/restore", headers=headers)).status_code == 200
    assert len((await client.get("/api/connections", headers=headers)).json()) == 1
    assert len((await client.get("/api/transactions", headers=headers)).json()) == 2
    assert (await client.get("/api/dashboard", headers=headers)).json()["invoiced_cents"] == 200_000
    assert (await client.post(f"/api/connections/{conn_id}/restore", headers=headers)).status_code == 404


async def test_connection_restore_only_restores_cascade_deleted_transactions(db):
    cursor = await db.execute("INSERT INTO users (email, password_hash) VALUES ('x@y.z', 'h')")
    uid = cursor.lastrowid
    conn_id = await _add_connection(db, uid)
    # No per-transaction delete endpoint exists, so set up an earlier independent delete directly.
    earlier = await _add_txn(db, conn_id, uid, "old", deleted_at="2020-01-01 00:00:00")
    live = await _add_txn(db, conn_id, uid, "live")

    assert await soft_delete_connection(db, conn_id, uid)
    assert await _deleted_at(db, "transactions", earlier) == "2020-01-01 00:00:00"  # untouched
    assert await _deleted_at(db, "transactions", live) is not None

    assert await restore_connection(db, conn_id, uid)
    assert await _deleted_at(db, "transactions", live) is None
    assert await _deleted_at(db, "transactions", earlier) == "2020-01-01 00:00:00"


async def test_connection_user_scoping_and_404s(client, db):
    h1, u1 = await _auth(client, "o1@example.com")
    h2, _ = await _auth(client, "o2@example.com")
    conn_id = await _add_connection(db, u1)

    assert (await client.delete(f"/api/connections/{conn_id}", headers=h2)).status_code == 404
    assert await _deleted_at(db, "connections", conn_id) is None
    await client.delete(f"/api/connections/{conn_id}", headers=h1)
    assert (await client.post(f"/api/connections/{conn_id}/restore", headers=h2)).status_code == 404
    assert await _deleted_at(db, "connections", conn_id) is not None
    assert (await client.post("/api/connections/9999/restore", headers=h1)).status_code == 404


async def test_resync_does_not_conflict_after_delete(db):
    """Unique (connection_id, processor_txn_id) never trips: deleted connections are not
    synced, and a re-created connection gets a fresh AUTOINCREMENT id."""
    cursor = await db.execute("INSERT INTO users (email, password_hash) VALUES ('s@y.z', 'h')")
    uid = cursor.lastrowid
    first = await _add_connection(db, uid)
    await _add_txn(db, first, uid, "ch_1")
    await soft_delete_connection(db, first, uid)
    second = await _add_connection(db, uid)
    await _add_txn(db, second, uid, "ch_1")  # same processor id, new connection: allowed
    assert second != first


# ---------------------------------------------------------------- sync

async def test_sync_all_skips_soft_deleted_connections(db, monkeypatch):
    cursor = await db.execute("INSERT INTO users (email, password_hash) VALUES ('sy@y.z', 'h')")
    uid = cursor.lastrowid
    live = await _add_connection(db, uid, "live")
    dead = await _add_connection(db, uid, "dead")
    await soft_delete_connection(db, dead, uid)

    async def fake_get_db():
        yield db

    synced = []

    async def fake_sync(_db, conn_id, user_id, api_key):
        synced.append(conn_id)
        return 0

    monkeypatch.setattr("app.database.get_db", fake_get_db)
    monkeypatch.setattr("app.services.stripe_adapter.sync_connection", fake_sync)
    monkeypatch.setattr("app.crypto.decrypt_secret", lambda v: "sk")
    # aclose() on the fake generator would close the shared fixture connection; guard it.
    with patch.object(db, "close", AsyncMock()):
        await sync_all_connections()

    assert synced == [live]


async def test_sync_insert_skipped_when_connection_deleted(db, monkeypatch):
    from app.services import stripe_adapter

    cursor = await db.execute("INSERT INTO users (email, password_hash) VALUES ('si@y.z', 'h')")
    uid = cursor.lastrowid
    conn_id = await _add_connection(db, uid)
    await soft_delete_connection(db, conn_id, uid)
    fetched = [stripe_adapter.SyncedTransaction(
        processor_txn_id="late", amount_cents=100, fee_cents=0, net_cents=100, currency="EUR",
        description="", customer_name="", invoice_number="", txn_timestamp=_noon(),
    )]
    monkeypatch.setattr(stripe_adapter, "fetch_stripe_transactions", lambda key, gte: fetched)
    inserted = await stripe_adapter.sync_connection(db, conn_id, uid, "sk")
    assert inserted == 0
    count = await (await db.execute("SELECT COUNT(*) FROM transactions")).fetchone()
    assert count[0] == 0


# ---------------------------------------------------------------- purge

def _purge_db(tmp_path):
    path = tmp_path / "purge.db"
    conn = sqlite3.connect(path)
    from app.database.schema import SCHEMA, SOFT_DELETE_INDEXES
    for stmt in SCHEMA + SOFT_DELETE_INDEXES:
        conn.execute(stmt)
    conn.execute("INSERT INTO users (email, password_hash) VALUES ('p@y.z', 'h')")
    conn.commit()
    return path, conn


def _insert(conn, sql, *params):
    return conn.execute(sql, params).lastrowid


def test_purge_respects_cutoff_and_fk_order(tmp_path):
    path, conn = _purge_db(tmp_path)
    old, recent = "2000-01-01 00:00:00", "2999-01-01 00:00:00"
    conn_old = _insert(conn, "INSERT INTO connections (user_id, processor, api_key_encrypted, deleted_at) VALUES (1,'stripe','k',?)", old)
    conn_recent = _insert(conn, "INSERT INTO connections (user_id, processor, api_key_encrypted, deleted_at) VALUES (1,'stripe','k',?)", recent)
    conn_live = _insert(conn, "INSERT INTO connections (user_id, processor, api_key_encrypted) VALUES (1,'stripe','k')")
    t = "INSERT INTO transactions (connection_id, user_id, processor_txn_id, amount_cents, net_cents, txn_timestamp, deleted_at) VALUES (?,1,?,1,1,'2026-01-01',?)"
    _insert(conn, t, conn_old, "a", old)             # purged with its connection
    _insert(conn, t, conn_old, "b", None)            # live row under purged connection: must go (FK)
    _insert(conn, t, conn_recent, "c", recent)       # kept
    _insert(conn, t, conn_live, "d", old)            # old independent delete: purged
    _insert(conn, t, conn_live, "e", None)           # kept
    e = "INSERT INTO expenses (user_id, amount_cents, date, deleted_at) VALUES (1,1,'2026-01-01',?)"
    _insert(conn, e, old)
    _insert(conn, e, recent)
    _insert(conn, e, None)
    conn.commit()
    conn.close()

    counts = purge_deleted(path, days=30)

    assert counts == {"transactions": 3, "connections": 1, "expenses": 1}
    check = sqlite3.connect(path)
    assert check.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
    assert check.execute("SELECT id FROM connections ORDER BY id").fetchall() == [(conn_recent,), (conn_live,)]
    assert check.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 2
    assert check.execute("PRAGMA foreign_key_check").fetchall() == []


def test_purge_dry_run_deletes_nothing_and_cli_prints_counts(tmp_path, monkeypatch, capsys):
    path, conn = _purge_db(tmp_path)
    _insert(conn, "INSERT INTO expenses (user_id, amount_cents, date, deleted_at) VALUES (1,1,'2026-01-01','2000-01-01 00:00:00')")
    conn.commit()
    conn.close()

    assert purge_deleted(path, days=30, dry_run=True)["expenses"] == 1
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 1

    monkeypatch.setattr(settings, "database_path", str(path))
    assert purge_main(["--dry-run"]) == 0
    assert "Would purge" in capsys.readouterr().out
    assert purge_main(["--days", "30"]) == 0
    assert "Purged" in capsys.readouterr().out
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM expenses").fetchone()[0] == 0


def test_purge_cutoff_boundary(tmp_path):
    path, conn = _purge_db(tmp_path)
    e = "INSERT INTO expenses (user_id, amount_cents, date, deleted_at) VALUES (1,1,'2026-01-01',datetime('now', ?))"
    _insert(conn, e, "-31 days")
    _insert(conn, e, "-29 days")
    conn.commit()
    conn.close()
    assert purge_deleted(path, days=30)["expenses"] == 1
