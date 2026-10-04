import sqlite3

import pytest

from app.scripts.backup_db import BACKUP_RE, backup_database, prune_backups


def _make_wal_db(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.executemany("INSERT INTO t (v) VALUES (?)", [("a",), ("b",)])
    conn.commit()
    return conn


def test_backup_while_wal_connection_open(tmp_path):
    db_file = tmp_path / "meraki.db"
    conn = _make_wal_db(db_file)
    # Committed rows live in the -wal file (no checkpoint yet); this one is uncommitted.
    conn.execute("INSERT INTO t (v) VALUES ('c')")
    conn.commit()
    conn.execute("INSERT INTO t (v) VALUES ('uncommitted')")

    dest = backup_database(db_file)

    assert dest.parent == tmp_path / "backups"
    assert BACKUP_RE.match(dest.name)
    copy = sqlite3.connect(dest)
    try:
        assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert [r[0] for r in copy.execute("SELECT v FROM t ORDER BY id")] == ["a", "b", "c"]
    finally:
        copy.close()
    conn.rollback()
    conn.close()


def test_backup_twice_same_second_no_collision(tmp_path):
    db_file = tmp_path / "meraki.db"
    _make_wal_db(db_file).close()
    first = backup_database(db_file)
    second = backup_database(db_file)
    assert first != second
    assert first.exists() and second.exists()


def test_backup_missing_db_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        backup_database(tmp_path / "nope.db")
    assert not (tmp_path / "backups").exists()


def test_retention_keeps_newest_14_and_ignores_unrelated(tmp_path):
    backups = tmp_path / "backups"
    backups.mkdir()
    names = [f"meraki-202601{d:02d}T000000Z.db" for d in range(1, 21)]
    names.append("meraki-20260105T000000Z-1.db")
    for n in names:
        (backups / n).write_bytes(b"x")
    unrelated = ["notes.txt", "meraki.db", "meraki-latest.db", "other-20250101T000000Z.db"]
    for n in unrelated:
        (backups / n).write_bytes(b"keep")

    prune_backups(backups, keep=14)

    remaining = sorted(p.name for p in backups.iterdir() if BACKUP_RE.match(p.name))
    assert len(remaining) == 14
    assert remaining == [f"meraki-202601{d:02d}T000000Z.db" for d in range(7, 21)]
    assert "meraki-20260120T000000Z.db" in remaining
    assert "meraki-20260101T000000Z.db" not in remaining
    for n in unrelated:
        assert (backups / n).read_bytes() == b"keep"


def test_backup_prunes_to_keep(tmp_path):
    db_file = tmp_path / "meraki.db"
    _make_wal_db(db_file).close()
    for _ in range(5):
        backup_database(db_file, keep=3)
    assert len([p for p in (tmp_path / "backups").iterdir() if BACKUP_RE.match(p.name)]) == 3
