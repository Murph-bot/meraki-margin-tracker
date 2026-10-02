from pathlib import Path

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import register_spa


def _make_dist(tmp_path: Path) -> tuple[Path, Path]:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    (dist / "favicon.svg").write_text("<svg/>")
    secret = tmp_path / "outside" / "meraki.db"
    secret.parent.mkdir()
    secret.write_text("SECRET-DB-CONTENT")
    return dist, secret


async def _get(app: FastAPI, raw_path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        return await ac.get(raw_path)


async def test_spa_serves_files_inside_dist(tmp_path):
    dist, _ = _make_dist(tmp_path)
    app = FastAPI()
    register_spa(app, dist)
    r = await _get(app, "/favicon.svg")
    assert r.status_code == 200
    assert r.text == "<svg/>"
    r = await _get(app, "/dashboard")
    assert r.text == "<html>spa</html>"


async def test_spa_does_not_serve_absolute_paths_outside_dist(tmp_path):
    dist, secret = _make_dist(tmp_path)
    app = FastAPI()
    register_spa(app, dist)
    for path in ("/" + str(secret), "/%2F" + str(secret).lstrip("/"), "/../outside/meraki.db"):
        r = await _get(app, path)
        assert "SECRET-DB-CONTENT" not in r.text, path
        assert r.text == "<html>spa</html>", path
