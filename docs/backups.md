# Database backups

The app stores everything in one SQLite file (`settings.database_path`:
`data/meraki.db`, or `$RAILWAY_VOLUME_MOUNT_PATH/meraki.db` when that variable is set).
Every connection runs in WAL mode (`synchronous=NORMAL`, `busy_timeout=5000`), so a plain
`cp meraki.db` can miss data in the `-wal` file or capture a torn state. Always back up
with the script below, which uses SQLite's online backup API.

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

## Scheduling nightly

### Railway

A Railway volume can only be attached to **one service**. A separate cron service therefore
cannot see the app's volume (and so cannot read the DB or write backups to it). Practical
options:

1. **Run it inside the app service.** For example, an in-app scheduler (APScheduler or
   an asyncio task) that calls `backup_database(settings.database_path)` once a day. The
   app already has a periodic sync (`sync_interval_hours`), so this fits the existing
   pattern. This is not implemented yet.
2. **External trigger.** Expose a protected endpoint or use `railway ssh`/`railway run`
   from a scheduler you control (GitHub Actions cron, a VPS cron) that executes
   `python -m app.scripts.backup_db` in the app's container. Note that `railway run`
   executes locally with Railway variables, not inside the container, so it does not
   reach the volume; use `railway ssh` or an authenticated endpoint instead.
3. **Railway's own volume backups**, if your plan offers them, as an additional layer.

### Self-hosted (system cron)

```cron
# 03:15 every night
15 3 * * * cd /path/to/repo/backend && /path/to/.venv/bin/python -m app.scripts.backup_db >> /var/log/meraki-backup.log 2>&1
```

Make sure the environment (`SECRET_KEY`, `DATABASE_PATH`, …) is available to cron, e.g. via
the repo's `.env` in `backend/`.

## Restoring

1. Stop the app (so nothing writes while you swap files).
2. Optionally keep the current files for forensics:
   `mv meraki.db meraki.db.broken`.
3. Remove stale WAL side files: `rm -f meraki.db-wal meraki.db-shm`.
4. Copy the chosen backup into place: `cp backups/meraki-20260101T031500Z.db meraki.db`.
5. Verify: `sqlite3 meraki.db "PRAGMA integrity_check;"` should print `ok`.
6. Start the app. `init_db` re-applies the pragmas and any pending migrations.
