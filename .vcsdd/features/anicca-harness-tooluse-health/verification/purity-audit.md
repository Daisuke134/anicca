# Purity Boundary Audit

## Feature: anicca-harness-tooluse-health | Sprint: 1 | Date: 2026-07-10

## Declared Boundaries
Per `specs/verification-architecture.md`'s "Purity boundary (pure core vs. impure shell)" section:

**PURE (deterministic, no I/O — unit-testable in isolation):**
- `runtime/loop/harness-health.mjs`: `classifyLayer`, `computeSlotHealth`, `computeBrainTransportHealth`,
  `computeHarnessHealth`, `shouldEscalate` (R1-R5). Declared: every function takes already-parsed ledger
  record arrays and returns plain objects; none opens a file, spawns a process, or reads `process.env`
  except `DEFAULT_STREAK_THRESHOLD`'s one module-level constant (same pattern as
  `catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC`).
- `skills/self/self-improve/lib/harness_health.py`: `classify_layer`, `compute_slot_health`,
  `compute_brain_transport_health`, `compute_harness_health`, `should_escalate` (R8) — declared identical
  contract to the JS twin, proven via a SHARED fixture, not shared code.

**IMPURE (I/O — isolated behind explicit entry points):**
- `runtime/loop/index.mjs::runOneWake` — the two new append call-sites (R6), reusing the EXISTING
  `appendLedgerLine` against a NEW path (`$ANICCA_HOME/state/harness-failures.jsonl`).
- `runtime/loop/harness-health-snapshot.mjs` (R7) — declared the ONLY caller of `computeHarnessHealth`
  against real disk state.
- `skills/self/self-improve/harness_health_report.py` (R8) — declared the ONLY caller of
  `compute_harness_health` against real disk state on the Python side.

## Observed Boundaries (verified against current code on disk, this session)

### `runtime/loop/harness-health.mjs` — PURE, confirmed
- `grep -n "process\.\|require(\|import \|readFile\|writeFile\|spawn\|fetch\|http" runtime/loop/harness-health.mjs`
  returns only 4 matches, ALL `process.env.HARNESS_HEALTH_STREAK_THRESHOLD` — 3 are comment/doc-string
  references, 1 is the single module-level `DEFAULT_STREAK_THRESHOLD` constant declaration
  (`export const DEFAULT_STREAK_THRESHOLD = Number(process.env.HARNESS_HEALTH_STREAK_THRESHOLD) || 5;`).
  Zero `fs`/`readFile`/`writeFile`/`spawn`/`fetch`/`http` imports or calls anywhere in the file. Every
  exported function (`classifyLayer`, `computeSlotHealth`, `computeBrainTransportHealth`,
  `computeHarnessHealth`, `shouldEscalate`, `capFailureDetail`) takes plain arrays/primitives as
  arguments and returns plain objects/strings/booleans — confirmed by reading the full 204-line file.
  **Matches the declared boundary exactly, including the one documented exception.**

### `skills/self/self-improve/lib/harness_health.py` — PURE, confirmed
- `grep -n "os\.environ\|open(\|subprocess\|requests\|import " skills/self/self-improve/lib/harness_health.py`
  returns 3 matches: `import os`, `import datetime`/`timezone`, and
  `DEFAULT_STREAK_THRESHOLD = int(os.environ.get("HARNESS_HEALTH_STREAK_THRESHOLD") or 0) or 5` — the
  Python twin of the same single documented exception. Zero `open(`/`subprocess`/`requests` calls.
  **Matches the declared boundary exactly.**

### `runtime/loop/harness-health-snapshot.mjs` — IMPURE, confirmed as the sole disk-touching caller
- Imports `node:fs` (`promises as fs`) and `node:path`; reads `ANICCA_HOME` from `process.env`; calls
  `readLedgerLines(LEDGER_PATH)` (existing primitive) and `fs.writeFile(SNAPSHOT_PATH, ...)`. Confirmed
  by full read of the 61-line file: this is the ONLY file in the feature's scope that both reads
  `ledger.jsonl` from disk and calls `computeHarnessHealth` against that real data, then overwrites (not
  appends) `harness-health.json`. Matches R7's "derived VIEW, not an event log" semantics exactly (uses
  `fs.writeFile`, never `appendLedgerLine`/`O_APPEND`, for this path).

### `skills/self/self-improve/harness_health_report.py` — IMPURE, confirmed as the sole Python-side disk caller
- Reads `ledger_path` from `argparse`, calls `load_ledger_rows` (existing `ledger_metrics.py` primitive,
  reused per R8's "never a new/duplicated jsonl loader" requirement — confirmed by the `from
  ledger_metrics import load_ledger_rows` import), calls `compute_harness_health`, prints JSON to stdout.
  No file write — this CLI is read+print only (matches its own docstring: "the ONLY caller of
  compute_harness_health against real disk state on the Python side").

### `runtime/loop/index.mjs` — the two new append call-sites, confirmed isolated
- `classifyLayer` and `capFailureDetail` (both pure) are imported from `harness-health.mjs`; `index.mjs`
  does NOT import `computeHarnessHealth`/`computeSlotHealth`/`computeBrainTransportHealth`/
  `shouldEscalate` at all — it only needs R1's classification and the shared detail-capping helper for
  its own append bookkeeping, never the whole-ledger report. The new `appendHarnessFailure` helper
  (index.mjs:616-632) is a single, shared, effectful function called from exactly 2 sites (the THINK-catch
  `brain_transport` branch at line 370, and the post-dispatch `tool_missing`/`tool_timeout`/`tool_logic`
  branch at line 465) — both routes through the SAME `appendLedgerLine` primitive against the SAME new
  path, no duplicated I/O logic. `redactPrivateKeyPatterns` (imported from the pre-existing
  `env-filter.mjs`, never a new/different redaction implementation) is called once, at the brain_transport
  call-site only, exactly as declared.

## Drift Check
**No drift detected.** Every function/file the spec declares PURE contains zero I/O beyond the one
explicitly documented `process.env`/`os.environ` read (present in both language twins by design, matching
the codebase's pre-existing `catalog-gate.mjs::DEFAULT_BOOTSTRAP_RESERVE_USDC` idiom). Every function/file
the spec declares IMPURE is confirmed to be the sole caller of its corresponding pure aggregator against
real disk state, with no pure function anywhere reaching across the boundary to do its own I/O. No hidden
side effects, no verifier-hostile coupling (e.g. no global mutable state, no pure function silently reading
a closure-captured file handle), and no core/shell inversion (impure code never gets re-imported by a pure
module) were found.

One structural note (non-blocking, documented for completeness): `harness-health.mjs`'s `capFailureDetail`
helper is technically PURE (string-in, string-out, no I/O) but lives in the same file as the R1-R5 pure
aggregators and is consumed by the IMPURE `index.mjs::appendHarnessFailure` — this is architecturally
correct (a pure helper being called FROM impure code is exactly the intended shape; the concern would only
be the reverse) and matches the spec's own description of `capFailureDetail` as "the SAME shared pure step
index.mjs::runOneWake applies identically to BOTH... branches."

## Follow-up before Phase 6
None required. The purity boundary as declared in Phase 1b matches the implementation exactly; no
remediation is needed before proceeding.

## Summary
Declared boundary (2 pure modules/5+5 functions, 3 impure entry points) matches observed implementation
exactly, verified by direct source inspection (grep + full-file read) in this session, not by
re-trusting Phase 2/3 claims. No drift, no hidden side effects, no follow-up required.
