# VCSDD Phase 1c Spec Review — realtime-fleet-dashboard (ITERATION 3, final lean round)

- Reviewer: VCSDD Adversary (fresh context, disk-only, zero builder context)
- Date: 2026-06-29
- Artifacts reviewed: `specs/behavioral-spec.md`, `specs/verification-architecture.md` (the iteration-3 content; both still title-labelled "ITERATION 2" — see M3)
- Grounding cross-checked LINE-BY-LINE against the REAL files (not the spec's claims):
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-verify.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-schema.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-store.js`
  - `~/anicca-project/apps/landing/netlify/functions/dashboard-sync.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-aggregate.js`
  - `~/anicca/runtime/dashboard/telemetry-poster.mjs`

## OVERALL VERDICT: **PASS**

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **PASS** |
| 2. Edge Cases | **PASS** |
| 3. Completeness / Gaps | **PASS** |
| 4. Structural Integrity (purity boundary) | **PASS** |
| 5. Verification Readiness | **PASS** |

N1–N9 from iteration-2 review: **9 / 9 RESOLVED** (verified against disk, not just claimed).
New findings: **0 critical, 0 major, 4 minor** (M1–M4; non-blocking in lean mode).
This spec is **READY TO EXIT the Phase 1c gate.**

---

## N1–N9 Resolution (each verified against the actual source)

| ID | iter-2 problem | Status | Disk evidence |
|---|---|---|---|
| **N1** (critical) | fabricated "host-guard" the spec leaned on | **RESOLVED** | Spec line 16 now grounds id-binding to `telemetry-verify.js:28` and states verbatim "NOT a 'host-guard'; there is no host check beyond nonempty-string." Confirmed: `telemetry-verify.js:28` = `if (signer.toLowerCase() !== p.id.toLowerCase()) return { reason: "signer_mismatch" }`; `host` is only `length===0` checked at `telemetry-schema.js:7-9`. REQ-3 (lines 48-50) + §Decision line 26 now name `signer_mismatch` as the writer→row binding. No `host_wallet_mismatch` string remains anywhere. |
| **N2** (major) | `computeTotals` (TS) duplicated `aggregate` (JS); which renders undefined | **RESOLVED** | REQ-6 (lines 57-62) deletes `computeTotals`; "$ totals SHALL be REUSED from server-side `aggregate()` … `aggregate` is NOT reimplemented in TS." Only new pure aggregation = `countByStatus(rows,nowSec)→{alive,stale,dead,critical}` (staleness, which `aggregate` does not compute). ver-arch line 8-9 mirrors. Single source for the 4 $ figures = `telemetry-aggregate.js:11`. Non-overlapping with the counts. |
| **N3** (major) | schema's `'critical'` silently swallowed by `deriveStatus` | **RESOLVED** | REQ-4 line 53 "else 'critical' if `status==='critical'` (preserved, not swallowed)"; ver-arch line 6 return type `'alive'|'stale'|'critical'|'dead'`; `countByStatus` now returns a 4th `critical` count (REQ-6 line 60). Ordering (dead→stale→critical→alive) is defined and internally consistent. |
| **N4** (minor) | server default VALUES for funding/env/brain on legacy path unspecified | **RESOLVED** | REQ-14 lines 87-88: migration columns default NULL; OLD-poster rows render `'unknown'` (explicitly NOT assumed human/local). ver-arch line 11 mirrors in `toCardModel`. |
| **N5** (major) | the REAL anti-overwrite defense (`signer_mismatch`) had no named test | **RESOLVED** | ver-arch line 41 Integration (c): "post signed by a DIFFERENT key than `id` → 401 `signer_mismatch` (the akash-fix regression, N5)"; acceptance line 98 adds the anon-write rejection. Both map to `telemetry-verify.js:28`. |
| **N6** (minor) | sync path + leaderboard shape mis-cited | **RESOLVED** | Spec line 20 corrects path to `apps/landing/netlify/functions/dashboard-sync.js` (not `_lib/`) and describes `leaderboard[]` = "full rows" — matches `dashboard-sync.js:6` (`select=*`) + `telemetry-aggregate.js:10` (`[...rows].sort`). |
| **N7** (major) | REQ-8 assumed `log`/3-fields are persisted columns; unverified | **RESOLVED** | REQ-13 lines 82-86 ships explicit DDL `ALTER TABLE instances ADD COLUMN IF NOT EXISTS funding/env/brain text` AND a round-trip integration test that `log` is a persisted jsonb column (adding if absent). ver-arch line 41 (a) proves migration applied + `log` returned via `select=*`. This closes the gap created by `store.js` persisting only existing columns. |
| **N8** (minor) | REQ-11 promised a fixed `model` though it is DERIVED | **RESOLVED** | REQ-11 lines 80-81 now states `model_live` is DERIVED by `lastModel()` from the ledger, NOT declared — confirmed `telemetry-poster.mjs:102-106` (`lastModel()` default `"auto"`). No test depends on a fixed model string (acceptance line 100-102 asserts only the 3 badges). Residual wording nit → M4 (minor). |
| **N9** (minor) | `isSelfFundedEconomic` arity inconsistent (1 vs 2 args) | **RESOLVED** | REQ-5 line 56 "Signature is `(row, nowSec)` in BOTH spec docs"; ver-arch line 7 `isSelfFundedEconomic(row, nowSec)`. Consistent + testable. Note: `deriveStatus≠'dead'` ⟺ `status!=='dead'` (REQ-4's only 'dead' source), so REQ-5 stays equivalent to `telemetry-aggregate.js:6`. |

---

## Dimension 1 — Spec Fidelity: **PASS**
Positive evidence: every grounding citation now matches disk. `signer_mismatch` at `telemetry-verify.js:28` (N1), `canonicalMessage` correctly described as a dormant client helper (`telemetry-verify.js:4-13`), `status` enum at `telemetry-schema.js:15`, whole-payload upsert at `telemetry-store.js:14-19`, `select=*`→`aggregate` at `dashboard-sync.js:6`, leaderboard=full-rows at `telemetry-aggregate.js:10`, verbatim-sign + 120s at `telemetry-poster.mjs:135-148,156`. The 19-field key-safety allowlist (ver-arch lines 32-34) equals the 16 real posted fields + 3 new. The fabricated-citation class that failed iter-1/iter-2 is gone.

## Dimension 2 — Edge Cases: **PASS**
`deriveStatus` edges (missing/null/NaN ts → stale; exactly-300 → alive; 301 → stale; dead overrides) defined and consistent (REQ-4, ver-arch lines 21-24). `'critical'` now first-class (N3). Empty-fleet → `countByStatus([])` all-zero (REQ-6) and `aggregate` pct guard matches `telemetry-aggregate.js:8-9`. burn_day=0 confirmed non-hazard. One stale residual → M2 (minor, the ver-arch edges table row still names the deleted `computeTotals`).

## Dimension 3 — Completeness / Gaps: **PASS**
N2 (single source of $ totals) and N7 (explicit DDL + log-column round-trip) are the substantive closures and both hold. Scope IN/OUT is concrete. Backward-compat (old poster → 202 + `'unknown'`) defined. Residual: `netUsd`'s sign-semantics are defined (ver-arch line 28: burn>revenue ⇒ net<0) but the daily-vs-monthly normalization basis is unpinned → M1 (minor).

## Dimension 4 — Structural Integrity (purity boundary): **PASS**
Pure `dashboard-core` (ver-arch lines 5-11) keeps `nowSec` an explicit parameter on `deriveStatus`/`isSelfFundedEconomic`/`countByStatus`/`toCardModel` (no `Date.now()`), forbids fetch/supabase/fs imports, isolates I/O behind a fake-source adapter (line 16). `toCardModel`'s return shape is fully enumerated, no open-ended fields. Removing `computeTotals` (N2) reduced surface and eliminated the JS/TS duplication without breaking the boundary.

## Dimension 5 — Verification Readiness: **PASS**
Signatures pinned (N9); `signer_mismatch` integration test named (N5); DDL round-trip + `log`-column read-back test (N7); key-safety allowlist matches the real 19-field payload; replay test (ts≤lastTs) maps to `telemetry-verify.js:25`; E2E unique-sentinel probe (acceptance lines 99-102) objectively distinguishes live registry from a cached/hardcoded board. Pure-core unit plan is RED-first and parameterized. The minors below slightly nick precision but block nothing.

---

## NEW findings (all minor — non-blocking in lean mode)

### M1 (minor, spec_gap / verification) — `toCardModel.netUsd` period-normalization unpinned
REQ-8 (line 68) lists `netUsd` with no formula in the requirement; ver-arch line 28 ("burn>revenue ⇒ net<0") defines its SIGN as net = revenue − burn but not the basis. Fields are `revenue_mo_usd` (monthly) vs `burn_day_usd` (daily), so the unit test for `toCardModel` cannot assert `netUsd` without choosing `revenue_mo_usd − burn_day_usd*30` (monthly) or `revenue_mo_usd/30 − burn_day_usd` (daily, the basis REQ-5 already uses). **Fix at build:** state the exact expression in REQ-8 (recommend the daily basis to match REQ-5).

### M2 (minor, internal inconsistency) — ver-arch edges table cites the DELETED `computeTotals`
ver-arch line 25 still lists `empty fleet computeTotals([]) → {assets:0,…,counts:{0,0,0},…}` — but line 8 says "NO `computeTotals`", and the real empty edge is `countByStatus([])` = all-zero with FOUR counts `{alive,stale,critical,dead}` (REQ-6). The stale 3-count row is a leftover from the N2 fix. **Fix:** replace that row with `countByStatus([]) → {alive:0,stale:0,critical:0,dead:0}`.

### M3 (minor, labeling / handover) — both spec docs are title-labelled "ITERATION 2"
`behavioral-spec.md:1` and `verification-architecture.md:1` both read "ITERATION 2", yet the bodies fix N1–N9 (raised by the iteration-2 review) → the content is iteration 3. A fresh handover reader will mis-date the artifacts. **Fix:** bump both titles to ITERATION 3.

### M4 (minor, requirement precision) — REQ-11 NOTE conflates `brain` (declared) with `model_live` (derived)
REQ-11 lines 80-81 say "with `brain='claude-p'` it will read `claude-sonnet-4-6`", but `brain` is a separate declared field and `model_live` is derived by `lastModel()` (`telemetry-poster.mjs:102-106`, default `"auto"`) independently of `brain`. The asserted value is illustrative and no test depends on it (acceptance asserts only the human/local/claude-p badges), so non-blocking. **Fix:** reword to "model_live = whatever `lastModel()` resolves; `brain` is the declared engine label, not the model string."

---

## Gate decision
PASS. All 5 dimensions PASS; 9/9 prior N-findings resolved with disk evidence; zero open criticals; zero new criticals or majors. The 4 minors (M1–M4) are non-blocking under lean rules — fold them into the build (M1 + M2 should be settled before writing the `toCardModel` / empty-fleet unit tests). The spec may exit the Phase 1c gate and proceed to Phase 2a (RED).
