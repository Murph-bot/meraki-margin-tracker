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

See local file `docs/superpowers/plans/2026-09-19-meraki-implementation.md` for the complete task-by-task plan covering Phase 0 research, Phase 1 foundation (scaffolding, auth, frontend), Phase 2 core sync (tax engine, margin calculator, Stripe adapter, dashboard APIs/UI), Phase 3 polish and deploy, and the self-review checklist.
