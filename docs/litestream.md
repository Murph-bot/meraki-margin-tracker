# Continuous replication with Litestream → Cloudflare R2

[Litestream](https://litestream.io) streams the SQLite WAL to an S3-compatible bucket
(Cloudflare R2 here), so a lost Railway volume costs seconds of data rather than a day.
It is the only automatic backup mechanism. It complements the manual, on-request file
backups in [backups.md](backups.md); nothing else (backup, purge) is scheduled.

How it fits together:

- The Docker image contains the pinned `litestream` binary (v0.5.17, sha256-verified at
  build time) and `/app/litestream.yml`.
- `start.sh` is the container entrypoint. With replication configured it runs
  `litestream replicate -exec "uvicorn …"`, so Litestream supervises the app and exits with
  it. Without configuration it runs uvicorn directly, exactly as before.
- On boot, if the database file does not exist (fresh volume), `start.sh` first runs
  `litestream restore -if-db-not-exists -if-replica-exists`. If a replica exists the DB is
  rebuilt from it; if none exists yet the app starts with a new DB. **If the restore itself
  fails the container exits non-zero** instead of starting with an empty DB (which would
  then be replicated over your real backup).

## 1. Cloudflare setup (manual; nothing here is automated)

1. **Create a bucket**: Cloudflare dashboard → R2 → Create bucket, e.g. `meraki-db-backup`.
2. **Create an API token**: R2 → Manage R2 API Tokens → Create API token.
   Permission **Object Read & Write**, *Specify bucket(s)* → only `meraki-db-backup`.
   Copy the **Access Key ID** and **Secret Access Key** (shown once) and note your
   **Account ID** (the endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`).

## 2. Railway variables

Set these on the app service (placeholders shown; never commit real values):

| Variable | Example |
| --- | --- |
| `LITESTREAM_REPLICA_URL` | `s3://meraki-db-backup/meraki.db` |
| `LITESTREAM_ENDPOINT` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `LITESTREAM_ACCESS_KEY_ID` | `<R2 access key id>` |
| `LITESTREAM_SECRET_ACCESS_KEY` | `<R2 secret access key>` |

Replication is enabled **only when all four are non-empty**. If some but not all are set,
`start.sh` prints a warning to stderr naming the *missing variables* (never values) and
starts without replication. `LITESTREAM_DB_PATH` is derived by `start.sh` (same resolution
as `config.py`: `$RAILWAY_VOLUME_MOUNT_PATH/meraki.db`, else `$DATABASE_PATH`, else
`data/meraki.db`); do not set it yourself.

Retention is Litestream's default (snapshots kept 24h, which bounds point-in-time restore).
To change it see the comment in `litestream.yml`.

## 3. Verify replication

- **Logs**: after a deploy, Railway logs should show Litestream lines such as
  `replicating to` / `initialized db`, followed by uvicorn's startup. A warning
  `Litestream replication disabled, missing variables: …` means a variable is absent.
- **Inside the container** (`railway ssh`):
  ```bash
  export LITESTREAM_DB_PATH=$RAILWAY_VOLUME_MOUNT_PATH/meraki.db   # as start.sh does
  litestream databases -config /app/litestream.yml
  litestream ltx -config /app/litestream.yml $LITESTREAM_DB_PATH
  ```
  (the config expands the `LITESTREAM_*` variables already present in the container
  environment). New LTX files should appear within seconds of a write.
- **Restore test** (never touches the live DB; restores into a temp file, runs
  `PRAGMA integrity_check`, prints row counts and live vs soft-deleted counts):
  ```bash
  cd /app/backend && python -m app.scripts.restore_test --source litestream
  ```
  `--source auto` (default) uses Litestream when the four variables are set and the binary
  is available, otherwise the newest local backup. Exit code is non-zero on any failure.

## 4. Disabling

- Unset any of the four variables, or set `LITESTREAM_DISABLE=1`, and redeploy. The app
  then runs without Litestream. Existing data in the bucket is left alone.

## 5. Disaster recovery / point-in-time restore

Normal case: delete nothing, just redeploy onto an empty volume. `start.sh` restores
automatically as described above.

Manual restore to a file (inside the container or any machine with the binary and the
`LITESTREAM_*` variables exported):

```bash
export LITESTREAM_DB_PATH=/data/meraki.db      # the original path, used to find the replica
litestream restore -config /app/litestream.yml -o /tmp/restored.db "$LITESTREAM_DB_PATH"

# a point in time (UTC, RFC3339) — limited by snapshot retention (24h by default)
litestream restore -config /app/litestream.yml -timestamp 2026-10-05T09:30:00Z \
    -o /tmp/restored.db "$LITESTREAM_DB_PATH"

sqlite3 /tmp/restored.db "PRAGMA integrity_check;"
```

To put a restored file in place: stop the app, move the broken `meraki.db`, `-wal` and
`-shm` aside, copy the restored file to the DB path, start the app. (If you delete the DB
and leave replication configured, `start.sh` restores the *latest* state on boot.)
Accidentally deleted rows are usually easier to undo with a
[soft-delete restore](soft-deletes.md) than with PITR.

## Notes

- Only one writer should replicate to a given replica path. Do not run two services
  against the same bucket path (e.g. during a deploy overlap); `railway.toml` sets
  `overlapSeconds = 0` for this reason.
- Litestream replicates the live DB, so soft-deleted rows are replicated too; a
  [purge](soft-deletes.md#purging) removes them from the replica after the next snapshot
  retention cycle.
