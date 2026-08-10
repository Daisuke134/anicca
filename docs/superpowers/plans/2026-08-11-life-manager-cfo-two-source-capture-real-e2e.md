# CFO-2a2b.5c2c2 Two-Source Capture Real E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Sol owns plan, review,
> state, commit, push, and real rerun; Luna alone edits the one test file.

**Status:** COMPLETE — commit `eb4a90a53`; fresh Sol review: ship

**Goal:** Replace the obsolete assertion that both real attempt ledgers are absent with a truthful, append-safe E2E
that validates both actual usage/attempt pairs, exact reconciliation, and dynamic OTel attributes.

**Architecture:** Extend the existing real E2E only. Snapshot both usage and attempt files, copy them to its existing
0700 temp root, reuse production reconciliation for each source, derive the exact aggregate receipt, and require the
real sources to remain prefix-immutable. Historical exceptions remain visible; no total-cost or ready claim is added.

**Tech Stack:** Node.js built-ins, existing CFO local usage/reconciliation/span modules, existing real JSONL sources.

## Global constraints

- Ponytail `full`: exactly one existing test file, hard maximum **80 gross added LOC**; no production change, helper
  module, dependency, DB, service, scheduler, retry, repair row, provider call, or Telegram send.
- File: `apps/life-call/test/cfo-local-agent-usage-real-e2e.js` only.
- Never hardcode current row totals. Real ledgers may grow between runs; derive counts from snapshotted bytes.
- Require both usage and attempt files to be regular `0600` complete-line JSONL and preserve both pre-run prefixes.
- `missing_completion_rows` must be `0` for the current snapshot. Other named historical exceptions remain visible.
- No prompt, response, token value, cost value, credential, source path, or row content in stdout or OTel output.
- Luna does not stage, commit, push, mutate real ledgers, or run any provider/launchd/Telegram effect.

---

### Task 1: Make the current real two-source E2E truthful

**Files:**
- Modify/Test: `apps/life-call/test/cfo-local-agent-usage-real-e2e.js`

**Interfaces:**
- Consumes: both real `agent-usage.jsonl` and adjacent `agent-usage-attempts.jsonl` files through the existing
  `SOURCES`/`attemptPath` mapping.
- Produces: one content-free PASS line with dynamic source/capture counts, or the existing fixed FAIL line.

- [x] **Step 1: Retain the current RED**

Run after `npm ci` in `apps/life-call`:

```bash
node test/cfo-local-agent-usage-real-e2e.js
```

Expected: exact `cfo-local-agent-usage-real-e2e: FAIL`, exit `1`, because line 22 still requires both attempt files
absent. Do not weaken the hidden-error/fixed-output behavior.

- [x] **Step 2: Add only the existing reconciliation import and count list**

Import `reconcileLocalAgentCapture` from `../lib/cfo-local-agent-capture-reconciliation.js`. Define the existing eight
capture count keys once:

```js
const CAPTURE_COUNTS = ["attempted_rows", "success_rows", "failed_rows", "missing_completion_rows",
  "unmatched_completion_rows", "duplicate_attempt_rows", "conflicting_attempt_rows", "ambiguous_completion_rows"];
```

- [x] **Step 3: Snapshot and copy both source pairs**

Keep `scan` as the structural complete-line/0600/prefix snapshot. Change `before` to exact per-source pairs:

```js
before = SOURCES.map(source => ({ usage: scan(source), attempts: scan({ real: attemptPath(source) }) }));
```

When building the temp tree, write/chmod both `usage.bytes` and `attempts.bytes` to their matching temp filenames.
Update existing `verifySource` calls to receive `before[i].usage`. Do not read a live source again to calculate the
temp receipt.

- [x] **Step 4: Derive and assert exact capture truth**

After collection, read each temp chain and parse its snapshotted attempt bytes. Reuse production reconciliation:

```js
const chains = SOURCES.map(source => readLocalAgentUsageChain(lmRoot, source.id));
const captures = SOURCES.map((source, i) => reconcileLocalAgentCapture(
  source.id,
  before[i].attempts.bytes.toString("utf8").slice(0, -1).split("\n").map(JSON.parse),
  chains[i],
));
for (let i = 0; i < captures.length; i++) {
  const value = captures[i];
  assert.equal(value.source_id, SOURCES[i].id);
  assert.ok(value.attempted_rows > 0);
  assert.equal(value.missing_completion_rows, 0);
  assert.equal(value.success_rows + value.failed_rows + value.missing_completion_rows, value.attempted_rows);
}
const coverage_exceptions = [...new Set(captures.flatMap(value => value.coverage_exceptions))].sort();
const expectedCapture = {
  status: coverage_exceptions.length ? "partial" : "complete",
  source_count: 2,
  reconciled_source_count: 2,
  ...Object.fromEntries(CAPTURE_COUNTS.map(key => [key, captures.reduce((sum, value) => sum + value[key], 0)])),
  coverage_exceptions,
};
```

Require aggregate `missing_completion_rows === 0`, `receipt.capture_counts` deep-equals `expectedCapture`, and
receipt/top-level exceptions/status match it exactly. Do not require `complete`; current measured truth is partial.

- [x] **Step 5: Make the OTel assertion dynamic and exact**

Build the existing `exact` attribute object from the immutable receipt rather than zero literals:

```js
const c = receipt.capture_counts;
const exact = {
  "cfo.operation.name": "local_agent_usage.collect",
  "cfo.usage.collection.status": receipt.status,
  "cfo.usage.collection.collected_at": AT,
  "cfo.usage.collection.source_count": 2,
  "cfo.usage.collection.coverage_exception_count": receipt.coverage_exceptions.length,
  "cfo.usage.capture.status": c.status,
  "cfo.usage.capture.source_count": 2,
  "cfo.usage.capture.reconciled_source_count": 2,
  "cfo.usage.capture.coverage_exception_count": c.coverage_exceptions.length,
};
if (receipt.coverage_exceptions.length) exact["cfo.usage.collection.coverage_exceptions"] = receipt.coverage_exceptions;
if (c.coverage_exceptions.length) exact["cfo.usage.capture.coverage_exceptions"] = c.coverage_exceptions;
for (const key of CAPTURE_COUNTS) exact[`cfo.usage.capture.${key}`] = c[key];
```

Keep the existing exact published-source attributes. For partial status require span status `ERROR` and exact
`error.type=collection_partial`; for complete status require status `UNSET` and no `error.type`. Keep the existing
content/privacy rejection. Use the SDK's existing numeric contract without another import:

```js
assert.equal(spanRecord.status_code, receipt.status === "partial" ? 2 : 0);
if (receipt.status === "partial") exact["error.type"] = "collection_partial";
```

- [x] **Step 6: Prove both real pairs remain append-only**

In the final real-source reread, apply the existing prefix-size/hash/mode proof independently to both the usage
snapshot and attempt snapshot. Allow concurrent suffix appends; require every original prefix byte unchanged. Remove
only the obsolete absence assertion.

- [x] **Step 7: Emit only dynamic content-free evidence and run gates**

Add one outer `capture` variable beside `totals`, assign it only after every receipt/capture assertion passes, and use
it in the final PASS line. The line keeps its existing source/discovered/accepted/missing/coverage/span fields and
appends dynamic `status/attempted/success/failed/missing_completion` fields from that immutable capture receipt; no
value comes from a hardcoded current total.

Run:

```bash
node test/cfo-local-agent-usage-real-e2e.js
npm run test:cfo
npm test
node --check test/cfo-local-agent-usage-real-e2e.js
git diff --check
```

Expected: real E2E exit `0` with one content-free PASS line; CFO and full suites exit `0`; syntax/diff PASS. Require
exactly one modified file and `<=80` gross additions. Luna reports RED/GREEN, exact counts, scope, and concerns without
staging/commit/push. Fresh Sol then reviews, reruns, commits/pushes, updates specs, and determines the next named
coverage repair; it must not mark capture ready while exceptions remain.

## Completion evidence

- RED: obsolete both-attempt-ledgers-absent assertion exited `1` with the fixed FAIL line.
- GREEN: real E2E observed two sources and reported `attempted=23`, `success=3`, `failed=20`,
  `missing_completion=0`; capture stayed `partial` with six source-scoped chain-exception occurrences.
- Scope: one existing test file, `+11/-9`, no production/runtime/provider/Telegram change.
- Verification: focused real E2E, CFO `302/302`, full suite, syntax, and diff checks all exited `0`.
- Review: fresh Sol found no Critical or Important issue and returned `ship`.
