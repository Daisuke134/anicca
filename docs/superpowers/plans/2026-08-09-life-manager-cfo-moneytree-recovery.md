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

**Status:** ACTIVE — Task 1 complete; Task 2 next.

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
`provider_outage`. Preserve the original closed `failureKind`; `nextRetryAt` must be exactly input
`observedAt + 30 minutes`.

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

**Interfaces:**
- Consumes: Task 1 recovery outcome, `buildCfoDailyReport`, `composeMoneytreeRead`,
  `validateFinancialSourceResult`.
- Produces: `buildCfoDailyReportFromRecovery({ revision, recovery })` and
  `validateCfoRecoverySnapshotBundle({ report, sourceBundle })`.

- [ ] **Step 1: Write RED for fresh/recovered/action-required bundles**

Assert an exact frozen `{report,sourceBundle}`. `fresh` equals the existing report facts with requested revision.
`recovered` uses only the fresh reread and exact repair proof. `action_required` uses empty accounts, unavailable
amounts, `evidence:moneytree_unavailable`, exact observed time, and `reconsent|provider_outage` action.
Map source consent from `failureKind` exactly: `unauthorized|expired` to `expired`, `forbidden|revoked` to `revoked`,
and provider-outage actions to `unknown`; the rendered action does not expose `failureKind`.

- [ ] **Step 2: Run RED**

Run: `node --test lib/cfo-recovery-snapshot.test.js`; expect missing module failure.

- [ ] **Step 3: Add fail-closed truth tests**

Reject stale amount injection, mismatched source/state time, action with net worth, recovered without fresh reread or
reconciliation, revision 0/non-integer, hostile envelopes, unknown keys, and a caller-mutated output.

- [ ] **Step 4: Implement minimum GREEN**

Build all facts once, then call the shared validator before returning. The action-required bundle uses:

```js
{
  sourceId: "moneytree_mufg", consent, freshness: "unavailable", asOf: recovery.observedAt,
  accounts: [], liabilities: [], evidenceRef: "evidence:moneytree_unavailable", partial: true, actionRequired
}
```

No old balance or prior report is an input.

- [ ] **Step 5: Verify and close**

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

- [ ] **Step 1: Write RED**

Add provider-outage and reconsent fixtures. Assert outage copy says automatic retry and does not ask reconnection;
reconsent asks one connection update. Both omit net worth, stale amount, raw error, stack, URL, and technical names.

- [ ] **Step 2: Run RED**

Run: `node --test lib/cfo-telegram.test.js`; expect action schema/copy failure.

- [ ] **Step 3: Implement minimum GREEN**

Allow only the two action kinds, require RFC3339 `nextRetryAt`, add separate Japanese/English string keys, and select
copy by action kind. Do not add a new view, callback type, or transport.

- [ ] **Step 4: Verify and close**

Run renderer test, recovery snapshot test, `npm run test:cfo`, LOC delta, diff-check. Commit/push
`feat(cfo): explain bounded recovery state`; report; fresh Sol review.

---

### Task 4: Append-only correction migration contract

**Files (soft target: one indivisible SQL <=220 LOC, tests <=180 LOC):**
- Create: `apps/life-call/migrations/2026-08-09-cfo-snapshot-corrections.sql`
- Create: `apps/life-call/lib/cfo-snapshot-correction-migration.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Produces: `lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)` and a forward-compatible
  revision-1 `lm_append_cfo_daily_snapshot`.

- [ ] **Step 1: Write static RED**

Assert positive revisions, null predecessor for revision 1, contiguous predecessor for revision N, composite
self-FK, unique owner/date/run/revision, old unique removal, append-only permissions/triggers, fixed search paths,
exact six-key no-UID receipt, and service-role-only RPC grants.

- [ ] **Step 2: Run RED**

Run: `node --test lib/cfo-snapshot-correction-migration.test.js`; expect missing SQL failure.

- [ ] **Step 3: Implement one forward migration**

Alter only `lm_cfo_daily_snapshots`; preserve all old rows. Replace the legacy RPC selection with `revision=1` so a
later correction cannot make revision-1 retry ambiguous. The new RPC locks revision N-1, checks the same run, inserts
N with `ON CONFLICT DO NOTHING`, accepts an identical retry, and rejects changed facts.

- [ ] **Step 4: Verify and close**

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

- [ ] **Step 1: Write RED then GREEN on PostgreSQL 18**

Copy only the lifecycle/cleanup pattern from existing CFO PostgreSQL proofs. Apply prerequisite migrations, insert
revision 1, then apply Task 4 migration.

- [ ] **Step 2: Prove correction invariants**

Prove revision 2 links revision 1, identical retry returns one row/ref, changed payload/source/predecessor conflicts,
revision gaps and cross-owner/date/run predecessors fail, legacy revision-1 retry stays stable, UPDATE/DELETE and app
roles fail, and two concurrent revision-2 calls create exactly one row.

- [ ] **Step 3: Verify and close**

Final stdout exactly `cfo-snapshot-corrections-postgres: PASS`; stderr empty. Run twice, then `npm run test:cfo`,
`npm test`, and diff-check. Commit/push `test(cfo): prove snapshot corrections`; report; fresh Sol review.

---

### Task 6: Strict correction-store client

**Files (soft target: production <=110 LOC, tests <=220 LOC):**
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision-store.js`
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision-store.test.js`

**Interfaces:**
- Consumes: `validateCfoRecoverySnapshotBundle`, shared `createCfoSupabaseRpc`.
- Produces: `appendCfoDailySnapshotRevision(input, opts)` from the design.

- [ ] **Step 1: Write RED**

Assert exact input/options, revision >=2, predecessor=revision-1, complete bundle validation before network, one RPC,
exact body, closed frozen six-key receipt, exact echo, hostile response/error redaction, and no retry/direct table/log.

- [ ] **Step 2: Run RED**

Run: `node --test lib/cfo-daily-snapshot-revision-store.test.js`; expect missing module failure.

- [ ] **Step 3: Implement minimum GREEN**

Validate with the Task 2 shared validator, call only `lm_append_cfo_daily_snapshot_revision`, and validate the receipt.
Do not rebuild reports, allocate revisions, read tables, or retry.

- [ ] **Step 4: Verify and close**

Run focused Task 2+6 tests, `npm run test:cfo`, LOC, diff-check. Commit/push
`feat(cfo): persist snapshot correction revisions`; report; fresh Sol review.

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

## Completion Boundary

CFO-1g3 is complete only after all seven tasks, live no-write installed-definition proof, full tests, and fresh Sol
review pass. The next visible work remains Telegram integration and the first real Moneytree finance send; 7/7 is not
claimed here.
