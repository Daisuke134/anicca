# Verification Architecture — realtime-fleet-dashboard — ITERATION 3

NOTE (M1): `toCardModel.netUsd` basis = MONTHLY: `netUsd = revenue_mo_usd − burn_day_usd*30` (same as REQ-6 net; daily figures are display-only, not used in net).

## Purity boundary (pure core vs effectful shell; unchanged-sound, now fully pinned)

### PURE module `dashboard-core` (TS, NO fetch/supabase/fs imports) — the heart, 100% unit-tested
- `deriveStatus(row, nowSec) -> 'alive'|'stale'|'critical'|'dead'` (REQ-4). `now` is a PARAMETER (no Date.now). 'critical' preserved.
- `isSelfFundedEconomic(row, nowSec) -> boolean` (REQ-5) — deriveStatus≠dead && revenue_mo/30 ≥ burn_day. Signature `(row,nowSec)`.
- `countByStatus(rows, nowSec) -> {alive,stale,critical,dead}` (REQ-6). NO `computeTotals`: the $ totals
  (total_net_worth_usd/earned_mo_usd/self_funded_pct/frontier_pct) are REUSED from server `aggregate()` — not re-derived in TS (resolves N2).
- `normalizeLogKind(kind) -> 'earn'|'claim'|'blocked'|'done'|'ping'|'spawn'|'info'` (unknown ⇒ 'info').
- `toCardModel(row, nowSec) -> {FULL fixed shape per REQ-8, no "..."}` incl. `logs` (newest-first, ≤20); funding/env/brain null ⇒ 'unknown' (REQ-14).

### EFFECTFUL shell (thin; integration/E2E)
- poster extension (`~/anicca/runtime/dashboard/telemetry-poster.mjs`): add 3 env-read fields INTO the signed msg (REQ-1).
- receiver (`~/anicca-project/.../telemetry-schema.js` + `telemetry-store.js`): accept/persist 3 fields, backward-compatible (REQ-2); auth path UNCHANGED (REQ-3).
- page data source (`app/dashboard/page.tsx`): fetch `dashboard-sync` live + client poll ≤120s (REQ-7/10); behind one interface so the page renders from a fake source in test.

## Edges (enumerated, internally consistent with the formulas — fixes F5/F6/F7)
| edge | defined result |
|---|---|
| `last ts` missing / null / NaN | `deriveStatus ⇒ 'stale'` (NOT alive) |
| `nowSec - ts` exactly 300 | `'alive'` (strict `> 300` ⇒ stale) |
| `nowSec - ts` 301 | `'stale'` |
| `status==='dead'` | `'dead'` (overrides staleness) |
| empty fleet `countByStatus([])` | `{alive:0,stale:0,critical:0,dead:0}` ($ totals come from server `aggregate`, not TS) |
| `burn_day_usd===0` | NOT a div hazard (REQ-5 divides by const 30, REQ-6 multiplies burn); row simply economic-self-funded if revenue_mo≥0 |
| negative net (burn>revenue) | net < 0 rendered as-is (honest) |
| NO `burn_day` division anywhere | confirmed (phantom F5 edge removed) |

## Key-safety obligation (REQ-12; fixes F15)
Test asserts, for the posted `message` string: (a) `wallet.privateKey` substring NOT present; (b)
`process.env.SUPABASE_SERVICE_ROLE_KEY` value substring NOT present; (c) `JSON.parse(message)` top-level key-set ⊆ the
documented allowlist {id,ts,host,geo,model_live,model_tier,funding,env,brain,net_worth_usd,daily_revenue_usd,
monthly_revenue_usd,revenue_by_source,revenue_mo_usd,burn_day_usd,runway_days,status,breakdown,log}. No 64-hex regex over
`log[]` (there is no tx_hash field in this payload).

## Test plan
| Layer | What | How |
|---|---|---|
| Unit | dashboard-core (deriveStatus incl critical/null-ts/300-boundary, isSelfFundedEconomic, countByStatus incl empty, normalizeLogKind, toCardModel full-shape+log order/cap+unknown defaults) | node:test, fixtures, RED→GREEN |
| Integration | (a) signed post w/ 3 fields → 202 + columns persisted + returned via select=* (proves REQ-13 migration applied + `log` is a column); (b) old post (no fields) → 202, renders 'unknown'; (c) **post signed by a DIFFERENT key than `id` → 401 `signer_mismatch`** (the akash-fix regression, N5); (d) replay (ts≤lastTs) → rejected | against telemetry receiver (test wallet, id-prefixed rows, snapshot-diff cleanup) |
| Key-safety | message key-set ⊆ allowlist; wallet privkey + SERVICE_ROLE_KEY never substring of `message` | unit over the built payload |
| E2E (mine, post-adversary) | unique sentinel in ledger → poster cycle → sentinel + 3 badges (human/local/claude-p) in /dashboard DOM ≤150s, NOT fallback | real browser screenshot + DOM assert |

## Done (4-D convergence)
spec ✓ + tests ✓ (pure core RED→GREEN + integration) + impl ✓ (poster fields + receiver + page rewrite) + verification ✓
(adversary PASS on disk + MY browser E2E: live this-instance row w/ unique sentinel + badges, NOT the fallback). NO-MOCK E2E required.
