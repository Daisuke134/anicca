# Non-blocking observations — iteration 2

These are NOT blocking findings (per the anti-leniency rule, listed here only because they are genuinely
minor/deferrable, not because they are being softened):

1. **REQ-501(b)'s config flag has no concrete name.** Unlike `SOL_GATE_LIVE_ENABLE` (a named env var this
   spec explicitly mirrors), REQ-501 only says "a config flag (default OFF)" without naming it. This is
   reasonable to leave to Phase 2b as long as the eventual name follows the same fail-closed contract — but
   if left unnamed through Phase 2a, two different RED-phase test files could invent two different flag
   names for the same feature. Recommend naming it explicitly (e.g. `ALWAYS_ACT_LIVE_ENABLE`) before Phase
   2a to avoid drift.

2. **REQ-512's "operational action" test-scope wording is slightly confusing but not contradictory on
   closer reading.** §6 Task List item 10 calls the flag-flip "out of this feature's own test scope," while
   REQ-512's own acceptance criteria demands a unit test for "the go-live operational action." The
   consistent reading is: the literal production event (an operator editing a real `.env`/config and
   restarting Franklin's daemon) is out of automated-test scope, but the CODE/script that performs the
   `kind:'always_act_go_live'` ledger append when invoked is in scope and unit-testable. Phase 2a should
   make this split explicit (a small `recordGoLive()`-style function, unit-tested, invoked manually by the
   operator's own one-time command) to avoid ambiguity for whoever implements REQ-512.

3. **PROP-504b's httpPost mocking mechanism (flagged as under-specified after iteration-1) is now adequately
   specified for Phase 2a**, since `brain.mjs::httpPost` is a private, non-exported closure over
   `node:http`/`node:https`, and the Test-Money Safety Rule explicitly names "module-mock at that single
   boundary" as an accepted mechanism (i.e. `vi.mock('node:http')`/`vi.mock('node:https')` intercepting
   `.request()`, rather than function-level dependency injection). This is a real, standard vitest technique
   that requires no further changes to `brain.mjs`'s structure beyond what REQ-504 already specifies. Not
   blocking, but Phase 2a's test author should be pointed at this exact technique rather than attempting to
   refactor `httpPost` into an injectable parameter (which would be an undocumented, out-of-spec change to
   `brain.mjs`'s function signature).

4. **REQ-506's PROP-506a/PROP-506d wording ("array-content assertion, not a bookkeeping flag") is good
   testability discipline** — explicitly reviewed and confirms this dimension is otherwise strong.

5. Ground-truth spot-check coverage performed (11 citations verified against real files, all matched
   byte-for-byte or line-range-accurate): `runtime/loop/index.mjs:382-416,440-456,450,458-475,179-421`,
   `runtime/loop/prompt.mjs:10-24,139-173,171`, `runtime/loop/brain.mjs:63,92`,
   `skills/earn/sol-trade/run.sh:21-24,28-41,38-41,45-48,68-76,105-158,113-116`,
   `skills/self/earning-health.py:12-22`, `skills/registry.json` (11-slot menu + exclusion list), plus
   `runtime/loop/catalog-gate.mjs`, `runtime/loop/earn-slot.mjs`, `runtime/loop/earn-detect.mjs`,
   `runtime/loop/context.mjs`, `skills/_shared/lib/earn-guard.mjs`,
   `skills/earn/sol-trade/lib/resolve-max-spend.sh` read in full for REQ-509 cross-check. Only one citation
   (REQ-504's "invalid enum value is already rejected today" claim) failed verification — see FIND-103.
