# Database backups

The app stores everything in one SQLite file (`settings.database_path`:
`data/meraki.db`, or `$RAILWAY_VOLUME_MOUNT_PATH/meraki.db` when that variable is set).
Every connection runs in WAL mode (`synchronous=NORMAL`, `busy_timeout=5000`), so a plain
`cp meraki.db` can miss data in the `-wal` file or capture a torn state. Always back up
with the script below, which uses SQLite's online backup API.

Related docs: continuous off-host replication to Cloudflare R2 is in
[litestream.md](litestream.md); undoing deletes and purging old rows is in
[soft-deletes.md](soft-deletes.md). Prove a backup is usable with
`python -m app.scripts.restore_test --source local` (restores the newest backup into a temp
file, runs `PRAGMA integrity_check`, prints row counts).

## Taking a backup

From `backend/`:

```bash
python -m app.scripts.backup_db            # keep newest 14 (default)
python -m app.scripts.backup_db --keep 30
```

- Writes `meraki-YYYYmmddTHHMMSSZ.db` (UTC) into `<directory of the DB>/backups/`
  (so on Railway, into the volume). If a name already exists, `-1`, `-2`, … is appended.
- Opens the live database read-only with a 5 s busy timeout; it is safe while the app runs.
- Prunes to the newest N backups. Only files matching the script's own naming pattern are
  ever deleted; anything else in `backups/` is left alone.
- Backups live next to the database, so they protect against corruption and bad writes but
  **not** against loss of the disk/volume. Copy them off-host if that matters.

## Running it (manual only)

Backups are **manual by design**: there is no cron job, in-app timer or Railway cron for
this script, and none should be added without the owner's say-so. The only automatic
protection is Litestream's continuous replication ([litestream.md](litestream.md)).

Run it on request, inside the app container so it can reach the volume (a Railway volume
is attached to a single service):

```bash
railway ssh            # opens a shell in the running app container
cd /app/backend && python -m app.scripts.backup_db
```

Note that `railway run` executes on your own machine with the Railway variables, not inside
the container, so it cannot see the volume. Self-hosted: run the same command from
`backend/` with the app's environment (`SECRET_KEY`, `DATABASE_PATH`, ...) loaded.

## Restoring

1. Stop the app (so nothing writes while you swap files).
2. Optionally keep the current files for forensics:
   `mv meraki.db meraki.db.broken`.
3. Remove stale WAL side files: `rm -f meraki.db-wal meraki.db-shm`.
4. Copy the chosen backup into place: `cp backups/meraki-20260101T031500Z.db meraki.db`.
5. Verify: `sqlite3 meraki.db "PRAGMA integrity_check;"` should print `ok`.
6. Start the app. `init_db` re-applies the pragmas and any pending migrations.
