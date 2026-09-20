# Meraki — Margin Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a margin-tracking web app for Greek freelancers that shows true take-home pay after taxes, fees, and expenses.

**Architecture:** Python FastAPI backend with SQLite database, TypeScript React frontend with Vite + Tailwind. Deployed on Railway.

**Tech Stack:** Python 3.12+, FastAPI, aiosqlite, Stripe SDK, React 18, Vite, Tailwind CSS, React Query, Recharts

**Spec:** `docs/superpowers/specs/2026-09-19-meraki-design.md`

## Global Constraints

- SQLite for database (via aiosqlite for async)
- All tax rates hardcoded with source comments and disclaimer
- Frontend in TypeScript + React 18 + Vite
- Backend in Python 3.12+ with FastAPI
- Deploy on Railway (single service or frontend+backend split)
- Email/password auth with bcrypt + JWT
- Stripe read-only API keys for payment sync
- Environment variables for secrets (no hardcoded secrets)

---

## File Structure

```
meraki-margin-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app + CORS + lifespan
│   │   ├── config.py            # Settings from env vars (pydantic-settings)
│   │   ├── database.py          # SQLite init + get_db dependency
│   │   ├── models.py            # Pydantic models (request/response schemas)
│   │   ├── auth.py              # Password hashing, JWT create/verify, get_current_user
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth_router.py       # POST /signup, POST /login
│   │   │   ├── connections_router.py # CRUD for processor connections
│   │   │   ├── transactions_router.py # List synced transactions
│   │   │   ├── expenses_router.py    # CRUD for expenses
│   │   │   ├── dashboard_router.py   # GET /dashboard (main take-home data)
│   │   │   └── benchmarks_router.py  # GET /benchmarks
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── tax_engine.py         # Greek income tax + EFKA calculation
│   │   │   ├── margin_calculator.py  # Aggregates gross→fees→tax→net
│   │   │   ├── stripe_adapter.py     # Stripe API sync logic
│   │   │   ├── viva_adapter.py       # Viva Wallet API sync (stub for MVP)
│   │   │   └── sync_service.py       # Background scheduler for daily sync
│   │   └── database/
│   │       ├── __init__.py
│   │       └── schema.sql           # CREATE TABLE statements
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_tax_engine.py
│       ├── test_margin_calculator.py
│       └── test_auth.py
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── client.ts          # Axios instance + React Query setup
│   │   ├── pages/
│   │   │   ├── Landing.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Signup.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Connections.tsx
│   │   │   ├── Expenses.tsx
│   │   │   └── Reports.tsx
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── TakeHomeCard.tsx
│   │   │   ├── MarginBreakdown.tsx
│   │   │   ├── MarginChart.tsx
│   │   │   ├── ExpenseForm.tsx
│   │   │   └── ConnectionForm.tsx
│   │   └── lib/
│   │       ├── format.ts          # Currency, percentage formatting
│   │       └── constants.ts       # API base URL, chart colors
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── index.html
├── railway.toml
├── .env.example
└── docs/superpowers/specs/2026-09-19-meraki-design.md
```

---

### Phase 0: Research (Parallel)

### Task 0: Research 2026 Greek Tax Rates

**Files:** None (research output feeds Task 2.1)

- [ ] **Step 1: Search ΑΑΔΕ for current 2026 income tax brackets**

Search AADE (aade.gr) or Greek Ministry of Finance for the 2026 tax law (Νόμος 4387/2016 as amended). Find the current progressive income tax brackets for self-employed individuals.

- [ ] **Step 2: Search ΕΦΚΑ rates for 2026**

Find current ΕΦΚΑ social security contribution rates for self-employed (main insured, first 3 years reduced, minimum monthly amount, ceiling).

- [ ] **Step 3: Cross-reference with a Greek accounting resource**

Find at least one Greek accounting/tax blog that confirms the rates (e.g., taxheaven.gr, e-forologia.gr, or similar).

- [ ] **Step 4: Hardcode verified rates into tax_engine.py**

Write the rates as named constants with source URL comments. Flag with "VERIFIED: 2026-09-19 — update annually" comment.

---

### Phase 1: Foundation

### Task 1.1: Backend Project Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/__main__.py`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `railway.toml`

Full remaining plan text is in the local workspace copy of this file and must match disk exactly. This update restores structure; subsequent SHA update will replace with the complete local file if this payload is truncated by transport limits.
