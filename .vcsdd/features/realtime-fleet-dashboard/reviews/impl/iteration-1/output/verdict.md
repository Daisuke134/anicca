# Adversary Verdict — realtime-fleet-dashboard — Phase 3 Implementation Review (iteration 1)

- feature: realtime-fleet-dashboard
- reviewType: implementation (Phase 3)
- timestamp: 2026-06-29
- context: fresh, disk-only. Read every file in the manifest + the dependency files that
  the listed files call into (telemetry-store/verify/telemetry handler, dashboard-sync,
  telemetry-aggregate, and the existing telemetry test suite).

## OVERALL VERDICT: FAIL

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | FAIL |
| 2. Edge Case Coverage | PASS |
| 3. Implementation Correctness | PASS |
| 4. Structural Integrity | PASS |
| 5. Verification Readiness | FAIL |

overallVerdict = FAIL (any FAIL ⇒ FAIL). NOT ready to converge.

---

## Did the user's "always-STALE" hypothesis hold? NO — disproven from disk.

The concern was: if `dashboard-sync`'s aggregate drops `ts`, the page's `deriveStatus`
would `NaN→stale` always, and the STALE screenshot would be a hidden bug, not a real gap.

Disproven:
- `telemetry-store.js:9` queries `instances?...&select=ts` for replay protection — this only
  parses if `ts` is a real column, so `ts` IS a persisted column.
- `telemetry-store.js:15-21` `upsertInstance` POSTs the whole validated payload (which
  includes `ts`) → `ts` round-trips.
- `telemetry-aggregate.js:10` builds `leaderboard = [...rows].sort(...)` from `select=*`
  rows — it does NOT drop `ts`.
- `dashboard-sync.js:6` selects `*`.

⇒ leaderboard rows DO carry `ts`; `deriveStatus` on the page is fed a real `ts`. The STALE
badge is consistent with the benign explanation (poster ran ~10 min before render, `> 300s`).
This is positive evidence, not a free pass — see verification-readiness for why "STALE in the
screenshot" is still a weak E2E signal.

---

## Dimension 1 — Spec Fidelity: FAIL

What is correctly implemented (verified by inspection):
- REQ-1: poster builds `funding/env/brain` INSIDE the signed msg
  (`telemetry-poster.mjs:23-25` env-read w/ defaults human/local/claude-p; `:142-144`
  inside the `JSON.stringify`; `:155` `signMessage(msg)` signs the verbatim full msg) — code-correct.
- REQ-2 (accept): schema treats the 3 fields as optional-with-enum
  (`telemetry-schema.js:16-19`) — backward compatible (absent OK).
- REQ-7: page fetches `dashboard-sync` live (`page.tsx:48`), error → explicit ErrorCard
  (`page.tsx:83,229-235`); no hardcoded fallback rows; no static `dashboard.json` read.
- REQ-8: `toCardModel` returns the full fixed shape incl `assetsUsd = net_worth_usd`
  (`dashboard-core.mjs:54`), no open-ended fields.

FAIL findings (see FIND-001/002/004/005):
- FIND-001 (critical): REQ-12 (lines 89-92) says "a test SHALL assert" privkey + SERVICE_ROLE_KEY
  are never a substring of the message AND the key-set ⊆ allowlist. NO such test exists anywhere.
- FIND-002 (high): REQ-2/REQ-13 persistence of the 3 new fields + `log` round-trip is never
  asserted by any test; the schema's funding/env/brain enum branch is dead-untested.
- FIND-004 (medium): REQ-9 primary axis (harness/env/brain/model) is not the layout's axis —
  the board is ranked by net worth with harness attrs as secondary badges.
- FIND-005 (medium): the `brain` badge can misrepresent reality (declared claude-p while the
  live evidence shows a GLM-4.7 proxy/free model) — contradicts REQ-11's own NOTE.

## Dimension 2 — Edge Case Coverage: PASS

Positive evidence (implemented AND tested):
- missing/null/NaN `ts` ⇒ stale: `dashboard-core.mjs:11-12`; tests `dashboard-core.test.mjs:22-24`.
- exactly-300 ⇒ alive (strict `>`): `core:12`; test `:20`; 301 ⇒ stale test `:21`.
- `dead` overrides staleness: `core:10`; test `:19`. critical preserved + beaten-by-stale: tests `:25-26`.
- `countByStatus([])` all-zero: `core:24-28`; test `:39`.
- `toCardModel` null funding/env/brain ⇒ 'unknown': `core:36`; test `:59-62`.
- logs newest-first + cap 20 + kind normalize: `core:37-41`; test `:63-70`.
- 22 unit assertions present and internally consistent with the code (verified by inspection;
  not executed — I am the disk-only adversary). Plausibility of "22/22 pass" = confirmed.

(One low edge gap is logged under Dimension 3 / FIND-006, not enough to fail this dimension.)

## Dimension 3 — Implementation Correctness: PASS

Positive evidence:
- `ts` round-trips as a column (see top section) ⇒ no always-stale bug.
- `netUsd` monthly basis correct: `core:57` `revenueMoUsd - burnDayUsd*30`; matches REQ-6/M1 and
  test `:54`.
- signature covers the 3 new fields (full-msg signing, `poster.mjs:141-155`).
- key safety at the wire: the posted msg key-set = the documented allowlist; no private key in
  payload (`poster.mjs:141-154`).
- PostgREST injection guard on `id` before any DB query (`telemetry.js:24-25`; test
  `handler-telemetry.test.js:51-61`).
- aggregate's `status!=='dead'` is provably equivalent to `deriveStatus!=='dead'` (deriveStatus
  returns 'dead' iff `status==='dead'`), so `self_funded_pct` is consistent with REQ-5.

Low findings (do not fail the dimension): FIND-006 (no null-row guard in `toCardModel`),
FIND-007 (page renders only `logs.slice(0,8)` of the ≤20).

## Dimension 4 — Structural Integrity: PASS

- `dashboard-core.mjs` has zero `fetch`/`fs`/`supabase`/`Date.now` imports; `nowSec` is a
  parameter everywhere — purity boundary honoured.
- Page imports the pure core (`page.tsx:5`) and calls `countByStatus` (`:91`) + `toCardModel`
  (`:128`) rather than reimplementing display logic.
- `aggregate()` is REUSED for $ totals (not forked into TS), exactly as REQ-6 demands.

## Dimension 5 — Verification Readiness: FAIL

- FIND-001: REQ-12 key-safety test missing (mandated).
- FIND-003 (high): the integration/verify tests sign messages built by `canonicalMessage()`
  (`handler-telemetry.test.js:26`, `verify.test.js:11`) — the 11-field legacy shape that the
  poster NEVER sends. The real poster signs a 19-key msg (funding/env/brain/breakdown/log,
  `poster.mjs:141-154`). No test proves the ACTUAL posted message verifies → 202 → persists
  funding/env/brain → renders. The new code path is verified only by my reading, not by a test.
- The screenshot showing STALE is a weak convergence signal: STALE is *also* the exact symptom
  of a ts-less row, so the live evidence does not by itself distinguish "correct + 10min gap"
  from a regression. A real ALIVE row within one heartbeat (per the spec's `≤150s` sentinel E2E)
  was not demonstrated.

---

## FINDINGS

### FIND-001 — spec_fidelity / security_surface — CRITICAL
REQ-12 ("a test SHALL assert" privkey + SUPABASE_SERVICE_ROLE_KEY never appear in `message`, and
the top-level key-set ⊆ allowlist) is unimplemented. `dashboard-core.test.mjs` has 22 tests, none
key-safety. `runtime/dashboard/telemetry-poster.mjs` has no `__tests__`. No file asserts the
allowlist or secret-absence over the built payload.
- evidence: spec behavioral-spec.md:89-92; verification-architecture.md:32-37; absence across
  `apps/landing/lib/dashboard-core.test.mjs` and `runtime/dashboard/` (no poster test).
- routeToPhase: 2b (write the mandated key-safety unit over the built msg).

### FIND-002 — test_coverage / requirement_mismatch — HIGH
REQ-2/REQ-13: no test sends a signed message INCLUDING funding/env/brain and asserts they persist
(`upserts[0].funding === 'human'`), and no round-trip test proves `log` persists as a column. The
schema enum branch for the 3 fields (`telemetry-schema.js:17-19`) is never exercised (neither an
accept-good nor a reject-bad case).
- evidence: telemetry-schema.js:16-19 (untested branch); handler-telemetry.test.js:30-37 (asserts
  only `id`, message omits the 3 fields); dashboard-sync.test.js SAMPLE_ROWS:7-41 (no `log`, no
  funding/env/brain).
- routeToPhase: 2b.

### FIND-003 — verification_tool_mismatch — HIGH
The integration + verify tests sign `canonicalMessage()` (the 11-field legacy serializer), a
message shape the poster never emits. The real verify/store/render path for the poster's actual
full msg (with the 3 new fields + breakdown + log) is untested.
- evidence: telemetry-verify.js:7-13 (canonicalMessage = dormant 11-field helper);
  verify.test.js:11,16; handler-telemetry.test.js:26; vs poster.mjs:141-154 (real 19-key msg).
- routeToPhase: 2b.

### FIND-004 — requirement_mismatch — MEDIUM
REQ-9 requires harness/env/brain/model to be the PRIMARY visual grouping/axis. The page ranks the
leaderboard by net worth and shows harness attributes as secondary badges only — no grouping/axis
by harness/env.
- evidence: telemetry-aggregate.js:10 (sort by net_worth); page.tsx:112-114 (rank order),
  page.tsx:135-140 (attrs as tags).
- routeToPhase: 2b (or spec clarification if "badges suffice" is intended — then tighten REQ-9).

### FIND-005 — requirement_mismatch / spec_gap — MEDIUM
`brain` is env-declared (default 'claude-p', poster.mjs:25) and never reconciled with the
independently-derived `model_live`. Builder's own live evidence shows the badge CLAUDE-P next to a
GLM-4.7 (proxy/free) model — which directly contradicts REQ-11's NOTE ("brain='claude-p' ⇒ model
reads claude-sonnet-4-6"). The badge can assert a brain the body is not actually running.
- evidence: poster.mjs:25,108-113,133-134,144; behavioral-spec.md:78-81 (REQ-11 NOTE); builder
  E2E note (CLAUDE-P + FREE-GLM-4.7).
- routeToPhase: 2b / spec (decide whether brain must be validated against model_live or documented
  as a pure self-declared origin label).

### FIND-006 — impl_correctness — LOW
`toCardModel` dereferences `row.log`/`row.id` with no null guard, unlike `deriveStatus`
(`dashboard-core.mjs:10-11` guards null; `:35-37` does not). A null leaderboard entry throws.
Page never passes null today.
- evidence: dashboard-core.mjs:35-41.
- routeToPhase: 2b (cheap guard + test).

### FIND-007 — impl_correctness — LOW/INFO
The card renders only `c.logs.slice(0, 8)` of the ≤20 the model carries; the truncation to 8 is
undocumented vs REQ-8's "≤20".
- evidence: page.tsx:164.
- routeToPhase: 2c (cosmetic / doc).

---

## Convergence signals
- findingCount: 7 (1 critical, 2 high, 2 medium, 2 low)
- must-fix to converge: FIND-001, FIND-002, FIND-003 (then re-review). FIND-004/005 need a fix or
  an explicit spec ruling.
- duplicateFindings: none
- ready to converge: NO.
