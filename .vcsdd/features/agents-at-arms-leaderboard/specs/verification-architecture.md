# Verification Architecture — agents-at-arms-leaderboard (VCSDD Phase 1b)

Companion to `behavioral-spec.md` (v5, spec-gate PASS round 5). Defines HOW each requirement R1–R12
is proven and the purity boundary. Adversary spec-review verdict: `reviews/sprint-1/output/spec-verdict.md` (PASS).

## Purity boundary (pure core vs. impure shell)
- **PURE (deterministic, no I/O — unit-testable in isolation):**
  - `aggregate(rows)` — existing pure fn; extended to carry additive fields + `stale/*_src` and rank by
    verified earnings (R1,R2,R4,R5).
  - `leaderboard-constants.js` — `OUR_INSTANCE_IDS`, `SEED_ADDRESSES`, `excludeSet(row)` (pure).
  - `telemetry-schema.validate` — pure validator, extended with typed additive fields (R9).
  - `telemetry-verify.canonicalMessage` — pure serialization, extended (R10).
  - the ranking/stale/exclusion logic inside `enrichOnChain` that is independent of the reader.
- **IMPURE (I/O — isolated behind an injected `reader`):**
  - `enrichOnChain(rows, reader)` — the ONLY chain caller. `reader` (Base RPC + USDC logs + price feed)
    is injected so tests use a deterministic mock (R3). Failure = `reader` method throws ⇒ `unverified`.
  - the producers (netlify `dashboard-sync.js` handler; the Dais render writing `public/dashboard.json`)
    — must call `enrichOnChain` before `aggregate` (R11,R12).
- **UI:** `EmpireDashboard.tsx` render is a pure function of `leaderboard` data (component test) + a
  browser E2E over the served `/dashboard.json`.

## Proof table (RED tests to author in Phase 2a)

| Req | Kind | Test (fails until GREEN) |
|---|---|---|
| R1 | unit | `aggregate` output keeps existing keys; leaderboard elements carry additive fields + `stale/*_src` |
| R2 | unit | verified-first by `revenue_mo_usd` desc; tie by `net_worth_usd` (both chain) else `id` asc; unverified appended by `id` asc |
| R3 | unit (mock reader) | net_worth = usdc/1e6 + wei/1e18*price (exact); **self/seed-only inflow ⇒ revenue 0 ⇒ not #1** (anti-buy); reader throw ⇒ `unverified` flagged |
| R4 | unit | totals sum only `*_src==='chain'`; all-unverified ⇒ `undefined` (not 0); never NaN |
| R5 | unit | old `ts` ⇒ `stale:true`; `status` unchanged; `dead` visible |
| R6 | component + browser E2E | rows render in order w/ all fields incl `earn_src`; CloakBrowser shot of live `/dashboard` |
| R7 | component + browser E2E | `#agent-hackathon` ⇒ only tagged; `Ours` ⇒ only `OUR_INSTANCE_IDS` untagged |
| R8 | component | absent today ⇒ `—`; all-unverified headline ⇒ `—`; empty filter ⇒ empty-state node |
| R9 | unit | existing fixtures `ok:true`; non-array `tags`⇒false; `revenue_today>revenue_mo`⇒false; negative `revenue_by_source` value⇒false |
| R10 | unit | `canonicalMessage` includes additive fields; signed msg w/ `tags` ⇒ `signer==id`; tampered ⇒ `signer_mismatch` |
| R11 | integration | Dais render produces `public/dashboard.json` containing `leaderboard`; UI E2E reads THAT file |
| R12 | unit/integration | netlify `dashboard-sync` handler w/ mock reader ⇒ its `leaderboard` reflects ENRICHED (self-transfer excluded); cannot serve raw self-reported |

## Test file layout (Phase 2a)
- `apps/landing/netlify/functions/_lib/__tests__/enrich.test.js` — R3, R2(ranking helper), R4, R5.
- extend `apps/landing/netlify/functions/_lib/__tests__/aggregate.test.js` — R1, R2, R4.
- `apps/landing/netlify/functions/_lib/__tests__/telemetry-schema.additive.test.js` — R9.
- `apps/landing/netlify/functions/_lib/__tests__/telemetry-verify.additive.test.js` — R10.
- extend `handler-telemetry.test.js` / a `dashboard-sync.test.js` — R12.
- `apps/landing/components/site/__tests__/EmpireDashboard.leaderboard.test.tsx` — R6,R7,R8.
- browser E2E (my own, CloakBrowser) over served `/dashboard.json` — R6,R7,R11.

## Definition of done = 4-D convergence
spec ✓ (gate PASS) · tests ✓ (R1–R12 green) · impl ✓ · verification ✓ (fresh-context adversary PASS on
impl + my CloakBrowser browser E2E green).
