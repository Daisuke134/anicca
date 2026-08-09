# Life Manager CFO Moneytree Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan
> task-by-task. Sol owns this plan/spec/review state; only a Luna implementer writes production code, tests, SQL, or
> performs live migration/E2E.

**Goal:** Add bounded Moneytree recovery and append-only snapshot corrections without sending a finance report.

**Architecture:** A pure executor performs at most three reads and proves recovery only through a fresh composed
Moneytree bundle. A single recovery-bundle validator builds truthful `recovered` or `action_required` snapshot facts.
PostgreSQL appends contiguous correction revisions; existing delivery dedupe suppresses repeat alerts.

**Tech Stack:** Node.js 22, `node:test`, PostgreSQL 18, Supabase/PostgREST RPC, Telegram renderer contract.

**Design:** `docs/superpowers/specs/2026-08-09-life-manager-cfo-moneytree-recovery-design.md`.

**Status:** ACTIVE — Task 7b exposed live service-role overgrant; Task 7c hardening next.

## Global Constraints

- One active task: RED → minimum GREEN → focused/full tests → commit/push → fresh Sol review.
- At most three changed files per task. Production over 100 LOC is split unless the plan records an indivisible SQL
  transaction; tests may be larger only when they prove real PostgreSQL concurrency/permissions.
- No incident service/table, queue, scheduler abstraction, browser agent, Steel deployment, Moneytree live failure,
  synthetic live snapshot, delivery claim/receipt, or Telegram finance send.
- At most three reads, two repairs, and waits `1000`, then `5000`; callers cannot override the budget.
- Recovery requires a separate fresh reread plus `composeMoneytreeRead` and daily-report reconciliation.
- Stale/unavailable amounts never enter totals. Errors/logs never expose provider bodies, messages, URLs, UIDs,
  account refs, amounts, credentials, cookies, stacks, or callback values.
- Snapshot rows remain append-only. Revision `N` supersedes exact revision `N-1` for the same owner/date/run.

---

### Task 1: Pure bounded Moneytree recovery executor

**Files (soft target: production <=100 LOC, tests <=240 LOC):**
- Create: `apps/life-call/lib/cfo-moneytree-recovery.js`
- Create: `apps/life-call/lib/cfo-moneytree-recovery.test.js`
- Modify: `apps/life-call/package.json` (`test:cfo` wiring only)

**Interfaces:**
- Consumes: `composeMoneytreeRead`, `buildCfoDailyReport`.
- Produces: `recoverMoneytreeRead({ reportingDate, observedAt }, { read, repair, wait })`.

- [x] **Step 1: Write the closed-contract RED tests**

Cover exact inputs/options, valid calendar date/RFC3339 time, Proxy/accessor/symbol/non-enumerable/custom prototype,
hostile callback values/errors, and the exact frozen result keys. The first happy assertion is:

```js
const result = await recoverMoneytreeRead(
  { reportingDate: "2026-08-09", observedAt: "2026-08-09T08:00:00+09:00" },
  { read: async () => ({ ok: true, moneytreeRead: validRead() }), repair: forbidden, wait: forbidden },
);
assert.equal(result.status, "fresh");
assert.equal(calls.read, 1);
assert.equal(calls.repair, 0);
assert.equal(calls.wait, 0);
assert.equal(result.failureKind, null);
```

- [x] **Step 2: Run RED**

Run: `cd apps/life-call && node --test lib/cfo-moneytree-recovery.test.js`.
Expected: FAIL because `cfo-moneytree-recovery.js` does not exist.

- [x] **Step 3: Add the bounded transition tests**

For each `timeout|network|rate_limited|provider_5xx`, prove repair→wait→fresh reread→composition/reconciliation before
`recovered`. Prove exhausted calls are exactly `reads=3, repairs=2, waits=[1000,5000]`. Prove
`unauthorized|forbidden|expired|revoked` uses one read and no repair/wait, and schema/contract failures become
`provider_outage`. Preserve the first transient kind only when automatic recovery exhausts; a later consent failure
becomes the decisive terminal `failureKind`. `nextRetryAt` must be exactly input `observedAt + 30 minutes`. Every
action is exactly `kind,sourceLabel,retryLabel,nextRetryAt` with the fixed labels from the design.

- [x] **Step 4: Implement minimum GREEN**

Use closed sets and one loop with fixed arrays:

```js
const TRANSIENT = new Set(["timeout", "network", "rate_limited", "provider_5xx"]);
const WAITS = Object.freeze([1000, 5000]);
```

Every successful read is revalidated by `composeMoneytreeRead` and `buildCfoDailyReport`. Deep-freeze a structured
clone. Every thrown error is `cfo_moneytree_recovery_failed:<fixed_code>`; do not log.

- [x] **Step 5: Verify and close**

Run focused test, `npm run test:cfo`, `wc -l` for both files, and `git diff --check`. Commit/push
`feat(cfo): bound Moneytree recovery`; write ignored report; obtain fresh Sol review.

---

### Task 2: Recovery/action snapshot bundle

**Files (soft target: production <=120 LOC, tests <=220 LOC):**
- Create: `apps/life-call/lib/cfo-recovery-snapshot.js`
- Create: `apps/life-call/lib/cfo-recovery-snapshot.test.js`
- Modify: `apps/life-call/package.json` (`test:cfo` wiring only)

**Interfaces:**
- Consumes: Task 1 recovery outcome, `buildCfoDailyReport`, `composeMoneytreeRead`,
  `validateFinancialSourceResult`.
- Produces: `buildCfoDailyReportFromRecovery({ revision, recovery })` and
  `validateCfoRecoverySnapshotBundle({ report, sourceBundle })`.

- [x] **Step 1: Write RED for fresh/recovered/action-required bundles**

Assert an exact frozen `{report,sourceBundle}`. `fresh` equals the existing report facts with requested revision.
`recovered` uses only the fresh reread and exact repair proof. `action_required` uses empty accounts, unavailable
amounts, `evidence:moneytree_unavailable`, exact observed time, and `reconsent|provider_outage` action.
Map source consent from `failureKind` exactly: `unauthorized|expired` to `expired`, `forbidden|revoked` to `revoked`,
and provider-outage actions to `unknown`; the rendered action does not expose `failureKind`.

- [x] **Step 2: Run RED**

Run: `node --test lib/cfo-recovery-snapshot.test.js`; expect missing module failure.

- [x] **Step 3: Add fail-closed truth tests**

Reject stale amount injection, mismatched source/state time, action with net worth, recovered without fresh reread or
reconciliation, revision 0/non-integer, hostile envelopes, unknown keys, caller-mutated output, arbitrary/empty
exclusions, wrong retry labels, fresh reads with unsupported aggregation state, and the real Task 1 action shape.
Also prove a valid zero-balance report remains `0`, `nextRetryAt` is exactly `observedAt + 30 minutes`, and impossible
read/repair/wait histories are rejected for every outcome state.
Catch and replace every error at each public Task 2 boundary; never identify/rethrow a durable tagged Error object
that a caller can mutate and replay through a later hostile input.

- [x] **Step 4: Implement minimum GREEN**

Build all facts once, then call the shared validator before returning. For fresh/recovered reports, rebuild the
canonical existing daily report from `sourceBundle` and require exact deep equality after applying only the requested
revision and reviewed recovered metadata. Require the exact action report and fixed retry label by kind. The
action-required bundle uses:

```js
{
  sourceId: "moneytree_mufg", consent, freshness: "unavailable", asOf: recovery.observedAt,
  accounts: [], liabilities: [], evidenceRef: "evidence:moneytree_unavailable", partial: true, actionRequired
}
```

No old balance or prior report is an input.

- [x] **Step 5: Verify and close**

Run focused test, Task 1+2 tests, `npm run test:cfo`, LOC, and diff-check. Commit/push
`feat(cfo): build recovery snapshot facts`; report; fresh Sol review.

---

### Task 3: Human-readable provider-outage Telegram state

**Files (soft target: production additions <=40 LOC, tests additions <=100 LOC):**
- Modify: `apps/life-call/lib/cfo-telegram.js`
- Modify: `apps/life-call/lib/cfo-telegram.test.js`
- Modify: `apps/life-call/lib/i18n.js`

**Interfaces:**
- Consumes: Task 2 action report with exact action keys `kind,sourceLabel,retryLabel,nextRetryAt`.
- Produces: distinct `reconsent` and `provider_outage` summary copy; existing callback layout unchanged.

- [x] **Step 1: Write RED**

Add provider-outage and reconsent fixtures. Assert outage copy says automatic retry and does not ask reconnection;
reconsent asks one connection update. Both omit net worth, stale amount, raw error, stack, URL, and technical names.

- [x] **Step 2: Run RED**

Run: `node --test lib/cfo-telegram.test.js`; expect action schema/copy failure.

- [x] **Step 3: Implement minimum GREEN**

Allow only the two action kinds, require RFC3339 `nextRetryAt`, add separate Japanese/English string keys, and select
copy by action kind. Do not add a new view, callback type, or transport.

- [x] **Step 4: Verify and close**

Run renderer test, recovery snapshot test, `npm run test:cfo`, LOC delta, diff-check. Commit/push
`feat(cfo): explain bounded recovery state`; report; fresh Sol review.

---

### Task 3b: Suppress action-required financial facts in every Telegram view

**Files (soft target: production additions <=15 LOC, tests additions <=80 LOC):**
- Modify: `apps/life-call/lib/cfo-telegram.js`
- Modify: `apps/life-call/lib/cfo-telegram.test.js`

- [x] **Step 1: Write load-bearing RED**

Build an otherwise valid `action_required` snapshot containing non-null assets, liabilities, change, or source
amounts. Exercise every existing view and prove the renderer rejects the snapshot before rendering any stale amount.
The test must fail against the reviewed implementation and must not pass by checking only the summary shortcut.

- [x] **Step 2: Implement minimum GREEN**

Require every `action_required` total and every source amount to be `null`; keep the exact unavailable source/action
contract. Do not add a view, transport, or replacement financial copy.

- [x] **Step 3: Verify and close**

Run renderer and recovery-snapshot focused tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): suppress stale action-required facts`; write the ignored report; obtain fresh Sol review.

---

### Task 4: Append-only correction migration contract

**Files (soft target: one indivisible SQL <=220 LOC, tests <=180 LOC):**
- Create: `apps/life-call/migrations/2026-08-09-cfo-snapshot-corrections.sql`
- Create: `apps/life-call/lib/cfo-snapshot-correction-migration.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Produces: `lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)` and a forward-compatible
  revision-1 `lm_append_cfo_daily_snapshot`.

- [x] **Step 1: Write static RED**

Assert positive revisions, null predecessor for revision 1, contiguous predecessor for revision N, composite
self-FK, unique owner/date/run/revision, old unique removal, append-only permissions/triggers, fixed search paths,
exact six-key no-UID receipt, and service-role-only RPC grants.
Update `test:cfo` to include `cfo-snapshot-correction-migration.test.js`.

- [x] **Step 2: Run RED**

Run: `node --test lib/cfo-snapshot-correction-migration.test.js`; expect missing SQL failure.

- [x] **Step 3: Implement one forward migration**

Alter only `lm_cfo_daily_snapshots`; preserve all old rows. Replace the legacy RPC selection with `revision=1` so a
later correction cannot make revision-1 retry ambiguous. The new RPC locks revision N-1, checks the same run, inserts
N with `ON CONFLICT DO NOTHING`, accepts an identical retry, and rejects changed facts.

- [x] **Step 4: Verify and close**

Run static test, existing snapshot/daily-run/delivery migration tests, `npm run test:cfo`, SQL/test LOC, diff-check.
Commit/push `feat(cfo): append snapshot corrections`; report; fresh Sol review.

---

### Task 5: Real PostgreSQL correction proof

**Files (soft target: proof <=320 LOC; lifecycle/concurrency makes it indivisible):**
- Create: `apps/life-call/test/postgres/cfo-snapshot-corrections-postgres.integration.sh`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: Task 4 migration and existing daily-run/snapshot migrations.
- Produces: `npm run test:cfo-snapshot-corrections:postgres`.

- [x] **Step 1: Write RED then GREEN on PostgreSQL 18**

Copy only the lifecycle/cleanup pattern from existing CFO PostgreSQL proofs. Apply prerequisite migrations, insert
revision 1, then apply Task 4 migration.

- [x] **Step 2: Prove correction invariants**

Prove revision 2 links revision 1, identical retry returns one row/ref, changed payload/source/predecessor conflicts,
revision gaps and cross-owner/date/run predecessors fail, legacy revision-1 retry stays stable, UPDATE/DELETE and app
roles fail, and two concurrent revision-2 calls create exactly one row.

- [x] **Step 3: Verify and close**

Final stdout exactly `cfo-snapshot-corrections-postgres: PASS`; stderr empty. Run twice, then `npm run test:cfo`,
`npm test`, and diff-check. Commit/push `test(cfo): prove snapshot corrections`; report; fresh Sol review.

---

### Task 6: Strict correction-store client

**Files (soft target: production <=110 LOC, tests <=220 LOC):**
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision-store.js`
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision-store.test.js`
- Modify: `apps/life-call/package.json` (`test:cfo` wiring only)

**Interfaces:**
- Consumes: `validateCfoRecoverySnapshotBundle`, shared `createCfoSupabaseRpc`.
- Produces: `appendCfoDailySnapshotRevision(input, opts)` from the design.

- [x] **Step 1: Write RED**

Assert exact input/options, revision >=2, predecessor=revision-1, complete bundle validation before network, one RPC,
exact body, closed frozen six-key receipt, exact echo, hostile response/error redaction, and no retry/direct table/log.

- [x] **Step 2: Run RED**

Run: `node --test lib/cfo-daily-snapshot-revision-store.test.js`; expect missing module failure.

- [x] **Step 3: Implement minimum GREEN**

Validate with the Task 2 shared validator, call only `lm_append_cfo_daily_snapshot_revision`, and validate the receipt.
Do not rebuild reports, allocate revisions, read tables, or retry.

- [x] **Step 4: Verify and close**

Run focused Task 2+6 tests, `npm run test:cfo`, LOC, diff-check. Commit/push
`feat(cfo): persist snapshot correction revisions`; report; fresh Sol review.

---

### Task 6b: Prevent shared RPC Error replay across public calls

**Files (soft target: production additions <=20 LOC, tests additions <=80 LOC):**
- Modify: `apps/life-call/lib/cfo-supabase-rpc.js`
- Modify: `apps/life-call/lib/cfo-supabase-rpc.test.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot-revision-store.test.js`

- [x] **Step 1: Write load-bearing RED**

Capture a fixed public Error, mutate it, replay that same object through a hostile response getter on a later call,
and prove the later failure is a newly created fixed redacted Error with the module prefix. Observe failure against
the reviewed implementation.

- [x] **Step 2: Implement minimum GREEN**

Internal provenance may distinguish only Errors created during the current public operation. Never recognize or
rethrow an Error retained from an earlier call. Preserve all existing prefixes and validation strictness.

- [x] **Step 3: Verify and close**

Run shared RPC and all three client focused tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): prevent shared rpc error replay`; write the ignored report; obtain fresh Sol review.

---

### Task 6c: Isolate nested and parallel shared-RPC error provenance

**Files (soft target: production delta <=20 LOC, tests delta <=100 LOC):**
- Modify: `apps/life-call/lib/cfo-supabase-rpc.js`
- Modify: `apps/life-call/lib/cfo-supabase-rpc.test.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot-revision-store.test.js`

- [x] **Step 1: Write load-bearing RED**

Reproduce a nested call inside an outer `fetchImpl` and overlapping promises. Replay an Error returned by the inner
public call through the outer response getter. Require a different fixed outer Error, independent concurrent error
reasons, and no ambient provenance after either operation settles. Observe failure against Task 6b.

- [x] **Step 2: Implement minimum GREEN**

Remove ambient operation state that survives or replaces its caller context. Error provenance must be local and
short-lived: exact same-operation propagation works, while settled, nested, and parallel operations cannot recognize
one another's Error identity. Preserve every public prefix and strict validator.

- [x] **Step 3: Verify and close**

Run shared RPC plus all four client tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): isolate shared rpc operation errors`; write the ignored report; obtain fresh Sol review.

---

### Task 6d: Add an explicit shared-RPC public-operation lifecycle

**Files (indivisible boundary change: five production clients/helper, focused tests):**
- Modify: `apps/life-call/lib/cfo-supabase-rpc.js`
- Modify: `apps/life-call/lib/cfo-daily-run.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot-store.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot-revision-store.js`
- Modify: `apps/life-call/lib/cfo-telegram-delivery.js`
- Modify focused shared/client tests as required.

This exceeds the normal three-file soft target because one helper instance cannot infer the lifetime of its four
public async clients. Every consumer must enter and leave the same explicit lifecycle; a partial rollout would leave
an unclosed public boundary.

- [x] **Step 1: Write load-bearing RED**

Add successful nested invocation, failing nested invocation, overlapping success/failure, and post-settlement
cleanup tests. Prove an inner call restores the exact outer same-operation provenance and neither successful nor
failing calls leave an ambient store. Observe failure against Task 6c. Evidence: shared RPC suite RED was 16
passed / 4 failed out of 20; all four failures were the missing `runOperation` lifecycle cases.

- [x] **Step 2: Implement minimum GREEN**

Expose one `runOperation` helper backed by `AsyncLocalStorage.run`, not `enterWith`. Wrap every exported public RPC
operation for daily-run, snapshot-store, correction-store, and Telegram delivery. The lifecycle must restore its
caller across success and failure, sync and async callbacks, nesting and overlap. Remove timer/microtask expiry.
Evidence: focused shared/client suites passed 47/47; no `enterWith`, `queueMicrotask`, `beginOperation`, or
`ensureOperation` remains in the five production files.

- [x] **Step 3: Verify and close**

Run shared RPC plus all four client tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): scope shared rpc public operations`; write the ignored report; obtain fresh Sol review. Evidence before
close: `npm run test:cfo` passed 312/312 and `git diff --check` passed. Commit and push are recorded in the
Task 6d ignored report.

---

### Task 6e: Expire provenance in detached async descendants

**Files (soft target: production delta <=10 LOC, tests delta <=80 LOC):**
- Modify: `apps/life-call/lib/cfo-supabase-rpc.js`
- Modify: `apps/life-call/lib/cfo-supabase-rpc.test.js`

- [ ] **Step 1: Write load-bearing RED**

From both successful and failing `runOperation` callbacks, create detached async descendants that retain the inherited
store. After the parent result settles, prove those descendants cannot recognize the parent's fixed Error. Also
prove a descendant replay through a hostile boundary yields a new fixed local Error. Observe failure against Task 6d.

- [ ] **Step 2: Implement minimum GREEN**

Store `{ errors, open }` per `AsyncLocalStorage.run` scope and close `open` in a `finally` tied to callback settlement.
`internal` requires `open === true`. Context restoration alone is insufficient; no timer or unbounded WeakSet-only
store may keep provenance valid after settlement.

- [ ] **Step 3: Verify and close**

Run shared RPC plus all four client tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): expire rpc error provenance`; write the ignored report; obtain fresh Sol review.

---

### Task 6f: Close provenance when thenable inspection throws

**Files (soft target: production delta <=5 LOC, tests delta <=50 LOC):**
- Modify: `apps/life-call/lib/cfo-supabase-rpc.js`
- Modify: `apps/life-call/lib/cfo-supabase-rpc.test.js`

- [x] **Step 1: Write load-bearing RED**

Return a value with a throwing `then` getter from `runOperation`, while a detached descendant retains its store.
Require the operation to fail, the descendant to see the parent Error as external after settlement, and hostile replay
to yield a different fixed local Error. Observe failure against Task 6e. **Evidence:** the focused run was 4 passed / 1
failed; the failing state was `internal: true`, `replayedIsParent: true`, and the parent error message.

- [x] **Step 2: Implement minimum GREEN**

Place thenable inspection inside the same success/failure cleanup boundary as callback invocation. Every exit from
`runOperation`, including a throwing `then` getter, closes `open`. Preserve sync return behavior for non-thenables.
**Evidence:** the thenable-focused test passed; the minimal change places callback invocation and thenable inspection in
one `try/catch`, retaining the existing async `finally` and synchronous return path.

- [x] **Step 3: Verify and close**

Run shared RPC plus all four client tests, `npm run test:cfo`, `git diff --check`; commit/push
`fix(cfo): close rpc thenable provenance`; write the ignored report; obtain fresh Sol review. **Evidence:** focused
helper plus four client suites passed 50/50, `npm run test:cfo` passed 315/315, `git diff --check` passed, and the
specified commit was pushed to canonical.

---

### Task 7: Live no-write migration proof and CFO-1g3 closure

**Files:**
- Modify tracked parent/design/plan docs only after all evidence passes.
- Create ignored no-echo runner/report in this plan's SDD workspace.

- [ ] **Step 1: Run the full clean matrix**

From `apps/life-call`: `npm ci --no-audit --no-fund`; all new focused tests; `npm run test:cfo`;
`npm run test:cfo-snapshot-corrections:postgres`; `npm test`; `git diff --check`. Record exact counts.

- [ ] **Step 2: Apply the forward migration once**

Use the existing secret-safe Supabase Management API database-query path and one PostgREST schema reload. Print no
URL, token, UID, amount, SQL body, or response body.

- [ ] **Step 3: Verify installed definitions without personal writes**

Read only catalog/privilege metadata. Require corrected revision constraints, self-FK, legacy RPC revision-1 filter,
new correction RPC, service grants, app-role denial, and append-only trigger. Query live snapshot/delivery counts
before/after and require no change. Do not read or print payload values.

Safe stdout is exactly:

```json
{"migrationSuccess":true,"schemaReloadSuccess":true,"installedDefinitionMatches":true,"snapshotRowsCreated":0,"deliveryRowsCreated":0,"telegramCalls":0,"payloadPrivacy":true}
```

- [ ] **Step 4: Final review and closure**

Fresh Sol final review must return no Critical/Important findings. Sol marks `CFO-1g3 COMPLETE — CFO-1h2 NEXT`,
records boolean/count evidence, updates all SSOTs, commits/pushes `docs(cfo): close bounded Moneytree recovery`, and
sends one separate `Codex:::` development milestone with real provider message ID. It must say no finance report was
sent.

---

### Task 7b: Make live proof and exact-once provenance load-bearing

**Files:**
- Modify ignored no-echo runner/evidence/report in this plan's SDD workspace only.
- Modify tracked plan/design status only after review evidence is defined; no production code or SQL changes.

- [ ] **Step 1: Strengthen read-only catalog RED/GREEN**

Without applying SQL or reloading schema, require exact constraint expressions and FK column arrays; unique/index
flags and ordered columns; trigger function, events, timing, and enabled state; complete table/function denial for
all app roles; service grants; and semantic clauses of both revision-1 and correction RPC definitions. Assert a
deliberately weakened fixture fails before running the live read-only check.

- [ ] **Step 2: Bind original exact-once evidence to immutable execution history**

Use the original Luna rollout JSONL as the immutable local transcript. Recover the exact original runner source and
execution call without printing it, record only SHA-256 digests, event identifiers/timestamps, one runner invocation,
one migration-query call, one schema-reload call, and hashes of original stdout/evidence. The final evidence must let
a reviewer locate and independently verify those transcript events locally. Never copy secrets, URLs, SQL, response
bodies, UIDs, or amounts into the evidence.

- [ ] **Step 3: Recheck without effects and review**

Run the strengthened live catalog check read-only. Require zero migration/reload/Telegram calls, zero snapshot and
delivery deltas, payload privacy, and no finance report. Preserve the current 315/315 CFO and 948/948 full matrix.
Obtain fresh Sol review before closure; do not send another milestone.

---

### Task 7c: Forward-harden snapshot service privileges

**Files (one indivisible migration proof slice):**
- Create: `apps/life-call/migrations/2026-08-09-cfo-snapshot-privilege-hardening.sql`
- Create: `apps/life-call/lib/cfo-snapshot-privilege-hardening-migration.test.js`
- Modify: `apps/life-call/test/postgres/cfo-snapshot-corrections-postgres.integration.sh`
- Modify: `apps/life-call/package.json` (`test:cfo` wiring only)

This exceeds the three-file soft target because the forward migration, static contract, real-PostgreSQL proof, and
suite wiring are one security boundary. Splitting them would leave an unproved production privilege mutation.

- [x] **Step 1: Write static and PostgreSQL RED**

Prove the installed Supabase default grants can leave `TRUNCATE`, `REFERENCES`, `TRIGGER`, and `MAINTAIN` on
`service_role`. Require the forward migration to revoke all table privileges from `service_role`, then grant only
`SELECT, INSERT`; app roles and PUBLIC retain none; required RPC EXECUTE and sequence rights remain. Observe RED.

Evidence: static focused RED was `0/1` before the migration existed; PostgreSQL 18 RED was `0/1` after the
test database recreated the default `GRANT ALL` overgrant and the existing correction chain retained all four
additional privileges.

- [x] **Step 2: Implement idempotent minimum GREEN**

Add one metadata-only forward migration. Do not touch rows, functions, constraints, indexes, triggers, policies, or
sequences. Re-running the SQL must converge to the same ACL. No dynamic SQL or new role.

Evidence: `2026-08-09-cfo-snapshot-privilege-hardening.sql` contains only the three table ACL statements; PostgreSQL
18 applied it twice with stderr `0` and proved exact service `SELECT, INSERT` only, all app/Public table privileges
denied, and RPC/sequence rights preserved.

- [x] **Step 3: Prove constraints against isolated catalog and close**

Apply the full tracked migration chain plus hardening in PostgreSQL 18. Compare live constraint definitions to that
isolated catalog representation rather than a source-text parser; do not mutate live constraints unless the isolated
catalog comparison proves a semantic mismatch. Run static/focused/PostgreSQL/CFO/full tests and diff-check. Commit
and push `fix(cfo): harden snapshot service privileges`; obtain fresh Sol review.

Evidence: live-vs-isolated normalized `pg_catalog` constraint names and semantic digest prefixes matched; live
before-vs-after hardening names/digests also matched (`constraintNamesMatch=true`, `constraintBeforeAfterMatch=true`,
`constraintSemanticsMatch=true`). Static focused was `1/1`, PostgreSQL correction proof was PASS/stderr `0`,
`npm run test:cfo` was `316/316`, full `npm test` was `949/949`, and `git diff --check` passed. Commit/push and
fresh Sol review remain the Task 7c handoff actions.

---

### Task 7d: Apply privilege hardening once and re-prove live state

- [ ] Apply only the new forward ACL migration once through the secret-safe Management API path. Do not rerun prior
      migrations, write rows, reload schema, read payloads, or send Telegram.
- [ ] Re-run the semantic catalog checker. Require exact isolated-catalog constraints, exact service table ACL
      `SELECT, INSERT`, required function/sequence grants, complete app-role denial, zero row deltas, and zero
      Telegram calls. Bind execution to transcript/source/output digests as in Task 7b.
- [ ] Obtain fresh Sol final review before closure.

## Completion Boundary

CFO-1g3 is complete only after all seven tasks, live no-write installed-definition proof, full tests, and fresh Sol
review pass. The next visible work remains Telegram integration and the first real Moneytree finance send; 7/7 is not
claimed here.
