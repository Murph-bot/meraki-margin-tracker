"""Online SQLite backup using the sqlite3 backup API.

Run from backend/:  python -m app.scripts.backup_db [--keep 14]
"""
import argparse
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

DEFAULT_KEEP = 14
BACKUP_RE = re.compile(r"^meraki-\d{8}T\d{6}Z(?:-\d+)?\.db$")


def default_backup_dir(db_path: str | Path) -> Path:
    return Path(db_path).resolve().parent / "backups"


def _backup_name(now: datetime, counter: int) -> str:
    suffix = f"-{counter}" if counter else ""
    return f"meraki-{now.strftime('%Y%m%dT%H%M%SZ')}{suffix}.db"


def backup_database(db_path, backup_dir=None, keep: int = DEFAULT_KEEP) -> Path:
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"database not found: {db_path}")
    backup_dir = Path(backup_dir) if backup_dir else default_backup_dir(db_path)
    backup_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    counter = 0
    while (backup_dir / _backup_name(now, counter)).exists():
        counter += 1
    dest = backup_dir / _backup_name(now, counter)
    tmp = dest.with_name(dest.name + ".tmp")

    # Read-only source: the backup never modifies the live DB.
    src = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        src.execute("PRAGMA busy_timeout = 5000")
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    finally:
        src.close()
    tmp.replace(dest)

    prune_backups(backup_dir, keep)
    return dest


def _sort_key(path: Path) -> tuple[str, int]:
    stamp, _, counter = path.stem.removeprefix("meraki-").partition("-")
    return stamp, int(counter or 0)


def prune_backups(backup_dir, keep: int = DEFAULT_KEEP) -> list[Path]:
    """Delete all but the newest `keep` backups matching our filename pattern."""
    if keep < 1:
        raise ValueError("keep must be >= 1")
    files = sorted(
        (p for p in Path(backup_dir).iterdir() if p.is_file() and BACKUP_RE.match(p.name)),
        key=_sort_key,
        reverse=True,
    )
    removed = files[keep:]
    for p in removed:
        p.unlink()
    return removed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Back up the SQLite database.")
    parser.add_argument("--keep", type=int, default=DEFAULT_KEEP, help="backups to retain")
    args = parser.parse_args(argv)
    dest = backup_database(settings.database_path, keep=args.keep)
    print(f"Backup written: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
