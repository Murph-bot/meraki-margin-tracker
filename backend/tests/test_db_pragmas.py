import aiosqlite

from app.config import settings
from app.database import apply_pragmas, get_db, init_db


async def _pragmas(db):
    out = {}
    for name in ("journal_mode", "synchronous", "busy_timeout", "foreign_keys"):
        out[name] = (await (await db.execute(f"PRAGMA {name}")).fetchone())[0]
    return out


EXPECTED = {
    "journal_mode": "wal",
    "synchronous": 1,
    "busy_timeout": 5000,
    "foreign_keys": 1,
}


async def test_get_db_sets_pragmas(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "a.db"))
    gen = get_db()
    db = await anext(gen)
    try:
        assert await _pragmas(db) == EXPECTED
    finally:
        await gen.aclose()


async def test_init_db_connection_sets_pragmas(tmp_path, monkeypatch):
    db_file = tmp_path / "b.db"
    monkeypatch.setattr(settings, "database_path", str(db_file))

    captured = {}
    original = apply_pragmas

    async def spy(db):
        await original(db)
        captured.update(await _pragmas(db))

    monkeypatch.setattr("app.database.apply_pragmas", spy)
    await init_db()

    assert captured == EXPECTED
    async with aiosqlite.connect(db_file) as db:
        assert (await (await db.execute("PRAGMA journal_mode")).fetchone())[0] == "wal"
