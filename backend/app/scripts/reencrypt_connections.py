"""Re-encrypt stored processor keys with ENCRYPTION_KEY.

Run once after setting ENCRYPTION_KEY and before rotating SECRET_KEY:
    python -m app.scripts.reencrypt_connections
"""
import asyncio

from app.crypto import rotate_secret
from app.database import get_db


async def reencrypt_all(db) -> int:
    cursor = await db.execute("SELECT id, api_key_encrypted FROM connections")
    rows = await cursor.fetchall()
    for row in rows:
        await db.execute(
            "UPDATE connections SET api_key_encrypted = ? WHERE id = ?",
            (rotate_secret(row["api_key_encrypted"]), row["id"]),
        )
    await db.commit()
    return len(rows)


async def _main() -> None:
    agen = get_db()
    db = await agen.__anext__()
    try:
        count = await reencrypt_all(db)
        print(f"re-encrypted {count} connections")
    finally:
        await agen.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
