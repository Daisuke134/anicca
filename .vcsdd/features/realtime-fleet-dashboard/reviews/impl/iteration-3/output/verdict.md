# Adversary Verdict — realtime-fleet-dashboard — Phase 3 Implementation Review (iteration 3, lean final)

- feature: realtime-fleet-dashboard
- reviewType: implementation (Phase 3)
- iteration: 3
- timestamp: 2026-06-29
- context: fresh, disk-only. Read the iteration-2 verdict + behavioral-spec.md (incl. REQ-13/PHASE 3 RULINGS)
  + supabase/instances.sql + fleet-fields.test.js + dashboard-core.test.mjs + telemetry-msg.mjs (NEW pure
  builder) + telemetry-poster.mjs + telemetry-msg.test.mjs (NEW) + telemetry-store.js.
- NOTE: I cannot open a browser. The live-DOM badge render + the manual a3cdd4 live round-trip are
  BUILDER-REPORTED; confirming them is the main agent's separate browser/E2E gate, not this disk review.

## OVERALL VERDICT: PASS

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | PASS |
| 2. Edge Case Coverage | PASS |
| 3. Implementation Correctness | PASS |
| 4. Structural Integrity | PASS |
| 5. Verification Readiness | PASS |

overallVerdict = PASS. No open CRITICAL/MAJOR. One LOW reporting discrepancy (non-blocking in lean).

---

## Iteration-2 finding resolution

### FIND-008 (CRITICAL — DDL drift + missing log/revenue columns + no persist test) — RESOLVED
- DDL no longer drifts. `supabase/instances.sql:5-23` (CREATE) now declares EVERY one of the 19 posted
  keys as a column: funding/env/brain (`:14-16`), daily_revenue_usd/monthly_revenue_usd/revenue_by_source
  (`:18-19`), breakdown (`:20`), and `log jsonb` (`:21`). Idempotent convergence ALTERs for already-created
  DBs at `:25-32` add all eight (funding/env/brain/daily/monthly/by_source/breakdown/log) `IF NOT EXISTS`.
  Cross-checked against the poster's exact send set (`telemetry-poster.mjs:146-154`): all 19 keys + updated_at
  have a column → no silent key-drop, which is precisely what REQ-13 (`behavioral-spec.md:82-86`) demanded.
- Store persist-path proven. `fleet-fields.test.js:81-92` injects a fake fetch (`f: fakeFetch`) into
  `upsertInstance(payload, { url, key, f })`, captures the POST body, and asserts `on_conflict=id`
  (`:86`) plus `body.funding==='human'`, `body.env==='local'`, `body.brain==='proxy'` (`:87-89`),
  `Array.isArray(body.log) && length===1` (`:90`), and `body.id` (`:91`). This exercises the REAL
  `telemetry-store.upsertInstance` (`telemetry-store.js:15-22`, which spreads `...p` into the body), not a
  stub. Combined with instances.sql declaring those columns + the builder's manual live a3cdd4 round-trip,
  the persist path is substantiated. RESOLVED.

### FIND-009 (MEDIUM — key-safety/verify tested over a replica, not the real artifact) — RESOLVED
- The poster no longer inlines its message shape: `telemetry-poster.mjs:13` imports `buildTelemetryMsg`
  from `./telemetry-msg.mjs` and `:145-155` builds the signed `msg` via that function, then signs the
  returned bytes (`:156`). The shape is now a single pure, side-effect-free export (`telemetry-msg.mjs:14-37`).
- The real exported builder is tested directly: `telemetry-msg.test.mjs` imports `buildTelemetryMsg, MSG_KEYS`
  (`:6`) and asserts (a) shape/field carry-through + id lowercasing + revenue mirror (`:20-26`), and (b)
  KEY-SAFETY on the actual artifact — `Object.keys(obj).sort()` is EXACTLY `MSG_KEYS` (`:30`), and a private
  key / stray `secret` passed in as extra inputs NEVER reach the output bytes (`:32-35`). Because
  `buildTelemetryMsg` constructs a fixed-key object (does NOT spread `...p`), extra/secret-bearing keys are
  structurally dropped — the guarantee is now proven on the system under test, not a copy. RESOLVED.

### FIND-010 (LOW — null-row guard untested) — RESOLVED
- `dashboard-core.test.mjs:72-78` adds the null-row case: for `[null, undefined, 42, 'x']`, `toCardModel`
  returns safe defaults (funding/env/brain `'unknown'`, `logs:[]`, `assetsUsd:0`, `statusDisplay:'stale'`)
  with no throw. RESOLVED.

---

## Dimension notes

- **1 Spec Fidelity (PASS):** REQ-13's two mandates (migration adds `log`/columns if absent; persist
  round-trip proven) are now both met (instances.sql:21,25-32; fleet-fields.test.js:81-92). REQ-1/2/3
  covered (telemetry-msg.mjs fixed key-set inside the signed bytes; fleet-fields.test.js:36-55 enum reject +
  backward-compatible absent case). FIND-004/005 rulings unchanged and honoured.
- **2 Edge Case Coverage (PASS):** missing/null/NaN ts + exactly-300 boundary vs 301 (dashboard-core.test.mjs:20-24),
  empty fleet zero (`:39`), dead/critical ordering (`:19,25-26`), burn0/rev0⇒true (`:32`), log cap-20/newest-first
  (`:63-70`), null funding⇒unknown (`:59-62`), null-row (`:72-78`), schema enum reject + absent (fleet-fields.test.js:46-55).
- **3 Implementation Correctness (PASS):** pure core ordering/economic test sound; `upsertInstance`
  forwards the full payload and forces lowercase id + updated_at (telemetry-store.js:19); `buildTelemetryMsg`
  mirrors monthly→`revenue_mo_usd` for back-compat (telemetry-msg.mjs:29) and applies status/runway/geo
  defaults (`:19,31,32`). No new logic defect found.
- **4 Structural Integrity (PASS):** message shape extracted to one pure module consumed by the poster
  (no inline duplication on the poster side); purity boundary intact (telemetry-msg.mjs has no fs/fetch/
  Date). RESIDUAL (informational, not a finding): the receiver-side `fleet-fields.test.js:22-32` still keeps
  a hand-copied `posterMsg()` replica because it lives in a different repo and cannot import the poster's
  `.mjs`; its 19-key set was cross-checked against MSG_KEYS and matches, and the real builder is now covered
  by telemetry-msg.test.mjs, so the FIND-009 gap is closed.
- **5 Verification Readiness (PASS):** persist-path test (real store, injectable fetch), key-safety on the
  real builder, null-row regression test, and committed DDL all present.

---

## NEW FINDINGS

### FIND-011 — verification accuracy / reporting discrepancy — LOW (non-blocking in lean)
The builder reported "fleet-fields (6 incl upsertInstance persist)". The file on disk contains exactly 5
`node:test` blocks: lines 36, 47, 58, 67, 81 of `fleet-fields.test.js`. dashboard-core (23) and
telemetry-msg (3) match the report. The off-by-one on the fleet-fields count is a reporting inaccuracy, not
a coverage gap — the mandated persist test (`:81`) and key-safety test (`:67`) are both present. Because
this disk review cannot execute the suites, the main agent SHOULD run all three suites and confirm green
counts (23 / 5 / 3) before marking done.
- evidence: fleet-fields.test.js:36,47,58,67,81 (5 tests); dashboard-core.test.mjs (23); telemetry-msg.test.mjs:20,28,38 (3).
- routeToPhase: none (informational; resolve at the main-agent run+verify gate).

No new CRITICAL or MAJOR finding.

---

## Convergence (4-D)

| Dimension | State | Basis |
|---|---|---|
| spec | YES | REQ-13 met (instances.sql:21,25-32); all REQ-1..14 + rulings honoured |
| tests (unit + persist-path) | YES on disk | dashboard-core 23 incl null-row; fleet-fields 5 incl upsertInstance persist; telemetry-msg 3 incl real-builder key-safety. Counts to be re-run by main agent (FIND-011) |
| impl | YES | pure core + extracted msg builder + store forwards full payload; no logic defect |
| verification | YES on disk; PENDING out-of-disk | adversary PASS (disk). Builder-reported live browser badges + manual a3cdd4 round-trip require the main agent's own browser/E2E confirmation (my disk scope cannot render DOM) |

CONVERGES: **YES**, conditional on the main agent's own gate — run the 3 suites (expect 23/5/3 green) and
the browser E2E (unique sentinel + human/local badges render on this instance's card per behavioral-spec.md:110-113).
The disk-reviewable work is complete and all iteration-2 findings (FIND-008/009/010) are RESOLVED with no new
blocker.
