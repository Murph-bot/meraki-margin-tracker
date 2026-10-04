# Soft deletes

User data that used to be removed immediately is now hidden instead, so a mistaken delete
can be undone. Hidden rows are kept until the purge script is run by hand (it removes rows
deleted more than 30 days ago); nothing purges them automatically.

## Semantics

- Tables with a `deleted_at TEXT` column: **connections**, **transactions**, **expenses**.
  `NULL` = live; otherwise a UTC `YYYY-MM-DD HH:MM:SS` stamp (SQLite `datetime('now')`).
- Not covered: `users` (no delete path), `sync_log` (log), and `margin_snapshots`
  (derived data: `record_daily_snapshots` still hard-`DELETE`s today's row and recomputes
  it from live data, which is correct and needs no restore).
- `DELETE /api/expenses/{id}` and `DELETE /api/connections/{id}` now run
  `UPDATE … SET deleted_at = … WHERE … AND deleted_at IS NULL`; **404** when nothing live
  matched (unknown id, someone else's row, or already deleted).
- Deleting a connection soft-deletes its live transactions in the same DB transaction with
  the **same** `deleted_at` value (computed once).
- Every read filters `deleted_at IS NULL`: expense/connection/transaction lists,
  dashboard (transactions, expenses, `missing_processors`), monthly report, the daily
  snapshot job, `POST /connections/{id}/sync`, and the scheduled sync (soft-deleted
  connections are never synced). Sync's insert is additionally guarded so a sync that was
  already running when its connection was deleted cannot add live rows to it.
- Migration (`_apply_migrations`, run by `init_db`) adds the column to existing databases
  with `ALTER TABLE` after a `PRAGMA table_info` check, so it is idempotent; existing rows
  stay live. Fresh databases get the column from `schema.py`. Partial indexes on live
  `expenses`/`connections` rows are created by the migration step.

## Restoring

| Endpoint | Effect |
| --- | --- |
| `POST /api/expenses/{id}/restore` | clears `deleted_at` |
| `POST /api/connections/{id}/restore` | clears `deleted_at` on the connection **and** only on those transactions whose `deleted_at` equals the connection's (the ones deleted with it) |

Both require auth, are scoped to the caller's own rows, and return **404** when the row does
not exist, belongs to someone else, or is not deleted. There is no endpoint to list deleted
rows yet (restore needs the id), and no per-transaction delete or restore.
A transaction deleted at a different moment than its connection (none can be today) stays
deleted on connection restore. Timestamps have 1 s resolution; two deletes in the same
second are indistinguishable.

The window is "until purged": once `purge_deleted` removes a row it cannot be restored
(other than via a [Litestream/file backup](litestream.md)).

## Sync and the UNIQUE(connection_id, processor_txn_id) constraint

This constraint cannot make a sync fail because of soft deletes: transactions are only ever
inserted for a **live** connection; soft-deleted connections are skipped, and a new connection
gets a new `AUTOINCREMENT` id, so re-adding the same Stripe account re-syncs into fresh rows.
The sync uses `INSERT OR IGNORE`, so even a (hypothetical) soft-deleted transaction under a
live connection would keep its row and stay deleted rather than error or be duplicated.

## Re-encrypting keys

`python -m app.scripts.reencrypt_connections` deliberately re-encrypts **all** connections,
including soft-deleted ones. They may still be restored, and must remain decryptable after
`SECRET_KEY` is rotated.

## Purging

```bash
cd backend
python -m app.scripts.purge_deleted --dry-run        # show counts, change nothing
python -m app.scripts.purge_deleted                   # default: older than 30 days
python -m app.scripts.purge_deleted --days 60
```

Hard-deletes rows with `deleted_at` older than N days, in **one transaction** with
`foreign_keys = ON`, in FK-safe order: transactions (including any transaction belonging to a
connection being purged), then connections, then expenses. Prints the counts per table.

### Manual only

The purge is **never run automatically**: no cron, no in-app timer, no Railway cron.
Soft-deleted rows stay restorable until someone runs the purge on request. When you do,
take a backup first, inside the app container:

```bash
railway ssh
cd /app/backend && python -m app.scripts.backup_db && python -m app.scripts.purge_deleted --dry-run
python -m app.scripts.purge_deleted      # after checking the dry-run counts
```

## Foreign-key notes

- `transactions.connection_id → connections(id)` has no `ON DELETE CASCADE`; the purge order
  above is what keeps it valid. Never hard-delete a connection without its transactions.
- Soft-deleted rows still satisfy their foreign keys, so nothing else needs changing.
