# Adversary Verdict — realtime-fleet-dashboard — Phase 3 Implementation Review (iteration 2)

- feature: realtime-fleet-dashboard
- reviewType: implementation (Phase 3)
- iteration: 2
- timestamp: 2026-06-29
- context: fresh, disk-only. Read the iteration-1 verdict + spec (now incl. PHASE 3 RULINGS) +
  fleet-fields.test.js + dashboard-core.mjs + dashboard-core.test.mjs + page.tsx + telemetry-schema.js +
  telemetry-verify.js + telemetry-store.js + store.test.js + handler-telemetry.test.js + verify.test.js +
  telemetry-poster.mjs + the committed DDL (supabase/instances.sql) + the new migration
  (_migrations/2026-06-29-instances-fleet-fields.sql).

## OVERALL VERDICT: FAIL

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | FAIL |
| 2. Edge Case Coverage | PASS |
| 3. Implementation Correctness | PASS |
| 4. Structural Integrity | PASS |
| 5. Verification Readiness | FAIL |

overallVerdict = FAIL (any FAIL ⇒ FAIL). NOT ready to converge. One NEW CRITICAL.

---

## Iteration-1 finding resolution

### FIND-001 (CRITICAL, key-safety test) — RESOLVED (with caveat → see FIND-009)
`fleet-fields.test.js:65-75` now asserts all three mandated properties: the private key is not a
substring (with and without `0x`, lines 70-71), the `SUPABASE_SERVICE_ROLE_KEY` value is not a
substring (line 72, real env var set at line 68), AND every top-level key ∈ a fixed `ALLOWED`
allowlist (lines 73-74 against the set at 16-20). REQ-12's literal "a test SHALL assert (a)…(b)…" is
met. CAVEAT: the test asserts over a hand-copied replica `posterMsg()` (lines 21-32), not the real
poster artifact — see NEW FIND-009.

### FIND-002 (HIGH, enum branch + persist + log round-trip) — STILL-OPEN (escalated)
- Enum branch: RESOLVED. `fleet-fields.test.js:46-54` exercises the schema enum reject path
  (funding=`zzz`, env=`mars`, brain=`gpt-p` ⇒ `ok:false`) AND the backward-compatible absent case
  (⇒ `ok:true`). The dead branch at `telemetry-schema.js:17-19` is now live-tested.
- 3-field carry-through verify: RESOLVED. `fleet-fields.test.js:35-43` asserts
  `r.payload.{funding,env,brain}`.
- PERSIST through the handler: STILL-OPEN. No test asserts `upserts[0].funding === 'human'`. The
  integration suite `handler-telemetry.test.js:26` still signs `canonicalMessage(...)`, the 11-field
  serializer (`telemetry-verify.js:7-13`) that OMITS funding/env/brain — so the receiver→store
  persistence of the 3 fields is asserted by NO test.
- `log` as a persisted COLUMN (REQ-13): STILL-OPEN and now CRITICAL — see FIND-008.

### FIND-003 (HIGH, real poster msg signed+verified) — RESOLVED
`fleet-fields.test.js:34-43` signs the real 19-key poster-shaped message (keys at 21-32 match
`telemetry-poster.mjs:141-154` exactly) and `verifyTelemetry` returns `ok:true`. The actual posted
shape (not the dormant `canonicalMessage`) is now proven to verify.

### FIND-004 (MEDIUM, REQ-9 axis ruling) — RESOLVED (by spec ruling)
`behavioral-spec.md:95-98` rules ranking-by-net-worth coexists with first-class
funding/env/brain/model badges. `page.tsx:135-140` renders all four as badges on every card. Ruling
is coherent; impl matches.

### FIND-005 (MEDIUM, brain semantics) — RESOLVED (by spec ruling)
`behavioral-spec.md:99-103` defines `claude-p` = Claude subscription, `proxy` = self-pay/free compute
(incl. free GLM), and rules that a `free/glm-4.7` body MUST declare `brain='proxy'`. Builder re-posted
the live row with `brain=proxy`, matching `model_live`. Ruling is internally coherent and REQ-11's
`claude-p` example is scoped to a body actually running `claude -p`. RESIDUAL (informational): the
brain↔model_live match is operator-declared only — `telemetry-poster.mjs:25` still defaults
`claude-p` and nothing in code reconciles `BRAIN` against `lastModel()`/`FREE_RE` (:108-113), so the
mismatch the ruling describes remains possible for any mis-configured instance. The ruling explicitly
accepts brain as a declared label, so this is acceptable, not a blocker.

### FIND-006 (LOW, null-row guard) — RESOLVED at impl (minor residual)
`dashboard-core.mjs:36` adds the guard (`row = {}` when null/undefined/non-object). RESIDUAL: no
regression test — `dashboard-core.test.mjs` is unchanged at 22 tests and has no `toCardModel(null)`
case (the builder's "22/22" confirms none was added). Guard present; coverage gap is LOW.

### FIND-007 (LOW/INFO, 8-of-20 logs) — RESOLVED (accepted display choice)
`page.tsx:164` still `c.logs.slice(0,8)`; the model carries ≤20 (`dashboard-core.mjs:41`). Accepted as
a display choice; newest-first ordering (:40) keeps a fresh sentinel at the top for the E2E.

---

## Dimension 1 — Spec Fidelity: FAIL
REQ-13 ("do NOT assume columns") is UNMET. See FIND-008: the committed DDL has no `log` column and the
sole migration adds only funding/env/brain — not `log`, `breakdown`, `daily_revenue_usd`,
`monthly_revenue_usd`, or `revenue_by_source`, all of which the poster sends
(`telemetry-poster.mjs:147-153`). REQ-13 explicitly mandated the migration add the `log` column "if
absent" and ship a round-trip integration test that `log` persists; neither exists. The FIND-004/005
rulings ARE satisfied; the pure-core requirements (REQ-4/5/6/8) remain correctly implemented.

## Dimension 2 — Edge Case Coverage: PASS
`dashboard-core.test.mjs` covers missing/null/NaN ts (22-24), exactly-300 alive vs 301 stale (20-21),
dead override (19), critical preserved + beaten-by-stale (25-26), empty fleet zero (39), null
funding/env/brain ⇒ unknown (59-62), log newest-first/cap-20/kind-normalize (63-70), burn0/rev0 ⇒ true
(32). New schema-enum reject + absent edges added (`fleet-fields.test.js:46-54`). The untested
null-row guard is LOW (FIND-006/010), not enough to fail this dimension.

## Dimension 3 — Implementation Correctness: PASS
Pure logic is sound: `deriveStatus` ordering (`dashboard-core.mjs:9-15`), economic self-funded /30
(:18-21), `netUsd` monthly basis (:58), null-row guard (:36). `verifyTelemetry` recovers the signer
from verbatim bytes and binds signer→id (`telemetry-verify.js:26-28`). The migration's incompleteness
is recorded under Spec Fidelity / Verification Readiness rather than here. No new logic defect found.

## Dimension 4 — Structural Integrity: PASS
`dashboard-core.mjs` keeps the purity boundary (no fetch/fs/supabase/Date.now; `nowSec` is a
parameter throughout). `page.tsx:5,91,128` consumes the pure core rather than reimplementing display
logic. `aggregate()` is reused for $ totals (REQ-6), not forked.

## Dimension 5 — Verification Readiness: FAIL
- REQ-13's mandated round-trip integration test (that `log` is a persisted column) does NOT exist
  anywhere (`store.test.js` and `handler-telemetry.test.js` never include `log`). FIND-008.
- No integration test asserts the 3 new fields persist through the handler (`handler-telemetry.test.js`
  still uses the 11-field `canonicalMessage`, omitting them). FIND-002 persist sub-point.
- The key-safety guarantee (FIND-001) is verified only over a replica, not the real poster
  serialization. FIND-009.

---

## NEW FINDINGS

### FIND-008 — spec_gap / verification_tool_mismatch — CRITICAL
The feature's central deliverable is the per-instance LIVE log on every card (Goal lines 4-7; REQ-8).
Persisting it requires a `log` column. The committed table `supabase/instances.sql:1-9` defines NO
`log` column (only id/ts/host/geo/model_live/model_tier/net_worth_usd/revenue_mo_usd/burn_day_usd/
runway_days/status/updated_at). The only migration
`_migrations/2026-06-29-instances-fleet-fields.sql:3-5` adds funding/env/brain and merely COMMENTS
"`log` (jsonb) already exists" (line 2) with NO committed DDL and NO test to substantiate it. The
poster also posts `breakdown`, `daily_revenue_usd`, `monthly_revenue_usd`, `revenue_by_source`
(`telemetry-poster.mjs:147-153`) — none of which have a column in committed DDL either. By the spec's
OWN logic (`behavioral-spec.md:86`: "Without the migration, `upsertInstance` silently drops the keys
and REQ-8 logs … cannot render"), the per-instance log cannot render from the committed schema.
REQ-13 (`behavioral-spec.md:82-86`) explicitly required (a) the migration add the `log` column if
absent and (b) a round-trip integration test proving `log` persists as a column — BOTH absent. The
live DB accepting these posts (builder's report) only proves out-of-band schema drift (live DB ⊋
committed DDL), which is exactly what REQ-13 ("do NOT assume columns") forbids and is not reproducible.
- evidence: supabase/instances.sql:1-9 (no log/breakdown/revenue cols);
  _migrations/2026-06-29-instances-fleet-fields.sql:2-5 (adds only funding/env/brain, comments log);
  telemetry-poster.mjs:147-153 (posts log/breakdown/daily/monthly/by_source);
  behavioral-spec.md:82-86 (REQ-13) and :108-109 (Acceptance integration test).
- routeToPhase: 2b (extend the migration to ADD COLUMN IF NOT EXISTS log jsonb, breakdown jsonb,
  daily_revenue_usd / monthly_revenue_usd double precision, revenue_by_source jsonb; add the mandated
  store/handler round-trip test that log + the 3 fields persist).

### FIND-009 — verification_tool_mismatch — MEDIUM
The FIND-001 key-safety test asserts over `posterMsg()` (`fleet-fields.test.js:21-32`), a literal
re-declaration of the message shape, NOT the real artifact: `telemetry-poster.mjs:141-154` builds the
signed `msg` inline and exports nothing, so the test cannot regression-catch a future leak (e.g. the
poster reads the raw private key at `telemetry-poster.mjs:15`) or an added key in the ACTUAL poster.
The guarantee is proven for the copy, not the system under test.
- evidence: fleet-fields.test.js:21-32,66-74; telemetry-poster.mjs:15,141-154 (no exported builder).
- routeToPhase: 2b (extract the poster's msg-builder into a pure exported fn and key-safety-test THAT).

### FIND-010 — test_coverage — LOW
The null-row guard (FIND-006, `dashboard-core.mjs:36`) and the 3-field handler-level persistence
(FIND-002) have no test. `dashboard-core.test.mjs` (22 tests) has no `toCardModel(null)` case;
`handler-telemetry.test.js` omits funding/env/brain.
- evidence: dashboard-core.test.mjs:1-72 (no null-row test); handler-telemetry.test.js:24-37.
- routeToPhase: 2b.

---

## Convergence signals
- findingCount this iteration: 3 new (1 critical, 1 medium, 1 low) + 1 still-open (FIND-002 persist/log).
- resolved: FIND-001 (caveat), FIND-003, FIND-004, FIND-005, FIND-006 (impl), FIND-007.
- must-fix to converge: FIND-008 (CRITICAL) + the FIND-002 persist/log-column integration test.
- 4-D convergence: spec ✗ (REQ-13), test ✗ (no persist/log round-trip test), impl ~ (pure core ✓, DDL
  incomplete), verification ✗. NOT converged.
- ready to converge: NO.
