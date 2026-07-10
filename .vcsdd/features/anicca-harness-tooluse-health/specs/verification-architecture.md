# Verification Architecture — anicca-harness-tooluse-health (VCSDD Phase 1b)

Companion to `behavioral-spec.md` (R1-R10). Defines HOW each requirement is proven and the purity
boundary.

## Purity boundary (pure core vs. impure shell)

- **PURE (deterministic, no I/O — unit-testable in isolation):**
  - `runtime/loop/harness-health.mjs`: `classifyLayer`, `computeSlotHealth`,
    `computeBrainTransportHealth`, `computeHarnessHealth`, `shouldEscalate` (R1-R5). Every function
    takes already-parsed ledger record arrays and returns plain objects; none opens a file, spawns a
    process, or reads `process.env` except `DEFAULT_STREAK_THRESHOLD`'s one module-level constant
    (same pattern as `catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC`).
  - `skills/self/self-improve/lib/harness_health.py`: `classify_layer`, `compute_slot_health`,
    `compute_brain_transport_health`, `compute_harness_health`, `should_escalate` (R8) — identical
    contract to the JS twin, proven via a SHARED fixture (below), not shared code.
- **IMPURE (I/O — isolated behind explicit entry points):**
  - `runtime/loop/index.mjs::runOneWake` — the two new append call-sites (R6) reuse the EXISTING
    `appendLedgerLine` (from `ledger.mjs`) against a NEW path
    (`$ANICCA_HOME/state/harness-failures.jsonl`); no new low-level writer is introduced.
  - `runtime/loop/harness-health-snapshot.mjs` (R7) — the ONLY caller of
    `computeHarnessHealth` against real disk state (`readLedgerLines` in, `fs.writeFile` of
    `harness-health.json` out). A CLI script, no long-running process, no scheduling.
  - `skills/self/self-improve/harness_health_report.py` (R8) — the ONLY caller of
    `compute_harness_health` against real disk state on the Python side; reads a ledger path argument,
    prints JSON to stdout.

## Proof table (RED tests to author in Phase 2a)

| Req | Kind | Test (fails until GREEN) |
|---|---|---|
| R1 | unit | each of `{wake,narrate,shutdown}`→`clean`; `wake_error`→`brain_transport`; `skill_missing`→`tool_missing`; `skill_timeout`→`tool_timeout`; `skill_error`→`tool_logic`; an unrecognized `kind` string→`unknown` (never throws) |
| R2 | unit | fixture array with slot `x` records `[wake,wake,skill_error,skill_error]`→`wakes:4,failures:2,failureRate:0.5,consecutiveFailureStreak:2`; a trailing `wake` after failures→streak resets to 0; slot never present→`null`; records with a DIFFERENT slot are excluded from `x`'s count; **a `loop_detect` record carrying `slot:'x'` interspersed among slot-`x` records→excluded entirely from `x`'s `wakes`/`failures`/`consecutiveFailureStreak` (fixture `[wake, {kind:'loop_detect', slot:'x'}, skill_error]` for slot `x`→`wakes:2,failures:1`, NOT `wakes:3`/`failures:2` — proves INV-LOOPDETECT-SEPARATE against FIND-001's live-data hazard, since 238/1063 real `loop_detect` rows carry a matching slot)** |
| R3 | unit | fixture with `wake_error` (no `slot`) interspersed among slot-bearing records→brain-transport counted independently of any slot's `failures`/streak; a `wake_error` immediately followed by a slot's own `skill_error` does NOT inflate that slot's streak |
| R4 | unit | multi-slot fixture→`perSlot` keys match exactly the distinct slots present; empty `records`→`{perSlot:{}, brainTransport:{failures:0,consecutiveFailureStreak:0,...}, generatedAt}`, never throws; every entry carries `escalate` computed via R5 with the passed `streakThreshold` |
| R5 | unit | `consecutiveFailureStreak` one below threshold→`false`; exactly at threshold→`true`; one above→`true` (boundary proof, not just interior cases) |
| R6 | integration (temp `$ANICCA_HOME`) | simulate one `wake_error` wake (THINK throws)→exactly one `harness-failures.jsonl` line, no `slot` key, `layer:'brain_transport'`, `detail` up to 4000 chars; **simulate a `wake_error` wake whose thrown `err.message` contains a 64-hex private-key pattern (`0x[0-9a-fA-F]{64}`)→the corresponding `harness-failures.jsonl` `detail` field shows `[REDACTED]`, not the raw hex (proves R6's new `redactPrivateKeyPatterns(err.message)` call site for the brain_transport branch actually redacts, since FIND-003 established `err.message` is NOT already redacted anywhere upstream)**; simulate one `skill_error` wake (mock skill exits 1 with a >2000-char stdout — **corrected, iteration 3, resolves FIND-007**: a fixture ≤900 chars would never exercise the boundary this proof exists to check, since it would pass identically whether `detail` is correctly capped at 4000 or wrongly capped at 900)→one line with `slot`,`layer:'tool_logic'`,`exit_code`,`detail` LONGER than 900 chars (proving `detail` genuinely preserves diagnostic content beyond `result`'s own 900-char cap, up to its own 4000-char ceiling — the entire reason this file exists) — **and, for the SAME simulated wake, assert `ledger.jsonl`'s own `result` field for it is capped at 900 chars while `harness-failures.jsonl`'s `detail` field for the identical failure is NOT truncated at 900, i.e. the two fields genuinely diverge on this fixture**; **simulate one `skill_error` wake with a >4000-char stdout (e.g. 6000 chars)→assert the appended `harness-failures.jsonl` `detail` field has length EXACTLY 4000 (the mandated ceiling in behavioral-spec.md R6 line 143), proving `detail` is neither left uncapped nor capped at any wrong value ≥2001 — the upper-boundary twin of R5's at/above-threshold proof (line 36); resolves FIND-008, iteration 4**; simulate one clean `wake`→**zero** lines appended to `harness-failures.jsonl`; **assert `ledger.jsonl`'s own `result` field for the SAME wake is still ≤900 chars (corrected, iteration 2, resolves FIND-006 — task #119 already raised this cap from 180 to 900 before this feature's own Phase 1a) and byte-identical in shape to pre-feature output** (regression guard for INV-NO-PROMPT-REGRESSION) |
| R7 | integration (temp dir) | fixture `ledger.jsonl` on disk → running the snapshot script produces `harness-health.json` deep-equal to `computeHarnessHealth` called directly on the same parsed fixture; missing `ledger.jsonl` → writes the R4 empty shape, exit code 0, no throw; re-running overwrites (file size/content reflects only the latest run, no unbounded growth) |
| R8 | unit (python) + cross-language parity | `harness_health.py`'s five functions on the SAME fixture JSON (checked into `tests/fixtures/harness-health-parity.json`, read by BOTH the `.mjs` and `.py` test suites) produce field-for-field identical output to the JS twin; `harness_health_report.py <fixture> --threshold 5` prints valid JSON matching `compute_harness_health(fixture_rows, 5)` |
| R9 | regression | existing `runtime/loop/__tests__/*.test.mjs` suite (esp. `ledger-record.test.mjs`, `integration.test.mjs`, `earn-slot.test.mjs`) stays green unmodified; `skills/earn/self-improve` and `skills/self/self-improve` existing test suites stay green unmodified; `weekly_report.py` has zero diff |
| R10 | static/code-review | `grep -rn "self-fix.sh" runtime/loop/ skills/self/self-improve/` after GREEN returns ZERO matches (proves no new auto-invocation call site was added by this feature) |

## Test file layout (Phase 2a)
- `runtime/loop/__tests__/harness-health.test.mjs` — R1, R2, R3, R4, R5.
- `runtime/loop/__tests__/harness-health-failure-detail.test.mjs` — R6 (extends `index.mjs`'s existing
  temp-`$ANICCA_HOME` integration-test convention already used by `integration.test.mjs`).
- `runtime/loop/__tests__/harness-health-snapshot.test.mjs` — R7.
- `skills/self/self-improve/tests/test_harness_health.py` — R8 (mirrors
  `tests/test_loop_evaluators.py`'s existing style in the same directory).
- `runtime/loop/__tests__/fixtures/harness-health-parity.json` (or a `tests/fixtures/` sibling readable
  from both the `.mjs` and `.py` suites) — the single shared fixture R8's parity assertion reads from
  both languages, so the two implementations are proven identical rather than independently "probably
  right".

## Definition of done = 4-D convergence
spec ✓ (gate PASS) · tests ✓ (R1-R10 green in both languages) · impl ✓ · verification ✓ (fresh-context
adversary PASS on spec AND impl · no Maestro/browser E2E — backend-only, see behavioral-spec.md's E2E
necessity judgment · self-run of `harness-health-snapshot.mjs` against a real/realistic ledger with
output cross-checked against manual `jq`/`grep` counts as fresh evidence).
