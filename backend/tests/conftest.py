import os
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-0123456789abcdef")
os.environ.setdefault("TESTING", "1")

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.setdefault("DATABASE_PATH", _tmp_db.name)

import pytest
import aiosqlite
from httpx import ASGITransport, AsyncClient
from app.database.schema import SCHEMA


@pytest.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        for stmt in SCHEMA:
            await conn.execute(stmt)
        await conn.commit()
        yield conn


@pytest.fixture
async def client(db):
    from app.main import app
    from app.database import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    # httpx 0.28 has no lifespan= argument and does not send ASGI lifespan events.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
