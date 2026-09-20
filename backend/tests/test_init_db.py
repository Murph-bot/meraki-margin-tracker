import aiosqlite
from app.config import settings
from app.database import init_db


async def test_init_db_adds_missing_user_columns(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    async with aiosqlite.connect(db_file) as db:
        await db.execute(
            """CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT ''
            )"""
        )
        await db.execute(
            "INSERT INTO users (email, password_hash, name) VALUES ('a@b.c', 'hash', 'A')"
        )
        await db.commit()

    monkeypatch.setattr(settings, "database_path", str(db_file))
    await init_db()

    async with aiosqlite.connect(db_file) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("PRAGMA table_info(users)")
        cols = {row[1] for row in await cursor.fetchall()}
        user = await (await db.execute("SELECT * FROM users WHERE email = 'a@b.c'")).fetchone()

    assert "efka_category" in cols
    assert "years_active" in cols
    assert "charges_vat" in cols
    assert user["efka_category"] == 1
    assert user["years_active"] == 1
    assert user["charges_vat"] == 0
