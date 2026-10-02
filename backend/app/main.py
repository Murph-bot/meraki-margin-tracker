from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database import get_db
from app.routers.auth_router import router as auth_router
from app.routers.connections_router import router as connections_router
from app.routers.dashboard_router import router as dashboard_router
from app.routers.expenses_router import router as expenses_router
from app.routers.transactions_router import router as transactions_router
from app.routers.benchmarks_router import router as benchmarks_router

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import init_db
    await init_db()
    from app.services.sync_service import start_scheduler
    start_scheduler()
    yield
    from app.services.sync_service import stop_scheduler
    stop_scheduler()


app = FastAPI(title="Meraki", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(connections_router)
app.include_router(dashboard_router)
app.include_router(expenses_router)
app.include_router(transactions_router)
app.include_router(benchmarks_router)


@app.get("/health")
async def health(db=Depends(get_db)):
    await db.execute("SELECT 1")
    return {"status": "ok"}


def register_spa(app: FastAPI, dist: Path) -> None:
    assets = dist / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        root = dist.resolve()
        # Strip leading slashes: pathlib drops the base dir when joined with an
        # absolute path, which used to let `//etc/passwd` escape dist/.
        candidate = (root / full_path.lstrip("/")).resolve()
        if full_path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(root / "index.html")


if FRONTEND_DIST.exists():
    register_spa(app, FRONTEND_DIST)
