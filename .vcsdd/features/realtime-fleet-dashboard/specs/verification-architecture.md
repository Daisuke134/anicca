# Verification Architecture — realtime-fleet-dashboard — ITERATION 2

## Purity boundary (pure core vs effectful shell; unchanged-sound, now fully pinned)

### PURE module `dashboard-core` (TS, NO fetch/supabase/fs imports) — the heart, 100% unit-tested
- `deriveStatus(row, nowSec) -> 'alive'|'stale'|'dead'` (REQ-4). `now` is a PARAMETER (no Date.now) → deterministic.
- `isSelfFundedEconomic(row, nowSec) -> boolean` (REQ-5) — uses deriveStatus≠dead && revenue_mo/30 ≥ burn_day.
- `computeTotals(rows, nowSec) -> {assets,revenue30d,net,counts:{alive,stale,dead},self_funded_pct,frontier_pct}` (REQ-6).
- `normalizeLogKind(kind) -> 'earn'|'claim'|'blocked'|'done'|'ping'|'spawn'|'info'` (unknown ⇒ 'info').
- `toCardModel(row, nowSec) -> {FULL fixed shape per REQ-8, no "..."}` incl. `logs` (newest-first, ≤20).

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
| empty fleet `computeTotals([])` | `{assets:0,revenue30d:0,net:0,counts:{0,0,0},self_funded_pct:0,frontier_pct:0}` |
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
| Unit | dashboard-core (5 fns) + every edge above | node:test, fixtures, RED→GREEN |
| Integration | signed post w/ 3 fields → 202 + persisted; old post → 202 + defaults; unsigned/anon → rejected | against telemetry receiver (test wallet, id-prefixed rows, snapshot-diff cleanup) |
| E2E (mine, post-adversary) | unique sentinel in ledger → poster cycle → sentinel + 3 badges in /dashboard DOM ≤150s | real browser screenshot + DOM assert |

## Done (4-D convergence)
spec ✓ + tests ✓ (pure core RED→GREEN + integration) + impl ✓ (poster fields + receiver + page rewrite) + verification ✓
(adversary PASS on disk + MY browser E2E: live this-instance row w/ unique sentinel + badges, NOT the fallback). NO-MOCK E2E required.
