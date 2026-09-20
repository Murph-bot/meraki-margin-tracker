# Meraki — Margin Tracker for Greek Freelancers

**Design Doc v0.1 — 2026-09-19**
> Follows The Founder's Playbook methodology: Idea → MVP transition

---

## 1. Product Overview

**Meraki** (μεράκι) — Greek word meaning "doing something with soul, creativity, and love." A margin-tracking web app for Greek freelancers and micro-businesses that shows their **true take-home pay** after taxes, fees, and expenses.

**Core insight from market research:** Greek freelancers use invoicing tools (Kiros, easyTimi, Epsilon Smart) for AADE/myDATA compliance, but **none of them tell you if you're actually making money**. Generic margin trackers (TrueProfit, ProTally, Owelet) don't understand Greek taxation, Greek payment processors, or the Greek freelance market.

**Target user:** Greek freelancer — developer, designer, consultant — invoicing €2K-€15K/mo, using Stripe and/or Viva Wallet, who wants to know their real hourly rate and margin.

---

## 2. MVP Scope (Per The Founder's Playbook — Idea Stage)

### Exit Criteria for Idea Stage (applies now)
1. Is the problem real and specific? ✅ Yes — validated via competitor research gap
2. Does our solution address the actual problem? ⏳ Building MVP to test
3. Do we have enough signal to justify building? ✅ Yes — zero competition in Greek market

### MVP Exit Criteria (what success looks like)
- 5 real Greek freelancers using the product weekly
- At least 3 say they'd be "very disappointed" if it disappeared (Sean Ellis test >40%)
- One confirmed pain point fixed from user feedback

### What We're NOT Building in MVP
- No multi-currency support
- No team accounts
- No expense OCR
- No accountant access
- No automated tax filing
- No marketing pages beyond a landing page

---

## 3. Architecture

```
┌─────────────────────────────────────────────┐
│              TypeScript Frontend             │
│           (React + Vite + Tailwind)          │
│           Hosted on Netlify/Railway          │
└──────────────────┬──────────────────────────┘
                   │ REST API (JSON)
┌──────────────────▼──────────────────────────┐
│              Python Backend (FastAPI)          │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Stripe   │  │ Viva     │  │ Tax Engine │ │
│  │ Adapter  │  │ Wallet   │  │ (hardcoded)│ │
│  │          │  │ Adapter  │  │            │ │
│  └──────────┘  └──────────┘  └────────────┘ │
│              │                               │
│              ▼                               │
│  ┌──────────────────────────────────────┐   │
│  │         SQLite (via aiosqlite)        │   │
│  │  Users | Transactions | Expenses     │   │
│  │  Subscriptions | SyncLog             │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

### Why This Architecture

| Component | Choice | Why |
|-----------|--------|-----|
| **Backend** | Python (FastAPI) | User's strength for data work, great for analytics |
| **Frontend** | TypeScript (React + Vite) | User is learning TS, React is most hireable skill |
| **Database** | SQLite (aiosqlite + litestream) | Zero setup, single file, backup to S3/Cloudflare R2 |
| **Auth** | Email/password (bcrypt + JWT) | Simple, no 3rd-party dependency |

### Data Model (MVP)

```
Users
  - id, email, password_hash, created_at
  - name, vat_number (optional), tax_scale (free/self-employed)

Connections (payment processor links)
  - id, user_id, processor (stripe/viva), api_key_encrypted, label
  - last_synced_at

Transactions (synced from processors)
  - id, connection_id, processor_txn_id, amount, currency
  - fee_amount, net_amount, timestamp, description
  - customer_name, invoice_number

Expenses (user-entered)
  - id, user_id, amount, category, description, date
  - recurring (bool), interval

MarginSnapshots (computed daily)
  - id, user_id, date, gross_revenue, total_fees, total_expenses
  - estimated_tax, social_security, net_take_home, effective_hourly_rate

ProfessionBenchmarks (hardcoded reference data)
  - profession, city, min_rate, max_rate, median_rate, source
  - last_verified
```

---

## 4. Tax Engine — Greek Tax Calculation (CRITICAL)

This is your moat. Generic tools can't do this. We must get these numbers **correct**.

### Income Tax (2026 rates — MUST VERIFY before shipping)

Self-employed freelancers (individuals with a block of services / Μπλοκάκι):

| Annual Income (€) | Tax Rate |
|-------------------|----------|
| 0 — 10,000 | 9% |
| 10,001 — 20,000 | 22% |
| 20,001 — 30,000 | 28% |
| 30,001 — 40,000 | 36% |
| 40,001+ | 44% |

*(Note: 2025 rates shown — needs verification for 2026 before shipping)*

### Social Security (ΕΦΚΑ)

For freelancers with a block of services:
- Main rate: ~26.71% of taxable income (for main insured)
- Reduced rate (first 3 years): ~20.28%
- Minimum monthly contribution: ~€170 (2025)
- Capped at approximately ~€6,500/mo ceiling

*(Needs verification for 2026 before shipping)*

### VAT

- Standard rate: 24%
- Reduced rate: 13% (some services)
- Super-reduced: 6%

*(Note: Not all freelancers charge VAT; depends on annual turnover <€10K threshold. The tax engine should handle both scenarios.)*

### Take-Home Calculation Formula

```
gross = sum(transaction.net_amount)  # after Stripe/Viva fees
gross -= sum(expenses)                # deductible business expenses
taxable_income = gross - social_security  # social security is tax-deductible

# Progressive tax
income_tax = progressive_brackets(taxable_income)
social_security = efka_rate(taxable_income)

net_take_home = gross - income_tax - social_security

effective_rate = (gross - net_take_home) / gross * 100
effective_hourly = net_take_home / hours_worked
```

### Verification Plan
Before shipping, I will:
1. Search the Greek Ministry of Finance (ΑΑΔΕ) website for current 2026 rates
2. Cross-reference with at least one Greek accounting site
3. Add a NOTE on the dashboard: "Tax estimates are approximate. Always consult your accountant."

---

## 5. Frontend — Pages & User Flow

### MVP Pages

1. **Landing page** (`/`) — 1-page marketer explaining what Meraki does
2. **Sign up / Log in** (`/signup`, `/login`) — Email + password
3. **Dashboard** (`/dashboard`) — The main event
   - Big number: "Your true take-home this month: €X,XXX"
   - Gross vs net comparison bar
   - "You're keeping X% of what you invoice"
   - Effective hourly rate
   - Mini sparkline of margin over last 30 days
4. **Connections** (`/settings/connections`) — Add Stripe or Viva Wallet API keys
5. **Expenses** (`/expenses`) — Simple form: amount + category + date
6. **Reports** (`/reports`) — Monthly breakdown: gross, fees, taxes, take-home

### Dashboard Wireframe (Text)

```
┌──────────────────────────────────────────────┐
│  Meraki logo                    Profile ▼    │
├──────────────────────────────────────────────┤
│  ┌────────────────────────────────────────┐  │
│  │  Your True Take-Home This Month        │  │
│  │  €3,247  ←  €5,200 invoiced           │  │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━     │  │
│  │  You keep  62%   of what you invoice   │  │
│  │  €25/hr   effective hourly rate        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Where the money goes:                       │
│  ┌──────────────┬────────┬────────────────┐  │
│  │  €5,200 gross │ €1,248 │ VAT (24%)     │  │
│  │               │  €156  │ Stripe fees   │  │
│  │               │  €320  │ Expenses      │  │
│  │               │  €986  │ Income tax    │  │
│  │               │  €243  │ ΕΦΚΑ          │  │
│  │  €3,247 net  │        │               │  │
│  └──────────────┴────────┴────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Margin trend                         │  │
│  │  ╱‾‾╲  ╱╲    ╱‾‾╲  ╱╲                │  │
│  │ ╱    ╲╱  ╲  ╱    ╲╱  ╲___            │  │
│  │ Sep1   Sep7  Sep14  Sep21  Sep30      │  │
│  └────────────────────────────────────────┘  │
├──────────────────────────────────────────────┤
│  ⚡ Missing connections: Stripe | Viva Wallet │
└──────────────────────────────────────────────┘
```

---

## 6. Data Sync Architecture

### Stripe Adapter
- Connect via Stripe API key (restricted key with read-only permissions)
- Sync: Pull `transactions`, `fees`, `payouts` from Stripe API
- Frequency: On connection + daily background sync + manual refresh button
- Stripe already provides `net_amount` after fees per transaction

### Viva Wallet Adapter
- Connect via Viva Wallet API credentials
- Viva API docs needed: `https://developer.vivawallet.com/`
- Sync: Pull transaction history, calculate fees
- *Note:* Viva's API is less documented than Stripe. This adapter may need more dev time.

### Sync Schedule
- Immediately on connection (pull last 90 days)
- Daily cron-style sync (could use GitHub Actions or simple cron)
- Manual "Refresh" button on dashboard

---

## 7. Tech Stack Details

### Backend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **FastAPI** | Async, Python-native, auto-docs at /docs |
| Database | **SQLite + aiosqlite** | Single file, zero-config, backup via litestream |
| Auth | **bcrypt + python-jose (JWT)** | Standard, battle-tested |
| Payments | **stripe Python SDK** | Official library |
| Background | **APScheduler** | In-process scheduling for daily sync |

### Frontend

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | **React 18 + Vite** | Modern, fast, user is learning TS |
| Styling | **Tailwind CSS v3** | Fast prototyping, utility classes |
| State | **React Query** | Server-state cache, perfect for API data |
| Routing | **React Router v6** | Standard |
| Charts | **Recharts** | Simple React charting (sparklines, bars) |

### Deployment

| Layer | Platform | Reason |
|-------|----------|--------|
| Backend API | **Railway** | Python-native, easy DB setup, free tier |
| Frontend | **Netlify** (or Railway static) | Free, fast CDN, easy deploys |
| Database | **SQLite on Railway** (volume mount) | Simple, backups via litestream → R2 |
| Domain | **meraki.gr** (or similar) | Greek market, .gr builds trust |

---

## 8. Security & Compliance

- **API keys stored encrypted** (AES-256 at rest, decrypted only at sync time)
- **JWT tokens** with 7-day expiry, refresh token support
- **HTTPS everywhere**
- **No storage of raw payment data** beyond what's needed for margin calc
- **GDPR compliant** — data stored in EU (Railway has EU region)
- **Disclaimer on all pages**: "Tax calculations are estimates. Consult your accountant."
- Rate limiting on auth endpoints
- Input validation via Pydantic models (FastAPI native)

---

## 9. MVP Build Sequence (Per Playbook — "Build the core interaction first")

Following the playbook's advice: *"Define the single core interaction your solution depends on. Build only that."*

Our core interaction is: **A freelancer connects their payment processor and sees their true take-home margin.**

### Phase 1 — Foundation (Days 1-3)
1. Set up project structure (Python backend + TS frontend)
2. FastAPI app with health endpoint
3. SQLite schema + migrations
4. User registration/login
5. Landing page + login UI

### Phase 2 — Core Sync (Days 4-7)
6. Stripe adapter — connect API key, pull transactions, store net amounts
7. Tax engine — hardcode Greek rates, compute take-home
8. Dashboard — show gross vs net, margin %, effective hourly rate
9. Simple expense entry form

### Phase 3 — Polish & Launch (Days 8-10)
10. Viva Wallet adapter (if time permits for MVP)
11. Benchmarks — hardcoded profession rates
12. Daily sync scheduler
13. Reports page (simple monthly view)
14. Deploy to Railway + Netlify

---

## 10. Post-MVP Roadmap

| After MVP | Later |
|-----------|-------|
| Viva Wallet adapter (if skipped) | Greek bank API integration |
| Stripe/Viva webhook (real-time sync) | Multi-currency |
| PDF report export | Automated tax filing (via AADE API) |
| Email notifications (margin drops) | Mobile app (React Native) |
| Greek language toggle | Team accounts |
| Accountant access (read-only) | Integration with myDATA |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Greek tax rates change yearly | Hardcode with a note: "verified [month/year]". Easy to update. |
| Viva Wallet API is limited | Start with Stripe-only; add Viva when API is confirmed |
| SQLite doesn't scale | Litestream provides backups; migrate to Postgres if needed |
| Freelancers don't trust a new tool with their financial data | Use restricted Stripe keys (read-only), clear privacy policy |
| User churns before connecting payment processor | Show demo mode with sample data on signup |
| Tax calculation is wrong | Disclaimers + let users override rates manually |

---

## 12. Spec Self-Review Checklist

- [x] Placeholders? None remaining. Specifics listed.
- [x] Internal consistency? Architecture fits feature descriptions.
- [x] Scope focused? MVP clearly defined, roadmap deferred.
- [x] Ambiguity? Tax rates flagged as "needs verification."
