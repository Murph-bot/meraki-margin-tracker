## Backups

The SQLite database runs in WAL mode; back it up with
`python -m app.scripts.backup_db` (from `backend/`). See [docs/backups.md](docs/backups.md)
for how to run it (manual, on request) and restore.

For continuous off-host replication to Cloudflare R2 (Litestream, started by `start.sh`
when configured), see [docs/litestream.md](docs/litestream.md). Verify any backup with
`python -m app.scripts.restore_test`.

## Soft deletes

Deleting a connection or an expense hides it; it can be undone via
`POST /api/connections/{id}/restore` / `POST /api/expenses/{id}/restore` until a purge is run.
The purge script (manual, never scheduled) removes rows deleted more than 30 days ago. See [docs/soft-deletes.md](docs/soft-deletes.md).
