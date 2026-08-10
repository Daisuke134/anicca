# CFO-2a2b.3 — Hourly Capture Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and
> superpowers:test-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking. Luna owns production/test edits; Sol owns this plan, review, verification, state, commit, and push.

**Status:** COMPLETE — implementation `7f6424d95`; fresh fix-round review `ship`

**Goal:** Make the existing local one-hour usage runner publish truthful attempt/completion coverage in its immutable
receipt and existing OTel span, including a forced usage-persistence gap as `missing_completion`, never zero cost.

**Architecture:** Extend only `runLocalAgentUsageCollection`, which the existing `cfo-hourly-local.js` main already
invokes before finance. After its current append-only usage batch attempt, re-read the existing normalized chain, read
the adjacent write-ahead attempt JSONL, and call the completed pure
`reconcileLocalAgentUsageCapture(sourceId, attemptRows, usageChain)`. Return two fixed capture envelopes and add only
aggregate integer coverage counts to the same in-process OTel span. Truth remains in the two local append-only ledgers;
OTel transports the derived counts and is not a token oracle or new persistence layer.

**Tech Stack:** Node.js 20 CommonJS, `node:fs`/`node:path`, existing local chain reader, completed pure reconciler,
existing OpenTelemetry API/provider, `node:test`.

## Global Constraints

- Ponytail `full`: reuse the existing runner, chain reader, reconciler, `readFile` seam, and span; no new module,
  dependency, daemon, launchd label, DB/RPC, local span sink, retry, pricing, Telegram report, or cloud path.
- One active item: Luna's implementation diff changes exactly the two production/test files named in Task 1 and
  nothing else. After review, Sol separately updates this plan and the parent/child spec as controller state.
- Implementation soft target: at most 95 added production/test LOC total; controller documentation does not relax this
  limit. Reduce implementation scope before exceeding it.
- Fixed sources and order: `life_manager_agent_usage`, then `anicca_agent_usage`.
- The hourly consumer reads only the canonical adjacent `agent-usage-attempts.jsonl`; the producer's explicit override
  remains a test/owner producer boundary and is not guessed across two sources.
- A nonexistent attempt ledger is an empty capture (`capture_not_started`), not an unreadable failure. Any other read
  failure is `attempt_source_unreadable`; malformed JSON, empty interior row, or non-newline-terminated tail is
  `attempt_source_invalid`; post-publish chain/reconciliation failure is `local_state_failure`.
- No prompt, output, token value, price, path, credential, event ID, exception text, or owner identifier enters the
  public receipt, OTel attributes, logs, stdout, or Telegram.
- The existing finance run remains isolated: usage/capture partial or failure never blocks the truthful Moneytree
  report. This task sends no finance or usage Telegram message.

---

### Task 1: Publish capture receipts through the existing hourly usage runner

**Files:**

- Modify: `apps/life-call/lib/cfo-local-agent-usage-runner.js`
- Test: `apps/life-call/lib/cfo-local-agent-usage-runner.test.js`

**Interfaces:**

- Consumes: `reconcileLocalAgentUsageCapture(sourceId, attemptRows, usageChain)` from
  `./cfo-local-agent-capture-reconciliation.js`.
- Preserves: `runLocalAgentUsageCollection(options = {})`; its existing option keys, usage source order, usage batch
  behavior, failure isolation, one clock read, and one `collect local_agent_usage` INTERNAL span.
- Adds to the frozen runner receipt one exact `capture_sources` array. Each item is exactly:

```json
{"source_id":"life_manager_agent_usage","status":"reconciled","receipt":{"schema_version":1,"source_id":"life_manager_agent_usage","status":"complete","cutover_at":"2026-08-11T01:00:00.000Z","attempted_rows":1,"success_rows":1,"failed_rows":0,"missing_completion_rows":0,"unmatched_completion_rows":0,"duplicate_attempt_rows":0,"conflicting_attempt_rows":0,"ambiguous_completion_rows":0,"coverage_exceptions":[]},"coverage_exceptions":[]}
```

- On a capture input failure, the same envelope is exact with `status="unavailable"`, `receipt=null`, and one fixed
  exception from the Global Constraints. On valid empty attempts it remains `reconciled` and carries the pure empty
  receipt with `coverage_exceptions=["capture_not_started"]`.
- Top-level `coverage_exceptions` is the sorted unique union of existing usage-publication exceptions and every capture
  envelope exception. Top-level `status="complete"` only when both usage sources are published and both pure capture
  receipts are complete; otherwise it is `partial`.
- Adds only these exact aggregate OTel attributes, each a safe integer or fixed status:

```text
cfo.local_agent_usage.capture.status
cfo.local_agent_usage.capture.source.count
cfo.local_agent_usage.capture.reconciled_source.count
cfo.local_agent_usage.capture.attempted.count
cfo.local_agent_usage.capture.success.count
cfo.local_agent_usage.capture.failed.count
cfo.local_agent_usage.capture.missing_completion.count
cfo.local_agent_usage.capture.unmatched_completion.count
cfo.local_agent_usage.capture.duplicate_attempt.count
cfo.local_agent_usage.capture.conflicting_attempt.count
cfo.local_agent_usage.capture.ambiguous_completion.count
cfo.local_agent_usage.capture.coverage_exception.count
```

- If aggregate counts leave the safe-integer range, emit no span. Never add token or cost attributes in this slice.

- [x] **Step 1: Write the failing behavioral test**

Extend the existing runner test with only three compact behaviors:

```js
// normal: both adjacent attempt ledgers + post-write chains reconcile;
// exact frozen capture_sources, top-level complete, and exact aggregate OTel counts.
// forced writeBatch failure: its durable attempt + post-write empty chain yields
// missing_completion_rows=1 and span missing_completion.count=1; no token/cost key exists.
// source boundary table: ENOENT => capture_not_started; malformed/partial =>
// attempt_source_invalid; non-ENOENT throw => attempt_source_unreadable; sentinels never escape.
```

Name the production change that makes each assertion pass. Update old exact receipt/call/span assertions only where the
new required reads and fields make them stale; do not broaden unrelated tests.

- [x] **Step 2: Run RED and record the real failure**

Run:

```bash
cd apps/life-call
node --test lib/cfo-local-agent-usage-runner.test.js
```

Expected: the new assertion fails because `capture_sources` and the capture OTel attributes do not exist. A syntax,
fixture, or missing-dependency error is not RED; fix the test setup until the intended behavior assertion fails.

- [x] **Step 3: Implement the minimum runner change**

Use the existing source usage path to derive the adjacent attempt path. Parse only complete newline-terminated JSONL
rows; pass parsed objects to the pure reconciler, which owns schema validation and immutable receipt construction. Run
the capture pass after existing batch attempts so the second chain read observes any successful publication. Keep
capture failures isolated per source, union their fixed exceptions into the current top-level receipt, derive aggregate
span counts from non-null pure receipts once, and deep-freeze the final result with the existing helper.

- [x] **Step 4: Run GREEN and bounded regression gates**

Run:

```bash
cd apps/life-call
node --test lib/cfo-local-agent-usage-runner.test.js
node --test lib/cfo-local-agent-capture-reconciliation.test.js lib/cfo-local-agent-usage-chain.test.js lib/cfo-local-agent-usage-runner.test.js
npm run test:cfo
npm test
node --check lib/cfo-local-agent-usage-runner.js
node --check lib/cfo-local-agent-usage-runner.test.js
git diff --check
```

Expected: all commands exit 0. Report exact test counts, production/test added LOC, diffstat, and confirm only the two
owned files changed. Do not edit docs, commit, push, launchd, live ledgers, OTel configuration, or Telegram.

- [x] **Step 5: Fresh review and state**

Fresh Sol review checks the exact envelopes, post-write ordering, forced missing-coverage proof, ENOENT distinction,
safe aggregate counts, OTel privacy, existing finance isolation, and Ponytail scope. Luna fixes only load-bearing
findings in the same two implementation files. After the implementation review passes, Sol independently re-runs the
gates, records completion in this plan and the parent/child specs as separate controller documentation, commits/pushes
the complete slice, and advances only to CFO-2a2b.4.

## Completion evidence

- RED: runner 9 tests produced 6 pass / 3 intended failures because `capture_sources` did not exist; no syntax,
  fixture, or dependency error qualified as RED.
- Final implementation: exactly the two named files, 49 additions / 14 deletions total; production added 8 LOC and
  no module, dependency, runner, span store, launchd label, DB, Telegram, or cloud path.
- GREEN: runner 9/9, related reconciliation/chain/runner 18/18, registered CFO suite 300/300, full npm suite 958/958,
  syntax and `git diff --check` pass.
- The forced usage-persistence failure leaves the durable attempt visible as `missing_completion_rows=1` and the same
  OTel aggregate count; no token or cost attribute is emitted.
- Fresh review found one weakened span assertion. Luna restored one exact deep-equality contract containing every
  legacy attribute plus all 12 capture attributes; scoped re-review marked it ADDRESSED with no new breakage.
