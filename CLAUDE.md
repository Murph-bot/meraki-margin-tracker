# Meraki

Take-home pay for Greek freelancers: pulls Stripe payments and shows what you keep each month
after VAT, processor fees, ΕΦΚΑ contributions, income tax and expenses. See `README.md`.

## Layout

- `backend/` — FastAPI, SQLite (WAL) via aiosqlite, APScheduler daily sync, bcrypt + JWT
  - `app/services/tax_engine.py` — Greek tax rules (sources cited in the file)
  - `app/services/margin_calculator.py`, `expense_schedule.py`, `soft_delete.py`
  - `app/services/stripe_adapter.py`; `viva_adapter.py` is a planned, unavailable integration
  - `app/crypto.py` — Fernet encryption of stored API keys
- `frontend/` — React, TypeScript, Vite, Tailwind, TanStack Query, i18next (Greek default)

## Commands

- Backend (from `backend/`): `pip install -r requirements-dev.txt`, `python -m app`, `pytest`
- Frontend (from `frontend/`): `npm ci`, `npm run dev`, `npm test`, `npm run build`

## Rules

- Tax figures are estimates for 2026 rules (ν. 5246/2025, ΕΦΚΑ circular 6/2026, prepayment 55% /
  27.5% first year). Any rate or threshold change must update the cited source in `tax_engine.py`
  and its tests.
- Money is computed in one place (`tax_engine.py` / `margin_calculator.py`); do not recompute in routers or UI.
- Stripe keys are read-only restricted keys, encrypted at rest. Never log them.
- UI strings go through i18next in both Greek and English.
- Run `/verify` before reporting work done.
