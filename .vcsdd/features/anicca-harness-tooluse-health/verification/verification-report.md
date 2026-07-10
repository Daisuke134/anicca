# Verification Report

## Feature: anicca-harness-tooluse-health | Sprint: 1 | Date: 2026-07-10

## Context

Pure observability feature (health aggregators over already-parsed ledger records + an append-only
`harness-failures.jsonl` writer + a snapshot CLI + a Python twin for `skills/self/self-improve`
consumption). No money/wallet/spend path is touched (confirmed by import-grep below). Tier assignment
per the VCSDD tier table: **Tier 1** (property/unit + integration tests) is the correct tier for this
non-critical, deterministic bookkeeping logic over an already-fixed `kind` enum (per INV-NO-JUDGMENT) —
not Tier 2/3, since nothing here is security/financial/safety-critical and the spec's own proof table
(`specs/verification-architecture.md`) was authored entirely as unit/integration test obligations, not
formal-methods obligations. No Kani/Hypothesis-style bounded-model-checking tool applies to this
JS+Python aggregation logic; `node --test` (JS) and a script-style manual test runner (Python, mirroring
the existing `tests/test_loop_evaluators.py` convention in the same directory) are the correct and
sufficient tools, already used throughout Phase 2.

## Proof Obligations

All 10 requirements from `specs/behavioral-spec.md` (R1-R10), each with its proof strategy from
`specs/verification-architecture.md`'s proof table, are treated as required proof obligations for this
phase. IDs below (`PROP-HH-R1`..`PROP-HH-R10`) are newly assigned in this phase (state.json's
`proofObligations` array was empty entering Phase 5 — the Phase 1b proof table existed only as prose).

| ID | Requirement | Tier | Required | Status | Tool | Evidence |
|---|---|---|---|---|---|---|
| PROP-HH-R1 | R1 layer classification (fail-safe enum map) | 1 | true | proved | node --test | `runtime/loop/__tests__/harness-health.test.mjs` (6 R1 tests) + `skills/self/self-improve/tests/test_harness_health.py` (8 R1 tests, incl. Python twin) |
| PROP-HH-R2 | R2 per-slot health + loop_detect exclusion (INV-LOOPDETECT-SEPARATE) | 1 | true | proved | node --test + python | `harness-health.test.mjs` (5 R2 tests incl. the `loop_detect`-carrying-`slot` exclusion fixture) + `test_harness_health.py` R2 test |
| PROP-HH-R3 | R3 brain-transport health, independent of any slot | 1 | true | proved | node --test + python | `harness-health.test.mjs` (3 R3 tests) + `test_harness_health.py` R3 test |
| PROP-HH-R4 | R4 whole-ledger report shape, never throws | 1 | true | proved | node --test + python | `harness-health.test.mjs` (3 R4 tests) + `test_harness_health.py` (3 R4 tests) |
| PROP-HH-R5 | R5 escalation predicate, boundary-exact | 1 | true | proved | node --test + python | `harness-health.test.mjs` (4 R5 tests, incl. one-below/at/one-above threshold) + `test_harness_health.py` (4 R5 tests) |
| PROP-HH-R6 | R6 failure-detail side-channel: redact-before-slice, 4000-char cap both branches, `slot` omitted for brain_transport, clean wakes append nothing, `result` field byte-identical/unregressed | 1 | true | proved | node --test (real temp-`$ANICCA_HOME` spawned-process integration) | `harness-health-failure-detail.test.mjs` (8 tests, all green — see per-test breakdown below) |
| PROP-HH-R7 | R7 snapshot CLI: overwrite semantics, empty-ledger fallback, no crash on missing ledger | 1 | true | proved | node --test (temp-dir integration) | `harness-health-snapshot.test.mjs` (3 tests) |
| PROP-HH-R8 | R8 Python mirror + cross-language parity (shared fixture) | 1 | true | proved | node --test + python (shared fixture) | `harness-health.test.mjs` R8 test + `test_harness_health.py` (3 R8 tests) both reading the SAME `runtime/loop/__tests__/fixtures/harness-health-parity.json` |
| PROP-HH-R9 | R9 backward compatibility / non-interference (ledger schema, prompt token footprint, evaluator.py/weekly_report.py untouched) | 0 | true | proved | node --test + python regression suites + git diff | Full regression run below; zero diff on `evaluator.py`/`ledger_metrics.py`/`weekly_report.py` |
| PROP-HH-R10 | R10 no auto-action / no new self-fix.sh call site | 0 | true | proved | node --test (static grep, executed) + manual re-grep | `harness-health-no-autoaction.test.mjs` + independent manual `grep -rn "self-fix.sh"` re-run in this session (see below) |

**Required obligations: 10. Proved: 10. Failed: 0. Skipped: 0.**

## Results

### PROP-HH-R1..R5 (pure aggregators, both languages)
- **Tool**: `node --test` / Python script-style test runner
- **Command**: `cd ~/anicca && node --test runtime/loop/__tests__/harness-health.test.mjs runtime/loop/__tests__/harness-health-failure-detail.test.mjs runtime/loop/__tests__/harness-health-snapshot.test.mjs runtime/loop/__tests__/harness-health-no-autoaction.test.mjs` and `cd ~/anicca/skills/self/self-improve && python3 tests/test_harness_health.py`
- **Result**: 34/34 JS ✅, 22/22 Python ✅ (re-run fresh in this session, not reused from Phase 2 evidence logs)
- **Output** (JS, tail): `ℹ tests 34 / ℹ pass 34 / ℹ fail 0 / ℹ cancelled 0 / ℹ skipped 0`
- **Output** (Python, tail): `=== test_harness_health: 22 passed 0 failed ===`

### PROP-HH-R6 (failure-detail side-channel, integration)
- **Tool**: `node --test` (real temp `$ANICCA_HOME`, real spawned mock skills / real thrown THINK errors)
- Individual assertions, all PASS in this session's fresh run:
  - `wake_error` wake → exactly one `harness-failures.jsonl` line, no `slot` key, `layer:'brain_transport'`
  - brain_transport `err.message` containing a 64-hex private-key pattern → `detail` shows `[REDACTED]`, not the raw hex (proves the NEW `redactPrivateKeyPatterns(err.message)` call site actually redacts)
  - `skill_error` wake with >2000-char stdout → `detail` LONGER than 900 chars while `ledger.jsonl`'s `result` for the SAME wake stays ≤900 chars (genuine divergence proof)
  - `skill_error` wake with >4000-char stdout → `detail` length EXACTLY 4000
  - `wake_error` wake whose `err.message` is 6000 chars → `detail` length EXACTLY 4000 (brain_transport twin of the tool_logic upper-boundary fixture)
  - clean `wake` → **zero** lines appended to `harness-failures.jsonl`; `ledger.jsonl`'s `result` stays ≤900 chars (INV-NO-PROMPT-REGRESSION)
  - `capFailureDetail` unit-level boundary proofs (both branches, whitespace-collapse-before-cap ordering)
- **Result**: 8/8 tests in `harness-health-failure-detail.test.mjs` PASS (integration tests, ~600ms-4.5s each — real process spawns/HTTP mocks, not stubs)

### PROP-HH-R7 (snapshot CLI, integration)
- **Tool**: `node --test` (real temp dir, real `node harness-health-snapshot.mjs` subprocess)
- **Result**: 3/3 PASS — fixture-ledger deep-equal to direct `computeHarnessHealth` call; missing-ledger empty-shape fallback, exit 0; re-run overwrite semantics (no unbounded growth)
- **Additional self-run evidence** (from Phase 2b, still valid — not re-executed against production disk in this Phase 5 session to avoid touching live state, but re-verified by code inspection this session): `harness-health-snapshot.mjs` was run in Phase 2b against a READ-ONLY copy of the real `~/.anicca/state/ledger.jsonl` (11774 lines) and cross-checked field-for-field against manual `grep -c`/`uniq -c` counts over the same file (see `evidence/sprint-1-green-phase.log`) — `brainTransport.failures=1245` matched `grep -c wake_error` exactly; slot `earn/gig` wakes=92/failures=92/escalate:true matched grep exactly; slot `hl_trade` wakes=1865/failures=2 matched grep exactly AND independently confirmed INV-LOOPDETECT-SEPARATE on real production data (147 real `loop_detect` rows carrying `slot:hl_trade` correctly excluded).

### PROP-HH-R8 (cross-language parity)
- **Tool**: `node --test` + Python, both reading `runtime/loop/__tests__/fixtures/harness-health-parity.json`
- **Result**: JS's `computeHarnessHealth` on the shared fixture matches `expected` field-for-field (generatedAt excluded); Python's `compute_harness_health` on the SAME fixture matches the SAME `expected` field-for-field; `harness_health_report.py <fixture> --threshold 5` CLI output matches `compute_harness_health(fixture_rows, 5)` called directly. Confirmed by reading both test files: they resolve `FIXTURE_PATH`/`fixturePath` to the identical file on disk (one JSON file, two consumers) — a genuine cross-language identity proof, not two independently-asserted "probably right" fixtures.

### PROP-HH-R9 (regression / non-interference)
- **Tool**: `node --test` over the full `runtime/loop/__tests__/*.test.mjs` directory (not just this feature's own package.json `test` script subset) + full `skills/self/self-improve/tests/*.py` directory + `git diff --stat`
- **Command**: `cd ~/anicca/runtime/loop && node --test __tests__/*.test.mjs` ; `cd ~/anicca/skills/self/self-improve && for f in tests/test_*.py; do python3 "$f"; done` ; `git diff --stat HEAD -- skills/self/self-improve/lib/ledger_metrics.py skills/self/self-improve/weekly_report.py skills/earn/self-improve/evaluator.py`
- **Result**:
  - Full JS suite: **214 tests, 213 pass, 1 fail.** The 1 failure is `PROP-201g: every currently-live registry.json slot matches behavioral-spec.md's exact expected count (17)` in `registry-classification.test.mjs` — asserts `registry.json` has exactly 17 live slots, found 18 (`["report","self/spawn","self/spawn-child","self/issue-dev","self/coordinate","economy/gig","economy/ubi","economy/lending","cook","yield","hl_trade","x402_sell","token_launch","earn/clip","earn/clip-producer","earn/video","earn/sol-trade","earn/polymarket-trade"]`). This is a **pre-existing, unrelated drift** between `registry.json`'s live-slot count and a stale expected-count constant in that test file (a slot-catalog bookkeeping test, unrelated to `kind`/`slot`/harness-health fields) — tracked separately per this task's briefing, NOT touched by this feature, and present identically before this feature's implementation (Phase 2a RED-phase log) and after (Phase 2b GREEN-phase log and this session's fresh re-run).
  - `config.test.mjs` (previously flagged as another pre-existing failure in earlier VCSDD sprint notes): re-run in isolation this session — **7/7 PASS**. Confirmed genuinely fixed/green now, not a lingering failure.
  - Full Python regression suite (`skills/self/self-improve/tests/`): `test_affiliate_evaluator_commission.py` 2/2, `test_gig_evaluator_by_category.py` 8/8, `test_harness_health.py` 22/22, `test_loop_evaluators.py` 15/15, `test_weekly_compare.py` 5/5, `test_weekly_report.py` 12/12 — **64/64 PASS, 0 fail**.
  - `git diff --stat` on `evaluator.py` / `ledger_metrics.py` / `weekly_report.py`: **empty output — zero diff**, confirming R9's "none of the three is modified by this feature" claim.

### PROP-HH-R10 (no auto-action)
- **Tool**: `node --test` (executes the grep itself as an automated assertion) + independent manual re-run
- **Command**: `grep -rn "self-fix.sh" runtime/loop/ skills/self/self-improve/`
- **Result**: only 5 matches, ALL inside `runtime/loop/__tests__/harness-health-no-autoaction.test.mjs`'s own header comment / test body prose (documenting/asserting the absence, not invoking it). Zero matches in any production file. `harness-health-no-autoaction.test.mjs`'s own test (which excludes its own file from the scan and asserts empty output) PASSES.

## Degradation Notes
No Tier 2/3 tool (Kani, formal model checker) was needed or attempted — Tier 1 (property/unit + integration
tests) is the spec-declared and correctly-matched tier for this deterministic bookkeeping logic (see
Context above). No degradation occurred.

## Summary
- Required obligations: 10
- Proved: 10
- Failed: 0
- Skipped: 0
- Non-required regression note: 1 pre-existing, unrelated test failure (`registry-classification.test.mjs`
  PROP-201g, live `registry.json` slot-count drift) persists unchanged from before this feature's
  implementation; does not block this feature's proof obligations and is explicitly out of this
  feature's scope (R9's "None of R1-R8 change... `registry.json`" is not itself a claim — this failure
  predates and is orthogonal to R1-R10).
