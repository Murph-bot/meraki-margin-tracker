"""Restore the newest backup into a temp file and sanity-check it. Never touches the live DB.

Run from backend/:  python -m app.scripts.restore_test [--source auto|local|litestream]

  litestream  restore the replica (R2) with `litestream restore -o <tmp>`
  local       copy the newest file in the backups dir (backup_db) via the sqlite backup API
  auto        litestream when all four LITESTREAM_* variables are set and the binary is
              available, otherwise local
"""
import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import settings
from app.scripts.backup_db import BACKUP_RE, _sort_key, default_backup_dir

REPLICATION_VARS = (
    "LITESTREAM_REPLICA_URL",
    "LITESTREAM_ACCESS_KEY_ID",
    "LITESTREAM_SECRET_ACCESS_KEY",
    "LITESTREAM_ENDPOINT",
)
SECRET_VARS = ("LITESTREAM_ACCESS_KEY_ID", "LITESTREAM_SECRET_ACCESS_KEY")
SOFT_DELETE_TABLES = ("connections", "transactions", "expenses")
RESTORE_TIMEOUT_SECONDS = 300


class RestoreTestError(Exception):
    pass


def _litestream_bin() -> str | None:
    return shutil.which(os.environ.get("LITESTREAM_BIN") or "litestream")


def _litestream_config() -> str:
    explicit = os.environ.get("LITESTREAM_CONFIG")
    if explicit:
        return explicit
    for candidate in (Path("/app/litestream.yml"), Path(__file__).resolve().parents[3] / "litestream.yml"):
        if candidate.is_file():
            return str(candidate)
    raise RestoreTestError("litestream.yml not found (set LITESTREAM_CONFIG)")


def _db_path() -> str:
    return os.environ.get("LITESTREAM_DB_PATH") or str(Path(settings.database_path).resolve())


def _scrub(text: str) -> str:
    for name in SECRET_VARS:
        value = os.environ.get(name)
        if value:
            text = text.replace(value, "***")
    return text


def litestream_configured() -> bool:
    return all(os.environ.get(name) for name in REPLICATION_VARS) and _litestream_bin() is not None


def restore_from_litestream(dest: Path) -> str:
    binary = _litestream_bin()
    if binary is None:
        raise RestoreTestError("litestream binary not found on PATH (or LITESTREAM_BIN)")
    env = {**os.environ, "LITESTREAM_DB_PATH": _db_path()}
    result = subprocess.run(
        [binary, "restore", "-config", _litestream_config(), "-o", str(dest), env["LITESTREAM_DB_PATH"]],
        env=env, capture_output=True, text=True, timeout=RESTORE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        detail = _scrub((result.stderr or result.stdout).strip())
        raise RestoreTestError(f"litestream restore failed (exit {result.returncode}): {detail}")
    if not dest.is_file():
        raise RestoreTestError("litestream restore reported success but wrote no file")
    return "litestream replica"


def latest_local_backup(backup_dir: Path) -> Path | None:
    if not backup_dir.is_dir():
        return None
    files = [p for p in backup_dir.iterdir() if p.is_file() and BACKUP_RE.match(p.name)]
    return max(files, key=_sort_key) if files else None


def restore_from_local(dest: Path, backup_dir: Path | None = None) -> str:
    backup_dir = backup_dir or default_backup_dir(settings.database_path)
    latest = latest_local_backup(backup_dir)
    if latest is None:
        raise RestoreTestError(f"no local backups found in {backup_dir}")
    src = sqlite3.connect(f"{latest.resolve().as_uri()}?mode=ro", uri=True)
    try:
        out = sqlite3.connect(str(dest))
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    return f"local backup {latest.name}"


def inspect_database(path: Path) -> dict:
    """Integrity check plus row counts; opened read-only."""
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        integrity = [row[0] for row in conn.execute("PRAGMA integrity_check")]
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        soft = {}
        for table in SOFT_DELETE_TABLES:
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if "deleted_at" in cols:
                live, deleted = conn.execute(
                    f"SELECT COALESCE(SUM(deleted_at IS NULL), 0), COALESCE(SUM(deleted_at IS NOT NULL), 0) FROM {table}"
                ).fetchone()
                soft[table] = (live, deleted)
    finally:
        conn.close()
    return {"integrity": integrity, "counts": counts, "soft": soft}


def run(source: str, backup_dir: Path | None = None) -> int:
    if source == "auto":
        source = "litestream" if litestream_configured() else "local"
    with tempfile.TemporaryDirectory(prefix="meraki-restore-test-") as tmp:
        dest = Path(tmp) / "restored.db"
        try:
            label = restore_from_litestream(dest) if source == "litestream" else restore_from_local(dest, backup_dir)
            report = inspect_database(dest)
        except (RestoreTestError, sqlite3.Error, subprocess.SubprocessError, OSError) as exc:
            print(f"restore test FAILED ({source}): {_scrub(str(exc))}", file=sys.stderr)
            return 1
    ok = report["integrity"] == ["ok"]
    print(f"source: {label}")
    print(f"integrity_check: {', '.join(report['integrity'])}")
    print("row counts:")
    for table, count in report["counts"].items():
        print(f"  {table}: {count}")
    if report["soft"]:
        print("live / soft-deleted:")
        for table, (live, deleted) in report["soft"].items():
            print(f"  {table}: {live} live, {deleted} soft-deleted")
    print("restore test PASSED" if ok else "restore test FAILED: integrity_check not ok")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify that a backup restores and is intact.")
    parser.add_argument("--source", choices=("auto", "local", "litestream"), default="auto")
    parser.add_argument("--backup-dir", type=Path, default=None, help="local backups dir (default: next to the DB)")
    args = parser.parse_args(argv)
    return run(args.source, args.backup_dir)


if __name__ == "__main__":
    raise SystemExit(main())
