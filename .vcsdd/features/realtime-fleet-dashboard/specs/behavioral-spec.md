# Behavioral Spec — realtime-fleet-dashboard (lean, typescript)

## Goal (provable)
Revive `/dashboard` as a REAL-TIME fleet board sourced from ONE registry (Supabase), showing every Anicca
instance's **assets + revenue + live logs**, with the **human-funded vs self-funded** distinction, **environment
(local/cloud)**, **model**, and **brain** as first-class fields. Kill the hardcoded-fallback + dead static
`dashboard.json` pipeline. THIS instance (Claude/human/local) appears as a real registered row.

## Context (grounded in existing code, 2026-06-29)
- `app/dashboard/page.tsx` reads static `public/dashboard.json`; `data.lineage` empty ⇒ 3 HARDCODED instances. Frozen since 2026-06-01.
- `netlify/functions/dashboard-sync.js` reads Supabase `GET /rest/v1/instances?select=*` → `aggregate()` → JSON (15s cache). Page never calls it.
- Existing `instances` fields (from `_lib/telemetry-aggregate.js`): `net_worth_usd, revenue_mo_usd, burn_day_usd, model_tier, status`. `aggregate()` already derives self-funded by ECONOMIC test (`revenue_mo/30 >= burn_day`), not a model proxy. We KEEP that test.
- Supabase creds: Netlify env (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) + `apps/api/.env` (real values, gitignored). Anon key for client reads.

## Scope
IN: canonical registry schema (`instances` + `instance_logs`); a registry CLIENT (register/heartbeat/log) usable by any instance (node, no human); the `/dashboard` page rewritten to render LIVE from the registry with realtime updates + funding/env/model badges + assets/revenue/net + per-instance logs + global feed + totals; register THIS instance.
OUT (separate features): resurrection (#17 — only the STALE derivation is in scope here), day/night engine (#15), bot2bot semantics beyond logging the 4 kinds (#16), the earn skills themselves, on-chain basescan cross-check (optional, stub allowed).

## Canonical schema (the contract)
`instances` (one row per body, PK `id`):
| col | type | notes |
|---|---|---|
| id | text PK | e.g. `anicca-001-claude` |
| name | text | harness/display |
| funding | text | `'human'` \| `'self'` (declared) |
| env | text | `'local'` \| `'cloud'` |
| brain | text | `'claude-p'` \| `'proxy'` |
| model | text | e.g. `claude-sonnet-4-6` |
| model_tier | text | `'frontier'` \| `'small'` \| `'free'` |
| runtime | text | host label |
| wallet | text null | Base address (PUBLIC only) |
| wallet_usdc | numeric | assets, USDC |
| revenue_mo_usd | numeric | realised 30d revenue (external, INV-7) |
| burn_day_usd | numeric | daily spend |
| status | text | `'alive'` \| `'dead'` (raw, as written) |
| current_activity | text null | latest one-line status |
| last_heartbeat | timestamptz | for staleness |
| updated_at | timestamptz | |

`instance_logs` (append-only feed): `id bigserial PK, instance_id text FK, ts timestamptz, kind text ('earn'|'claim'|'blocked'|'done'|'ping'|'spawn'|'info'), msg text, tx_hash text null`.

## Requirements (EARS)
- **REQ-1 (register):** WHEN an instance boots, the client SHALL upsert its `instances` row with id, name, funding, env, brain, model, model_tier, runtime, wallet, status='alive', last_heartbeat=now.
- **REQ-2 (heartbeat):** WHILE alive, at interval ≤30s the client SHALL update {last_heartbeat, wallet_usdc, revenue_mo_usd, burn_day_usd, current_activity, updated_at}.
- **REQ-3 (log):** WHEN a tracked action occurs, the client SHALL insert an `instance_logs` row {instance_id, ts, kind∈enum, msg, tx_hash?}; unknown kind ⇒ coerced to 'info'.
- **REQ-4 (staleness, PURE):** GIVEN a row and `now`, the derived display status SHALL be `'stale'` IF `status!=='dead' AND now-last_heartbeat>90_000ms`; `'dead'` IF status==='dead'; else `'alive'`.
- **REQ-5 (self-funded test, PURE):** the self-funded ECONOMIC flag SHALL be `status!=='dead' && revenue_mo_usd/30 >= burn_day_usd` (kept from existing aggregate). NOTE: `funding` column = declared origin; this flag = economic reality. Both shown.
- **REQ-6 (totals, PURE):** the page SHALL show totals: Σ wallet_usdc (assets), Σ revenue_mo_usd (revenue30d), net = Σrevenue_mo − Σ(burn_day·30), counts {alive, stale, dead}, self_funded_pct, frontier_pct.
- **REQ-7 (render live):** WHEN `/dashboard` loads, the page SHALL render rows from the LIVE registry (not the hardcoded fallback, not the stale static file). IF the registry is unreachable, THEN it SHALL show an explicit "registry unavailable" state (NOT silently fall back to fake rows).
- **REQ-8 (badges):** each instance card SHALL display funding (human/self) + env (local/cloud) + model + brain as distinct labels, plus wallet→assets (linked to basescan), revenue/burn/net, derived status dot, and its most-recent N logs.
- **REQ-9 (realtime):** WHILE `/dashboard` is open, new/changed `instances` rows and new `instance_logs` SHALL appear within ~5s with no manual refresh (Supabase Realtime; IF unavailable, polling ≤15s is an acceptable fallback and MUST be labelled as the mechanism in code).
- **REQ-10 (this instance):** THIS body SHALL be a real registered row: id `anicca-001-claude`, funding `human`, env `local`, brain `claude-p`, model `claude-sonnet-4-6`, wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5`, wallet_usdc from chain, status alive.
- **REQ-11 (no human loop):** register/heartbeat/log SHALL run with env-configured creds only — zero human action.
- **REQ-12 (key safety):** the client SHALL NEVER read/write a private key or service-role key into a row or log; only the PUBLIC wallet address. Writes use a least-privilege path (anon+RLS insert/upsert OR a scoped server endpoint); the service-role key stays server-side only.

## Acceptance / E2E
- Unit (pure, no network): REQ-4 staleness, REQ-5 self-funded, REQ-6 totals — table-driven incl. edge cases (no heartbeat, burn=0, empty fleet, exactly-90s boundary, dead).
- Integration: register→heartbeat→log against a Supabase test path returns the row; staleness flips after >90s.
- E2E (MY browser, after adversary PASS): open `/dashboard`, see `anicca-001-claude` ALIVE with funding/env/model badges, assets=on-chain USDC, and a live log line appearing within 5s of an inserted log — NOT the hardcoded fallback.
