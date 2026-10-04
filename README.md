## Backups

The SQLite database runs in WAL mode; back it up with
`python -m app.scripts.backup_db` (from `backend/`). See [docs/backups.md](docs/backups.md)
for scheduling and restore instructions.
