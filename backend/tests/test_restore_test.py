import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.scripts import restore_test
from app.scripts.backup_db import backup_database
from app.database.schema import SCHEMA, SOFT_DELETE_INDEXES

LITESTREAM_YML = Path(__file__).resolve().parents[2] / "litestream.yml"


def _make_db(path, with_deleted=True):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    for stmt in SCHEMA + SOFT_DELETE_INDEXES:
        conn.execute(stmt)
    conn.execute("INSERT INTO users (email, password_hash) VALUES ('r@y.z', 'h')")
    conn.execute("INSERT INTO expenses (user_id, amount_cents, date) VALUES (1, 5, '2026-01-01')")
    if with_deleted:
        conn.execute(
            "INSERT INTO expenses (user_id, amount_cents, date, deleted_at) "
            "VALUES (1, 6, '2026-01-02', '2026-02-01 00:00:00')"
        )
    conn.commit()
    conn.close()


@pytest.fixture
def clean_env(monkeypatch):
    for name in (*restore_test.REPLICATION_VARS, "LITESTREAM_BIN", "LITESTREAM_CONFIG", "LITESTREAM_DB_PATH"):
        monkeypatch.delenv(name, raising=False)


def test_local_restore_reports_counts(tmp_path, monkeypatch, capsys, clean_env):
    db = tmp_path / "meraki.db"
    _make_db(db)
    backup_database(db)
    monkeypatch.setattr(settings, "database_path", str(db))

    assert restore_test.main(["--source", "local"]) == 0

    out = capsys.readouterr().out
    assert "source: local backup meraki-" in out
    assert "integrity_check: ok" in out
    assert "users: 1" in out and "expenses: 2" in out
    assert "expenses: 1 live, 1 soft-deleted" in out
    assert "restore test PASSED" in out


def test_local_restore_picks_newest_backup(tmp_path, monkeypatch, capsys, clean_env):
    db = tmp_path / "meraki.db"
    _make_db(db, with_deleted=False)
    backup_database(db)
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO expenses (user_id, amount_cents, date) VALUES (1, 7, '2026-01-03')")
    conn.commit()
    conn.close()
    newest = backup_database(db)
    monkeypatch.setattr(settings, "database_path", str(db))

    assert restore_test.main(["--source", "local"]) == 0
    out = capsys.readouterr().out
    assert newest.name in out and "expenses: 2" in out


def test_no_backup_fails_nonzero(tmp_path, monkeypatch, capsys, clean_env):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "meraki.db"))
    assert restore_test.main(["--source", "local"]) == 1
    assert "no local backups" in capsys.readouterr().err


def test_auto_falls_back_to_local_without_litestream_vars(tmp_path, monkeypatch, capsys, clean_env):
    db = tmp_path / "meraki.db"
    _make_db(db)
    backup_database(db)
    monkeypatch.setattr(settings, "database_path", str(db))
    assert restore_test.main([]) == 0
    assert "source: local backup" in capsys.readouterr().out


def test_auto_prefers_litestream_when_configured(monkeypatch, tmp_path, clean_env):
    fake = tmp_path / "litestream"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    for name in restore_test.REPLICATION_VARS:
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("LITESTREAM_BIN", str(fake))
    assert restore_test.litestream_configured()
    monkeypatch.setenv("LITESTREAM_ENDPOINT", "")
    assert not restore_test.litestream_configured()


def test_corrupt_backup_fails(tmp_path, monkeypatch, capsys, clean_env):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    (bdir / "meraki-20260101T000000Z.db").write_bytes(b"this is not a sqlite database" * 100)
    assert restore_test.main(["--source", "local", "--backup-dir", str(bdir)]) == 1
    assert "FAILED" in capsys.readouterr().err


def test_litestream_failure_does_not_leak_secrets(tmp_path, monkeypatch, capsys, clean_env):
    fake = tmp_path / "litestream"
    fake.write_text("#!/bin/sh\necho \"boom key=$LITESTREAM_SECRET_ACCESS_KEY\" >&2\nexit 2\n")
    fake.chmod(0o755)
    monkeypatch.setenv("LITESTREAM_BIN", str(fake))
    monkeypatch.setenv("LITESTREAM_CONFIG", str(LITESTREAM_YML))
    monkeypatch.setenv("LITESTREAM_SECRET_ACCESS_KEY", "SUPERSECRETVALUE")
    assert restore_test.main(["--source", "litestream"]) == 1
    captured = capsys.readouterr()
    assert "SUPERSECRETVALUE" not in captured.out + captured.err
    assert "boom" in captured.err


LITESTREAM_TEST_BIN = os.environ.get("LITESTREAM_TEST_BIN")


@pytest.mark.skipif(
    not (LITESTREAM_TEST_BIN and os.access(LITESTREAM_TEST_BIN, os.X_OK)),
    reason="LITESTREAM_TEST_BIN not set to an executable",
)
def test_litestream_restore_with_real_binary(tmp_path, monkeypatch, capsys, clean_env):
    db = tmp_path / "meraki.db"
    _make_db(db)
    replica = tmp_path / "replica"
    env = {
        **os.environ,
        "LITESTREAM_DB_PATH": str(db),
        "LITESTREAM_REPLICA_URL": f"file://{replica}",
        "LITESTREAM_ENDPOINT": "",
        "LITESTREAM_ACCESS_KEY_ID": "",
        "LITESTREAM_SECRET_ACCESS_KEY": "",
    }
    subprocess.run(
        [LITESTREAM_TEST_BIN, "replicate", "-config", str(LITESTREAM_YML), "-exec", "sleep 3"],
        env=env, check=True, capture_output=True, timeout=60,
    )
    for key in ("LITESTREAM_DB_PATH", "LITESTREAM_REPLICA_URL", "LITESTREAM_ENDPOINT",
                "LITESTREAM_ACCESS_KEY_ID", "LITESTREAM_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(key, env[key])
    monkeypatch.setenv("LITESTREAM_BIN", LITESTREAM_TEST_BIN)
    monkeypatch.setenv("LITESTREAM_CONFIG", str(LITESTREAM_YML))

    assert restore_test.main(["--source", "litestream"]) == 0

    out = capsys.readouterr().out
    assert "source: litestream replica" in out
    assert "integrity_check: ok" in out
    assert "expenses: 1 live, 1 soft-deleted" in out
