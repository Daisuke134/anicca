# Connector Connpass Eligibility Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist one privacy-safe Connpass eligibility aggregate per official wake so the next live run proves which gate reduces Connpass candidates to zero.

**Architecture:** Reuse the existing Luma audit boundary without changing provider order, eligibility, browser ownership, or submission behavior. The Connpass workflow computes five monotonic aggregate counts, the existing operations owner validates and appends them to a Connpass-only mode `0600` JSONL file, and the production factory wires the callback.

**Tech Stack:** Node.js CommonJS, `node:test`, append-only JSONL, existing Connector production factory.

## Global Constraints

- Production provider order remains exactly `Luma → Connpass`.
- The acceptance window remains today-inclusive 14 Tokyo calendar days.
- Persist only aggregate integer counts: `observed_count`, `normalized_count`, `window_count`, `free_open_count`, `calendar_free_count`.
- Never persist event URL, event reference, title, provider page text, Calendar content, credential, cookie, profile value, or prompt.
- Audit rows are append-only, mode `0600`, keyed by the current `wake_id`, and use exact ISO timestamps.
- The callback runs once after successful Connpass discovery, including a zero-candidate result; a discovery contract failure keeps its existing exact safe error and does not fabricate an audit.
- Connector Native, healthcheck, and Healer schedules remain unloaded during this task.
- No dependency, service, agent, database, migration, retry, ranking, or new browser target.

---

### Task 1: Persist Connpass gate counts from the official production workflow

**Files:**
- Modify: `apps/mr-bot/lib/connector-connpass-workflow.js`
- Modify: `apps/mr-bot/lib/connector-connpass-workflow.test.js`
- Modify: `apps/mr-bot/lib/connector-minimal-operations.js`
- Modify: `apps/mr-bot/lib/connector-minimal-operations.test.js`
- Modify: `apps/mr-bot/lib/connector-minimal-production.js`
- Modify: `apps/mr-bot/lib/connector-minimal-production.test.js`

**Interfaces:**
- Consumes: `createConnpassScriptFirstWorkflow(options)` and `createMinimalProductionOperations(options)`.
- Produces: `createConnpassScriptFirstWorkflow({ onDiscoveryAudit })`, where the callback receives the exact five-count object below.
- Produces: `operations.recordConnpassDiscoveryAudit(input)`, which validates and appends one row to `connpass-discovery-audits.jsonl`.
- The runner dependency object does not change; audit wiring remains internal to `createMinimalProductionDependencies`.

- [ ] **Step 1: Write the failing Connpass workflow behavior test**

Add a test whose hand-checked fixture contains five valid normalized events: one outside the 14-day window, one paid, one closed, one Calendar-conflicting, and one eligible. Capture `onDiscoveryAudit` calls and assert exactly:

```js
assert.deepEqual(audits, [{
  observed_count: 5,
  normalized_count: 5,
  window_count: 4,
  free_open_count: 2,
  calendar_free_count: 1,
}]);
```

The production change this test catches is removal or mis-ordering of a Connpass eligibility stage from the durable aggregate.

- [ ] **Step 2: Run the workflow test and verify RED**

Run:

```bash
node --test apps/mr-bot/lib/connector-connpass-workflow.test.js
```

Expected: FAIL because `createConnpassScriptFirstWorkflow` does not yet invoke `onDiscoveryAudit`.

- [ ] **Step 3: Implement the minimal Connpass workflow counters**

Validate `options.onDiscoveryAudit` as a function with a no-op default. In `discoverCandidates`, increment counts only after the corresponding existing validation/gate succeeds, then call once:

```js
await onDiscoveryAudit(Object.freeze({
  observed_count: observed.length,
  normalized_count: normalizedCount,
  window_count: windowCount,
  free_open_count: freeOpenCount,
  calendar_free_count: result.length,
}));
```

Do not change eligibility conditions, result ordering, candidate values, or error codes.

- [ ] **Step 4: Run the workflow test and verify GREEN**

Run the Step 2 command. Expected: all tests pass with pristine output.

- [ ] **Step 5: Write the failing operations persistence test**

Create operations, call `recordConnpassDiscoveryAudit` with literal counts `41, 40, 11, 3, 1`, then assert:

```js
assert.deepEqual(Object.keys(row).sort(), [
  "calendar_free_count", "free_open_count", "normalized_count", "observed_count",
  "recorded_at", "schema_version", "wake_id", "window_count",
]);
assert.equal(row.wake_id, "wake-20260810-connpass-discovery");
assert.equal(fs.statSync(file).mode & 0o777, 0o600);
assert.equal(JSON.stringify(row).includes("https://"), false);
```

Use exact file `connpass-discovery-audits.jsonl`. The production break this catches is losing durable gate evidence or leaking event-level data.

- [ ] **Step 6: Run the operations test and verify RED**

Run:

```bash
node --test apps/mr-bot/lib/connector-minimal-operations.test.js
```

Expected: FAIL because `recordConnpassDiscoveryAudit` does not exist.

- [ ] **Step 7: Implement the minimal append-only operations method**

Reuse the existing `safeDiscoveryAudit`, `append`, exact timestamp, and private state directory. Add only:

```js
const connpassDiscoveryAuditFile = path.join(stateDir, "connpass-discovery-audits.jsonl");

async function recordConnpassDiscoveryAudit(input) {
  append(connpassDiscoveryAuditFile, safeDiscoveryAudit(input, wakeId, exactInstant(now())));
}
```

Return it from the frozen operations object. Do not rename or migrate the existing Luma audit file.

- [ ] **Step 8: Run the operations test and verify GREEN**

Run the Step 6 command. Expected: all tests pass with pristine output.

- [ ] **Step 9: Write the failing production wiring test**

Inject an operations object with `recordConnpassDiscoveryAudit`, use the real default provider construction with injected safe dependencies, call `dependencies.discoverCandidates("connpass", [], page)`, and assert the callback receives the exact zero-safe or literal aggregate emitted by the Connpass workflow. Keep the runner dependency key assertion unchanged because this callback is internal production wiring.

The production break this catches is a working workflow callback that is never connected by the official factory.

- [ ] **Step 10: Run the production test and verify RED**

Run:

```bash
node --test apps/mr-bot/lib/connector-minimal-production.test.js
```

Expected: FAIL because the factory does not pass `operations.recordConnpassDiscoveryAudit` into the Connpass workflow.

- [ ] **Step 11: Implement the production callback wiring**

Construct the default Connpass workflow as:

```js
const connpassWorkflow = options.connpassWorkflow || createConnpassScriptFirstWorkflow({
  now,
  onDiscoveryAudit: operations.recordConnpassDiscoveryAudit || (() => {}),
});
```

Do not expose a new runner dependency and do not modify the Luma callback.

- [ ] **Step 12: Run focused and regression GREEN**

Run:

```bash
node --test \
  apps/mr-bot/lib/connector-connpass-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-operations.test.js \
  apps/mr-bot/lib/connector-minimal-production.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

Expected: all tests pass, zero failures, pristine output.

- [ ] **Step 13: Commit implementation**

```bash
git add apps/mr-bot/lib/connector-connpass-workflow.js \
  apps/mr-bot/lib/connector-connpass-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-operations.js \
  apps/mr-bot/lib/connector-minimal-operations.test.js \
  apps/mr-bot/lib/connector-minimal-production.js \
  apps/mr-bot/lib/connector-minimal-production.test.js
git commit -m "feat(connector): persist Connpass eligibility audit"
```

After review, Sol runs the official foreground entrypoint, reads the new Connpass audit row for that exact wake, updates the master SSOT, and pushes.
