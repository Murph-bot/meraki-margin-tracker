# Meraki

Take-home pay for Greek freelancers. Meraki pulls your Stripe payments and shows what you actually keep each month after VAT, processor fees, ΕΦΚΑ contributions, income tax and your own expenses.

Most invoicing tools stop at revenue. A freelancer in Greece pays a fixed ΕΦΚΑ category every month, income tax on a progressive scale, and a tax prepayment that hits cash flow a year later. Meraki puts all of that on one screen.

## What it does

- **Monthly take-home.** Net income after VAT (24%), Stripe fees, ΕΦΚΑ + ΔΥΠΑ, income tax and expenses, with the share of each invoice you keep.
- **Greek tax rules for 2026.** Income tax scale from ν. 5246/2025, the six ΕΦΚΑ categories from circular 6/2026, and the 55% prepayment (27.5% in the first year). Sources are cited in `backend/app/services/tax_engine.py`.
- **Stripe sync.** Connect a read-only restricted key. Keys are encrypted at rest with Fernet and synced daily. Viva Wallet is planned but not available yet.
- **Expenses.** One-off and recurring, with soft delete and restore.
- **Margin trend and reports.** Monthly history of what you kept, charted with Recharts.
- **Greek and English.** The UI defaults to Greek.

Tax figures are estimates. Check them with your accountant.

## Stack

- **Backend:** FastAPI, SQLite (WAL) via aiosqlite, APScheduler for daily sync, bcrypt and JWT auth
- **Frontend:** React, TypeScript, Vite, Tailwind, TanStack Query, i18next
- **Deploy:** one Docker image on Railway, with optional Litestream replication to Cloudflare R2

## Run it locally

```bash
# Backend (http://localhost:8000)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # set SECRET_KEY to a long random string
python -m app

# Frontend (http://localhost:5173, proxies /api to the backend)
cd frontend
npm ci
npm run dev
```

Tests: `pytest` in `backend/`, `npm test` in `frontend/`.

## Deploy

`railway.toml` builds the `Dockerfile`, which bundles the built frontend into the FastAPI image. Mount a Railway volume and the database moves onto it automatically (`RAILWAY_VOLUME_MOUNT_PATH`). Set `SECRET_KEY`, and set `ENCRYPTION_KEY` so you can rotate the JWT secret without losing stored Stripe keys.

## Backups

The SQLite database runs in WAL mode; back it up with
`python -m app.scripts.backup_db` (from `backend/`). See [docs/backups.md](docs/backups.md)
for how to run it (manual, on request) and restore.

For continuous off-host replication to Cloudflare R2 (Litestream, started by `start.sh`
when configured), see [docs/litestream.md](docs/litestream.md). Verify any backup with
`python -m app.scripts.restore_test`.

## Soft deletes

Deleting a connection or an expense hides it; it can be undone via
`POST /api/connections/{id}/restore` / `POST /api/expenses/{id}/restore` until a purge is run.
The purge script (manual, never scheduled) removes rows deleted more than 30 days ago. See [docs/soft-deletes.md](docs/soft-deletes.md).
