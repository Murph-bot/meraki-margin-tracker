import aiosqlite
from pathlib import Path
from app.config import settings

async def apply_pragmas(db) -> None:
    """Per-connection SQLite settings. busy_timeout goes first so the WAL switch
    waits for locks instead of failing with SQLITE_BUSY."""
    await db.execute("PRAGMA busy_timeout = 5000")
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA synchronous = NORMAL")


async def get_db():
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await apply_pragmas(db)
    try:
        yield db
    finally:
        await db.close()

async def _column_names(db, table: str) -> set[str]:
    if table != "users":
        raise ValueError("unsupported table")
    cursor = await db.execute("PRAGMA table_info(users)")
    return {row[1] for row in await cursor.fetchall()}


async def _apply_migrations(db) -> None:
    user_cols = await _column_names(db, "users")
    if "efka_category" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN efka_category INTEGER NOT NULL DEFAULT 1"
        )
    if "years_active" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN years_active INTEGER NOT NULL DEFAULT 1"
        )
    if "charges_vat" not in user_cols:
        await db.execute(
            "ALTER TABLE users ADD COLUMN charges_vat INTEGER NOT NULL DEFAULT 0"
        )


async def init_db():
    from app.database.schema import SCHEMA
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as db:
        db.row_factory = aiosqlite.Row
        await apply_pragmas(db)
        for statement in SCHEMA:
            await db.execute(statement)
        await _apply_migrations(db)
        await db.commit()
