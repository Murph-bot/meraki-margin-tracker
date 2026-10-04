"""Permanently delete soft-deleted rows older than N days (see docs/soft-deletes.md).

Run from backend/:  python -m app.scripts.purge_deleted [--days 30] [--dry-run]
"""
import argparse
import sqlite3

from app.config import settings

DEFAULT_DAYS = 30

# Child rows first: transactions reference connections (foreign_keys is ON).
_PURGE_STATEMENTS = (
    (
        "transactions",
        """DELETE FROM transactions
           WHERE deleted_at < :cutoff
              OR connection_id IN (SELECT id FROM connections WHERE deleted_at < :cutoff)""",
        """SELECT COUNT(*) FROM transactions
           WHERE deleted_at < :cutoff
              OR connection_id IN (SELECT id FROM connections WHERE deleted_at < :cutoff)""",
    ),
    (
        "connections",
        "DELETE FROM connections WHERE deleted_at < :cutoff",
        "SELECT COUNT(*) FROM connections WHERE deleted_at < :cutoff",
    ),
    (
        "expenses",
        "DELETE FROM expenses WHERE deleted_at < :cutoff",
        "SELECT COUNT(*) FROM expenses WHERE deleted_at < :cutoff",
    ),
)


def purge_deleted(db_path, days: int = DEFAULT_DAYS, dry_run: bool = False) -> dict[str, int]:
    """Hard-delete rows soft-deleted more than `days` days ago, in one transaction.
    Returns per-table counts (what would be removed when dry_run)."""
    if days < 0:
        raise ValueError("days must be >= 0")
    conn = sqlite3.connect(str(db_path), isolation_level=None)
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            cutoff = conn.execute("SELECT datetime('now', ?)", (f"-{int(days)} days",)).fetchone()[0]
            counts: dict[str, int] = {}
            for table, delete_sql, count_sql in _PURGE_STATEMENTS:
                params = {"cutoff": cutoff}
                if dry_run:
                    counts[table] = conn.execute(count_sql, params).fetchone()[0]
                else:
                    counts[table] = conn.execute(delete_sql, params).rowcount
            conn.execute("ROLLBACK" if dry_run else "COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        return counts
    finally:
        conn.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Purge old soft-deleted rows.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="age threshold in days")
    parser.add_argument("--dry-run", action="store_true", help="report counts, delete nothing")
    args = parser.parse_args(argv)
    counts = purge_deleted(settings.database_path, days=args.days, dry_run=args.dry_run)
    verb = "Would purge" if args.dry_run else "Purged"
    summary = ", ".join(f"{n} {table}" for table, n in counts.items())
    print(f"{verb} (deleted more than {args.days} days ago): {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
