import os
import re
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
START_SH = REPO / "start.sh"
LITESTREAM_YML = REPO / "litestream.yml"
DOCKERFILE = REPO / "Dockerfile"

SECRETS = {
    "LITESTREAM_REPLICA_URL": "s3://bucket-SECRETVAL/meraki.db",
    "LITESTREAM_ACCESS_KEY_ID": "AKIA-SECRETVAL-ID",
    "LITESTREAM_SECRET_ACCESS_KEY": "SECRETVAL-secret-key",
    "LITESTREAM_ENDPOINT": "https://SECRETVAL.r2.example.com",
}
REPL_NAMES = list(SECRETS)


def _script(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def sandbox(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls.log"
    app_dir = tmp_path / "app" / "backend"
    app_dir.mkdir(parents=True)
    # The fakes log their argv (one line per call) and, for litestream restore,
    # optionally fail when FAKE_RESTORE_FAIL is set.
    _script(bindir / "uvicorn", f'echo "uvicorn $* [cwd=$(pwd)]" >> "{log}"\n')
    _script(
        bindir / "litestream",
        f'echo "litestream $*" >> "{log}"\n'
        '[ "$1" = restore ] && [ -n "${FAKE_RESTORE_FAIL:-}" ] && exit 3\n'
        "exit 0\n",
    )
    return {"bin": bindir, "log": log, "app": app_dir, "tmp": tmp_path}


def run_start(sandbox, env_extra=None, **kwargs):
    env = {
        "PATH": f"{sandbox['bin']}:/usr/bin:/bin",
        "APP_DIR": str(sandbox["app"]),
        "LITESTREAM_CONFIG": "/cfg/litestream.yml",
    }
    env.update(env_extra or {})
    return subprocess.run(
        ["sh", str(START_SH)], env=env, capture_output=True, text=True, timeout=30, **kwargs
    )


def calls(sandbox) -> list[str]:
    log = sandbox["log"]
    return log.read_text().splitlines() if log.exists() else []


def test_start_sh_syntax():
    subprocess.run(["sh", "-n", str(START_SH)], check=True)


def test_no_vars_runs_uvicorn_directly(sandbox):
    result = run_start(sandbox, {"PORT": "9123"})
    assert result.returncode == 0, result.stderr
    assert calls(sandbox) == [
        f"uvicorn app.main:app --host 0.0.0.0 --port 9123 [cwd={sandbox['app'].resolve()}]"
    ]
    assert "litestream" not in "".join(calls(sandbox)).replace("uvicorn", "")


def test_default_port_is_8000(sandbox):
    run_start(sandbox)
    assert "--port 8000 " in calls(sandbox)[0]


def test_partial_vars_warn_with_names_only_and_start_plain(sandbox):
    env = {
        "LITESTREAM_REPLICA_URL": SECRETS["LITESTREAM_REPLICA_URL"],
        "LITESTREAM_ACCESS_KEY_ID": SECRETS["LITESTREAM_ACCESS_KEY_ID"],
    }
    result = run_start(sandbox, env)
    assert result.returncode == 0
    assert "LITESTREAM_SECRET_ACCESS_KEY" in result.stderr
    assert "LITESTREAM_ENDPOINT" in result.stderr
    warning = next(line for line in result.stderr.splitlines() if "missing" in line)
    assert "LITESTREAM_REPLICA_URL" not in warning and "LITESTREAM_ACCESS_KEY_ID" not in warning
    assert "SECRETVAL" not in result.stdout + result.stderr
    log = calls(sandbox)
    assert len(log) == 1 and log[0].startswith("uvicorn ")


def test_empty_string_counts_as_missing(sandbox):
    env = dict(SECRETS, LITESTREAM_ENDPOINT="")
    result = run_start(sandbox, env)
    assert "LITESTREAM_ENDPOINT" in result.stderr
    assert calls(sandbox)[0].startswith("uvicorn ")


def test_all_vars_no_db_restores_then_replicates(sandbox):
    db = sandbox["tmp"] / "vol" / "meraki.db"
    env = dict(SECRETS, DATABASE_PATH=str(db), PORT="7000")
    result = run_start(sandbox, env)
    assert result.returncode == 0, result.stderr
    assert calls(sandbox) == [
        f"litestream restore -config /cfg/litestream.yml -if-db-not-exists -if-replica-exists {db}",
        "litestream replicate -config /cfg/litestream.yml "
        "-exec uvicorn app.main:app --host 0.0.0.0 --port 7000",
    ]
    assert db.parent.is_dir()  # start.sh creates the directory
    assert "SECRETVAL" not in result.stdout + result.stderr


def test_replicate_runs_from_app_dir(sandbox):
    _script(
        sandbox["bin"] / "litestream",
        f'echo "litestream $* [cwd=$(pwd) db=$LITESTREAM_DB_PATH]" >> "{sandbox["log"]}"\n',
    )
    db = sandbox["tmp"] / "meraki.db"
    db.touch()
    run_start(sandbox, dict(SECRETS, DATABASE_PATH=str(db)))
    line = calls(sandbox)[0]
    assert f"cwd={sandbox['app'].resolve()}" in line and f"db={db}" in line


def test_all_vars_existing_db_skips_restore(sandbox):
    db = sandbox["tmp"] / "meraki.db"
    db.write_bytes(b"x")
    result = run_start(sandbox, dict(SECRETS, DATABASE_PATH=str(db)))
    assert result.returncode == 0
    log = calls(sandbox)
    assert len(log) == 1 and log[0].startswith("litestream replicate ")


def test_restore_failure_aborts_without_starting_app(sandbox):
    db = sandbox["tmp"] / "meraki.db"
    result = run_start(sandbox, dict(SECRETS, DATABASE_PATH=str(db), FAKE_RESTORE_FAIL="1"))
    assert result.returncode != 0
    assert [c.split()[1] for c in calls(sandbox)] == ["restore"]
    assert "SECRETVAL" not in result.stdout + result.stderr


def test_disable_flag_forces_plain_start(sandbox):
    result = run_start(sandbox, dict(SECRETS, LITESTREAM_DISABLE="1"))
    assert result.returncode == 0
    log = calls(sandbox)
    assert len(log) == 1 and log[0].startswith("uvicorn ")


def test_railway_volume_wins_over_database_path(sandbox):
    vol = sandbox["tmp"] / "railway-vol"
    env = dict(SECRETS, RAILWAY_VOLUME_MOUNT_PATH=str(vol), DATABASE_PATH="/ignored/x.db")
    run_start(sandbox, env)
    assert f"-if-replica-exists {vol}/meraki.db" in calls(sandbox)[0]
    assert vol.is_dir()


def test_relative_default_resolves_against_app_dir(sandbox):
    run_start(sandbox, SECRETS)
    expected = f"{sandbox['app']}/data/meraki.db"
    assert calls(sandbox)[0].endswith(f"-if-replica-exists {expected}")
    assert (sandbox["app"] / "data").is_dir()


def test_relative_database_path_resolves_against_app_dir(sandbox):
    run_start(sandbox, dict(SECRETS, DATABASE_PATH="rel/x.db"))
    assert calls(sandbox)[0].endswith(f"-if-replica-exists {sandbox['app']}/rel/x.db")


# --------------------------------------------------------------- Dockerfile

def test_dockerfile_pins_litestream_version_and_checksums():
    text = DOCKERFILE.read_text()
    assert re.search(r"^ARG LITESTREAM_VERSION=0\.5\.17$", text, re.M)
    assert "cfb371176d164437ae869f8351cfde49bd1804ae71c61923f75c9cba9c9c006d" in text
    assert "f8ca4a050095c1efbda2c4365172e61bf9d955ea0d9ac42f448b52e51819baa5" in text
    assert "litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz" in text
    assert "litestream-${LITESTREAM_VERSION}-linux-arm64.tar.gz" in text
    assert "sha256sum -c" in text
    assert "ARG TARGETARCH=amd64" in text
    assert "unsupported TARGETARCH" in text
    assert "COPY litestream.yml /app/litestream.yml" in text
    assert "COPY --from=litestream /usr/local/bin/litestream /usr/local/bin/litestream" in text


# ------------------------------------------------- real litestream binary

LITESTREAM_TEST_BIN = os.environ.get("LITESTREAM_TEST_BIN")
needs_binary = pytest.mark.skipif(
    not (LITESTREAM_TEST_BIN and os.access(LITESTREAM_TEST_BIN, os.X_OK)),
    reason="LITESTREAM_TEST_BIN not set to an executable",
)


@needs_binary
def test_real_litestream_replicate_and_restore(tmp_path):
    db = tmp_path / "src" / "meraki.db"
    db.parent.mkdir()
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.executemany("INSERT INTO t (v) VALUES (?)", [("a",), ("b",), ("c",)])
    conn.commit()
    conn.close()

    env = {
        **os.environ,
        "LITESTREAM_DB_PATH": str(db),
        "LITESTREAM_REPLICA_URL": f"file://{tmp_path / 'replica'}",
        "LITESTREAM_ENDPOINT": "",
        "LITESTREAM_ACCESS_KEY_ID": "",
        "LITESTREAM_SECRET_ACCESS_KEY": "",
    }
    rep = subprocess.run(
        [LITESTREAM_TEST_BIN, "replicate", "-config", str(LITESTREAM_YML), "-exec", "sleep 3"],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert rep.returncode == 0, rep.stderr

    out = tmp_path / "restored" / "meraki.db"
    res = subprocess.run(
        [LITESTREAM_TEST_BIN, "restore", "-config", str(LITESTREAM_YML), "-o", str(out), str(db)],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert res.returncode == 0, res.stderr
    restored = sqlite3.connect(out)
    try:
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert [r[0] for r in restored.execute("SELECT v FROM t ORDER BY id")] == ["a", "b", "c"]
    finally:
        restored.close()
