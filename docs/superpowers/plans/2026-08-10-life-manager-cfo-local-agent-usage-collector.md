# CFO-2a2a.5a — Local Usage Collector Implementation Plan

Status: COMPLETE

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Compose the canonical cursor, attribution resolver, and reducer into one pure, content-free batch receipt.

**Architecture:** One synchronous function calls each completed module once. Cursor defects remain evidence; a cursor state is returned only after mapping and reduction finish successfully.

**Tech Stack:** Node.js CommonJS, node:test, existing CFO helpers only.

**Working directory:** `apps/life-call`

## Global constraints

- Canonical cursor is only `scanLocalAgentUsageAppend(sourceId, bytes, previousState)`.
- Add only the collector, its test, and one `package.json` suite entry: at most 3 files and 95 added lines.
- Reuse `resolveLocalAgentUsageAttribution`, `reduceLocalAgentUsageEvents`, and shared `freeze`; add no I/O, state writer, DB, RPC, migration, OTel, retry, scheduler, pricing, dependency, or second mapping.
- Preserve source exception names exactly: `source_truncated|source_rewritten|invalid_source_row|partial_tail`.
- Never return prompts, responses, raw rows, paths, accounts, credentials, or dynamic error text.

---

### Task 1: Pure batch collector

**Files:**
- Create: `apps/life-call/lib/cfo-local-agent-usage-collector.js`
- Create: `apps/life-call/lib/cfo-local-agent-usage-collector.test.js`
- Modify: `apps/life-call/package.json` — append the new test to `test:cfo`

**Interfaces:**
- Consumes: `scanLocalAgentUsageAppend(sourceId, bytes, previousState)`
- Consumes: `resolveLocalAgentUsageAttribution(input.loop, input.task_label)`
- Consumes: `reduceLocalAgentUsageEvents([{input, context:{source_row_ref, financial_unit_id}}])`
- Produces: `collectLocalAgentUsageBatch(sourceId, bytes, previousState)`
- Returns exact deeply frozen `{events, source_state, mapping_id, counts, coverage_exceptions}`.
- `mapping_id` is exactly `local_agent_usage_v1`.
- `counts` is the reducer's exact six counts plus `attributed_rows` and `unattributed_rows`; `accepted_rows = attributed_rows + unattributed_rows`.
- `coverage_exceptions` is the unique lexicographic union of cursor and reducer exceptions plus `unattributed_usage` iff `unattributed_rows > 0`.
- Cursor argument errors keep `cfo_local_agent_usage_cursor_invalid:<reason>`; any later unexpected failure throws only `cfo_local_agent_collector_invalid:invalid_batch`.

- [x] **Step 1: Write the failing behavior tests**

Use two valid newline-terminated rows with distinct `event_id` values: one attributed/provider-reported and one unattributed/unavailable. Assert literal public behavior:

```js
const result = collectLocalAgentUsageBatch("life_manager_agent_usage", bytes, null);
assert.deepEqual(Object.keys(result), ["events", "source_state", "mapping_id", "counts", "coverage_exceptions"]);
assert.equal(result.mapping_id, "local_agent_usage_v1");
assert.equal(result.counts.discovered_rows, 2);
assert.equal(result.counts.accepted_rows, 2);
assert.equal(result.counts.attributed_rows, 1);
assert.equal(result.counts.unattributed_rows, 1);
assert.deepEqual(result.coverage_exceptions, ["missing_usage", "unattributed_usage"]);
```

The same test file also proves: canonical event sorting; exact eight count keys; deep freeze through event tokens and source state; no input mutation; unchanged resume returns zero events; each fixed cursor defect passes through unchanged; partial tail may return its preceding valid event; schema-invalid complete rows return `invalid_source_row` with zero events and unchanged state; invalid cursor arguments keep the cursor prefix; serialized receipts/errors contain none of the fixed hostile sentinels.

- [x] **Step 2: Run RED**

Run: `node --test lib/cfo-local-agent-usage-collector.test.js`
Expected: FAIL because `./cfo-local-agent-usage-collector.js` does not exist.

- [x] **Step 3: Implement the minimum composer**

Call the cursor once outside the composition `try`. Map each returned pair once, adding only `financial_unit_id` to its context. Call the reducer once, derive the two attribution counts from accepted events, union/sort fixed exceptions, then freeze the exact receipt. Do not expose `source_state` until those steps complete.

- [x] **Step 4: Run GREEN and gates**

Run:

```bash
node --test lib/cfo-local-agent-usage-collector.test.js
node --test lib/cfo-local-agent-usage-cursor.test.js lib/cfo-local-agent-usage-attribution.test.js lib/cfo-local-agent-usage-collector.test.js
npm run test:cfo
npm test
node --check lib/cfo-local-agent-usage-collector.js
node --check lib/cfo-local-agent-usage-collector.test.js
git diff --check
```

Expected: all exit 0; exactly 3 changed files; implementation plus test at most 95 added lines; lockfile unchanged.

- [x] **Step 5: Real read-only evidence**

Read each actual ledger once, collect from null state, then resume the same fixed Buffer/state. Assert every complete row is accepted exactly once, `accepted_rows = attributed_rows + unattributed_rows`, and the second pass emits zero events. Print counts and fixed exception names only.

- [x] **Step 6: Review and close**

Fresh Sol review checks canonical-module reuse, state ordering, exact counts/exceptions, privacy, and Ponytail scope. Sol reruns the gates and real E2E, updates spec/plan evidence, commits, pushes, and advances to 2a2a.5b.

## Completion evidence

- Missing-old-module RED; canonical collector GREEN with combined focused tests 9/9.
- Scope: collector 22 lines + test 37 lines + one suite entry = 3 files, 60 additions/1 deletion.
- CFO suite 279/279, full `npm test`, syntax, and diff checks exit 0; fresh Sol review `ship`.
- Real read-only E2E: 4,957/4,957 accepted = 3,906 attributed + 1,051 unattributed; unchanged resumes emitted 0.
- Missing usage 273 and runner-ID collision groups 436 remain visible; stdout contained counts and fixed exception names only.
