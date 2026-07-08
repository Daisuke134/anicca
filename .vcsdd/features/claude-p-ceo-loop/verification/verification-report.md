# Verification Report

## Feature: claude-p-ceo-loop | Phase: 5 (Formal Hardening, mode: lean) | Iteration: 2 | Date: 2026-07-09

## Scope note

This is a re-verification of the Phase 5 iteration-1 report's 4 BLOCKING findings (F1-F4), fixed by
builder commit `07026f8` ("fix(ceo-loop): Phase 5 hardening 4-BLOCKING fix (F1/F2/F3/F4)") in
`~/anicca/.worktrees/ceo-loop`. Every claim below was independently re-run in this session (fresh
subprocess evidence, not a re-read of the commit message). `state.json` was not edited, per the task
instruction. All commands and outputs referenced below are saved under
`verification/security-results/iteration2-*.log` and `verification/iteration2-*.log` for audit.

## Proof Obligations — Findings F1-F4 (iteration-1 BLOCKING) re-verification

| ID | Iteration-1 verdict | Iteration-2 verdict | Evidence |
|---|---|---|---|
| F1 (earn-ledger read path disconnected from real data) | BLOCKING | **RESOLVED** | `iteration2-F1-live-reverification.log` |
| F2 (non-dict JSONL row crashes WEEKLY pass) | BLOCKING | **RESOLVED** | `iteration2-F2-purefunction-repro.log`, `iteration2-F2-endtoend-malformed-ledger-and-costevents.log` |
| F3 (`CEO_AGENT_DECISIONS_JSON` wrong-shape crash) | BLOCKING | **RESOLVED** | `iteration2-F3-11scenario-injection-probe.log` |
| F4 (allocation range-gate fail-open by default) | BLOCKING | **RESOLVED** | `iteration2-F4-failclosed-and-operator-override.log` |
| PROP-CEO-022 (RC≠0 reachability) | PASS | **PASS (fresh live re-confirmation)** | `iteration2-PROP-CEO-022-fresh-live-reconfirm.log` |

### F1 — RESOLVED
- `run_pass.py:36-52` imports `weekly_report.LEDGER_PATH_FOR_LOOP` (the same real production
  ledger-path resolver `weekly_report.py` itself uses) and `ledger_metrics.load_ledger_rows`. Confirmed
  by `Read` of the file and by `grep -n "earn-ledger.jsonl\"" run_pass.py` → no match; the fabricated
  `{state_dir}/{loop}-earn-ledger.jsonl` convention is gone.
- Live re-run: created real fixture ledgers (`clip.jsonl`: 2 rows, `earn_usdc` 10.0+15.0=25.0;
  `affiliate.jsonl`: 1 row, `commission_jpy` 1500 → 1500/150=10.0 usd) and pointed `run_pass.py` at
  them via `weekly_report.py`'s own env-override seams (`EARN_LEDGER`, `AFFILIATE_METRICS_PATH`,
  `EARN_VIDEO_METRICS_PATH`, `GIG_FUNNEL_PATH`, `BOUNTY_FUNNEL_PATH`). Output:
  `"company_score": 35.0"` (=25.0+10.0, exact expected value — not a fixture-independent constant).
  No `{loop}-earn-ledger.jsonl` file was created anywhere in the scratch state dir (confirmed by `ls`).
- Per-loop discrimination confirmed: `clip`/`affiliate` (real, positive data) do NOT appear in
  `allocation_decisions`; `video`/`gig`/`bounty`/`clip-promote` (no data source declared or empty
  ledger) all land in `reduce_frequency` — proving the WEEKLY pass now discriminates on real per-loop
  data, not a single company-wide stub. `pm-earner`/`clip-promote` (no declared real-ledger source)
  honestly stay at empty rows, matching the builder's own claim — no fabricated non-zero.

### F2 — RESOLVED
- `allocator.sum_earn_by_currency` (line 53: `dict_rows = [r for r in rows if isinstance(r, dict)]`),
  `budget.monthly_spend_by_loop` (line 77-78), `budget.weekly_spend_by_loop` (line 98-99), and
  `budget.load_fired_alert_keys` (line 186) all now guard `isinstance(row, dict)`. `run_pass.py`'s own
  prior-row readers (`_latest_per_loop_scores` line 107, `prior_rows` list-comprehension line 228) also
  guard.
- Re-ran the adversary's exact 3 repro calls at the pure-function level: all return the correct
  aggregate (`sum_earn_by_currency([{"earn_usdc":5.0},"not-a-dict-line",{"earn_usdc":3.0}])` → 8.0;
  `monthly_spend_by_loop`/`weekly_spend_by_loop` with mixed bad-type rows → correct totals, no crash).
- End-to-end: built a real `clip.jsonl` ledger with 4 malformed lines (`"not-a-dict-line"`, `null`,
  `123`, `["x","y"]`) interleaved with 2 valid rows, plus a `ceo-cost-events.jsonl` with the same
  malformed-line pattern. Full `run_pass.py` WEEKLY pass completed **RC=0**,
  `"company_score": 15.0"` (10.0+5.0, correctly skipping the bad lines).

### F3 — RESOLVED
- Re-ran all 4 of the adversary's original crashing scenarios (array `[1,2,3]`, bare string, bare
  `null`, per-loop value not a dict) PLUS 7 additional adjacent scenarios (bad-perloop-number,
  bad-perloop-array, empty object, empty file, malformed JSON syntax, valid decision, mixed
  valid+invalid) = 11 total. **All 11 complete with RC=0.** The 4 that previously crashed now emit a
  structured rejection log line (`"step": "8_agent_decisions_rejected"` /
  `"8_agent_decision_rejected"` with `reason`/`type`) and continue the pass with that decision treated
  as absent.
- Positive-path regression check: a syntactically valid decision (`{"clip":{"allocation":
  {"pass_frequency_multiplier":2.0}}}`) is still applied correctly
  (`allocation_decisions.clip.allocation.pass_frequency_multiplier == 2.0`), and a mixed
  valid+invalid file correctly isolates per-loop (clip's valid decision applied, affiliate's
  malformed one rejected+logged) — the fix does not silently swallow good input alongside bad.

### F4 — RESOLVED
- `allocator.DEFAULT_ALLOCATION_RANGES` (lines 163-167) ships `fleet_size_target: {min:0, max:50}`,
  `capital_cap_usd: {min:0, max:1_000_000}`, `pass_frequency_multiplier: {min:0.1, max:10}`.
  `run_pass.py:270-274` applies these whenever `ceo-allocation-ranges.json` does not exist on disk.
- Live-reproduced the exact adversary scenario: `CEO_AGENT_DECISIONS_JSON={"clip":{"allocation":
  {"fleet_size_target":-5}}}` against a scratch state dir with NO `ceo-allocation-ranges.json`
  present → `loop-registry.json`'s `clip` entry has `"allocation": null` (unchanged from bootstrap) —
  the field is absent, not `-5`. RC=0.
- Verified the other direction too (not in iteration-1's scope, added here for completeness): an
  explicit `ceo-allocation-ranges.json` with `fleet_size_target: {min:-10, max:50}` present on disk
  DOES let `-5` through (`clip.allocation.fleet_size_target == -5` in the written registry) — operator
  intent, when explicitly configured, still overrides the shipped defaults as designed.

### PROP-CEO-022 — fresh live re-confirmation
- `founder-loop.sh:77`: `bash "$HERE/ceo/ceo-pass.sh" || true`, called unconditionally before the
  script's own `exit $RC` — confirmed by direct code read, not just prior evidence.
- Live re-run: forced `founder-loop.sh` to RC=1 via a corrupted `FOUNDER_LEDGER` (`{not valid json`).
  Observed `record_rc=1` / `founder-loop.sh RC=1` ("LEDGER UNREADABLE" fail-safe) AND `ceo-pass.log`
  gained a fresh marker line, AND — because this session's `run_pass.py` now reads real F1-wired ledger
  data — `company_score: 35.0` was computed and `loop-registry.json` was written, all despite the
  founder-loop wake itself having failed. This is stronger evidence than iteration-1's (which predates
  the F1 fix and could only show the marker log, not a real company_score).

## Results — NEW finding (Phase 5 iteration-2)

### Finding F5 (BLOCKING, NEW) — a wrong-type numeric field inside an otherwise-valid dict row crashes 3 functions
- **Where**: `allocator.py:54` (`usd_total = sum(float(r.get("earn_usdc", 0) or 0) for r in
  dict_rows)`) and `:56` (same pattern for `earn_jpy`/`commission_jpy`); `budget.py:82`
  (`monthly_spend_by_loop`) and `budget.py:103` (`weekly_spend_by_loop`) — both
  `usd = float(row.get("usd_estimate") or 0.0)`.
- **What was observed**: a ledger/cost-event row that IS a dict (passes F2's `isinstance(row, dict)`
  guard) but whose expected-numeric field holds a non-numeric string (e.g. `{"earn_usdc":
  "not-a-number"}`, a plausible hand-edit, partial write, or upstream writer bug) raises an uncaught
  `ValueError: could not convert string to float: '...'` inside `sum()`'s generator expression.
  `run_pass.py`'s `main()` wraps none of this in `try/except`, so the crash propagates all the way to
  `sys.exit(1)` — same blast radius as the (now-fixed) F2: the pass aborts before step (9)'s registry
  write, step (11)'s verification row, and step (12)'s mail report.
- **Boundary-tested, only this shape crashes**: huge value (`1e18`), negative value (`-999999.99`),
  missing field entirely, explicit `null`, and an empty dict `{}` ALL pass through cleanly (the
  existing `or 0`/`.get(..., 0)` defaulting handles those). Only a **non-numeric string value** in a
  numeric field crashes — reproduced identically in `sum_earn_by_currency`, `monthly_spend_by_loop`,
  and `weekly_spend_by_loop` (3 call sites, same defect class).
- **Why this is a genuinely NEW finding attributable to this iteration's fix, not a pre-existing gap
  that was already reported**: before F1, `run_pass.py` read from a fabricated
  `{state_dir}/{loop}-earn-ledger.jsonl` path that "no loop CLI has ever written to" (iteration-1's own
  F1 finding) — so in production this code path was always fed `[]` (empty), and this crash, while
  theoretically present in the function's code even then, was never actually reachable by real data.
  F1's fix (correctly, per its own mandate) now routes `run_pass.py` through the SAME real,
  externally-written production ledger files (`~/.openclaw/state/clip-earn-ledger.jsonl`,
  `~/.cloak/affiliate-metrics.jsonl`, etc.) that this feature does not control the writer of — making a
  wrong-type field value in those files a live, previously-nonexistent attack/corruption surface for
  the WEEKLY pass. This is the specific "does F1 open a new door" check requested for this iteration,
  and it does.
- **Live reproduction**: `verification/security-results/iteration2-F5-NEW-wrongtype-numeric-field-crash.log`
  — includes the pure-function boundary matrix, the `budget.py` repro, and a full `run_pass.py`
  subprocess traceback via a real ledger file containing one `"earn_usdc": "not-a-number"` row (exit
  code 1).
- **Recommendation for the next iteration**: replace the bare `float(x or 0)` pattern at the 4 call
  sites above with a small safe-coercion helper (`try: float(x) except (TypeError, ValueError): 0.0`,
  or reuse one if `ledger_metrics.py`/agent-os's own budget module already has one — check before
  writing a new one, per `車輪の再発明禁止`) so a wrong-type field is skipped/zeroed like the other
  boundary cases, not fatal.

### Non-blocking observations (INFO, unchanged from iteration-1, not re-litigated in depth)
- `allocator.convert_to_usd()`'s bare `KeyError` on a `fx_config` present-but-missing `jpy_usd_rate` is
  still narrow/unreached by simple file-absence; not re-tested this iteration (out of F1-F4 scope, no
  regression indicated).
- `bandit.ThompsonSamplingRouter` still unwired to any config-driven linucb/thompson switch — unchanged
  observation, not re-tested this iteration.

## Regression check
- All 14 shipped test files, 168/168 assertions, re-ran green in this session (`tests/test_*.py` via
  `python3 <file>.py`, same non-pytest-collectible pattern as iteration-1 — confirmed again this
  session: `pytest` still INTERNALERRORs on collection for these standalone scripts).
- `skills/self/founder-loop/test-founder-loop.sh` baseline (INV-H1..H6 + FOUNDER_LEDGER TEST-gated +
  corrupt-ledger fail-safe) re-ran green.
- Full log: `verification/security-results/iteration2-regression-168tests-and-baseline.log`.

## Degradation notes
Same as iteration-1: no Tier-3 formal tooling applicable (Python/Bash feature); all evidence is live
subprocess execution + direct source read, not a formal prover.

## Summary
- F1, F2, F3, F4 (iteration-1 BLOCKING): **all 4 RESOLVED**, independently re-verified with fresh live
  execution in this session (not a re-read of the builder's commit message).
- PROP-CEO-022: PASS, fresh live re-confirmation, stronger evidence than iteration-1 (real
  company_score now flows through even on an RC≠0 wake).
- **NEW BLOCKING finding this iteration: F5** — wrong-type numeric field value (valid dict row, invalid
  field type) crashes `sum_earn_by_currency`/`monthly_spend_by_loop`/`weekly_spend_by_loop`, a
  previously-unreachable production surface that F1's own fix newly opened by wiring to real,
  externally-written ledger files.
- Regressions: 0 — all 168 shipped Tier1 assertions + baseline (INV-H1..H6) still green.
- **Overall verdict: NOT yet a clean PASS — 1 new BLOCKING finding (F5) requires another fix
  iteration before Phase 5 can close.** The 4 findings this task was specifically asked to re-verify
  (F1-F4) are genuinely resolved; F5 is a direct, in-scope consequence of the F1 fix surfaced by this
  iteration's own "does the fix open a new door" check (task item 6) and must be treated with the same
  BLOCKING severity as F2 (same defect class, same blast radius: whole-WEEKLY-pass abort, RC=1, no
  registry/verification/mail).

## Phase 5 iteration-3 — F5 RESOLVED (orchestrator independent re-check)

F5 fixed via `_safe_float(value, default)` in allocator.py + budget.py (4 call sites: sum_earn_by_currency earn_usdc/earn_jpy/commission_jpy, monthly_spend_by_loop, weekly_spend_by_loop). Independently re-run against worktree (commit 5112554):
- `sum_earn_by_currency([{"earn_usdc":"not-a-number"},{"earn_usdc":5.0}])` -> usd=5.0 (was ValueError). RESOLVED.
- `sum_earn_by_currency([{"earn_jpy":{"nested":"dict"}},{"earn_jpy":1000}])` -> jpy=1000.0 (was TypeError). RESOLVED.
- Existing boundaries intact: empty->0, null->0, negative->passes through (-3.0).
- test_currency_conversion 17/17, test_cost_events_and_spend 11/11 green.
- Builder subprocess proof: run_pass.py exit 0 with malformed ledger row, company_score 9.5 (bad row degraded to 0).

## Summary (final)

All BLOCKING findings resolved across iterations: F1 (fabricated ledger path -> real weekly_report/ledger_metrics wiring, company_score non-zero from real data), F2 (non-dict row guard), F3 (CEO_AGENT_DECISIONS_JSON shape validation), F4 (allocation-ranges fail-closed default), F5 (safe numeric coercion). PROP-CEO-022 confirmed live. 168 tests + baseline green. No remaining BLOCKING. Hardening PASS.
