# Alpaca Public Dashboard Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the Mac mini's redacted Alpaca paper-loop projection to the existing public Railway `/alpaca` page and use that stable logged-out URL in the Lablab submission.

**Architecture:** The existing `buildAlpacaPublicProjection()` remains the only allowlist and rendering source. After each finite local pass, a small publisher upserts one redacted JSON snapshot to Supabase; Railway reads that single row when local state is absent. Trading stays on the Mac mini and the public surface remains GET-only.

**Tech Stack:** Node.js standard library, Python standard library subprocess, Supabase REST, existing Railway Life Manager server.

## Global Constraints

- Paper trading only; do not add a live-capital path.
- Do not expose Alpaca credentials, account ID, raw prompts, raw errors, or broker identifiers.
- Do not add registration, order placement, another broker client, scheduler, or dependency.
- The existing projection must drive local publishing and public rendering.
- One row only: `id = alpaca-hackathon`.

---

### Task 1: Durable redacted snapshot boundary

**Files:**
- Create: `apps/life-manager/migrations/20260904_alpaca_public_snapshot.sql`
- Modify: `apps/life-manager/lib/alpaca-public.js`
- Test: `apps/life-manager/lib/alpaca-public.test.js`

**Interfaces:**
- Produces: `publishAlpacaPublicProjection(options): Promise<object>` and `fetchAlpacaPublicProjection(options): Promise<object>`.
- Storage: `lm_alpaca_public_snapshot(id text primary key, projection jsonb, observed_at timestamptz, updated_at timestamptz)` with service-role-only access.

- [ ] Write focused tests proving the publisher sends only the existing allowlisted projection and the reader returns that projection.
- [ ] Run `node --test apps/life-manager/lib/alpaca-public.test.js`; expect the new tests to fail before implementation.
- [ ] Add the minimal publisher/reader functions and SQL table with RLS enabled and no anon/authenticated grants.
- [ ] Re-run the focused test; expect PASS.

### Task 2: Local wake publication and cloud readback

**Files:**
- Create: `apps/life-manager/scripts/publish-alpaca-public.js`
- Modify: `skills/alpaca-investment/run.py`
- Modify: `apps/life-manager/server.js`
- Test: `apps/life-manager/lib/alpaca-public.test.js`

**Interfaces:**
- Local pass invokes the publisher after state files and Telegram receipt are persisted; publication failure does not authorize a broker retry.
- `GET /api/life-manager/alpaca/public` reads local state when present and otherwise reads the Supabase snapshot.

- [ ] Add one focused invocation test covering the post-pass publisher call and cloud fallback.
- [ ] Run the focused Node and Python Alpaca tests; expect RED for the missing wiring.
- [ ] Add the publisher entrypoint, one bounded `subprocess.run`, and asynchronous GET fallback.
- [ ] Run the focused tests and `git diff --check`; expect PASS.

### Task 3: Production publish, deploy, and submission URL

**Files:**
- Modify: no source files beyond Tasks 1–2.

**Interfaces:**
- Public URL: `https://life-call-production.up.railway.app/alpaca`.

- [ ] Apply the additive SQL migration and verify table, RLS, grants, primary key, and single-row upsert.
- [ ] Publish the current Mac projection and verify the stored JSON contains no account ID, credentials, raw prompts, raw errors, or broker IDs.
- [ ] Commit and push the task branch, merge it to `main`, deploy the exact main SHA to Railway, and verify `/health` reports that SHA.
- [ ] Fetch `/alpaca` and its JSON API logged out; verify HTTP 200, paper-only copy, current equity/P&L, latest decision, and no mutation controls.
- [ ] Update the Lablab Demo URL to the stable Railway `/alpaca` URL and read the public submission back logged out.
