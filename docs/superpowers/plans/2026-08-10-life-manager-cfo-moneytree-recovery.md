# Life Manager CFO-1g3 Moneytree Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Luna implements one task at a time; Sol owns this
> plan, task review, and final review.

**Goal:** Add bounded Moneytree recovery, truthful recovery/action reports, and append-only superseding snapshot
revisions without sending Telegram or creating live owner corrections.

**Architecture:** A pure executor performs one initial read plus at most two safe repair/reread cycles and reuses the
existing Moneytree composition gate. Recovery outcomes feed a separate report-builder entry point. PostgreSQL extends
the immutable snapshot ledger with contiguous revisions and exact predecessor linkage; a strict one-RPC client appends
those revisions. The action-required snapshot stores the future retry time and the existing delivery identity provides
later alert dedupe.

**Tech Stack:** Node.js 20+ CommonJS, `node:test`, PostgreSQL 18, Supabase PostgREST/Management API, built-in `fetch`.

## Global Constraints

- Canonical design: `docs/superpowers/specs/2026-08-09-life-manager-cfo-moneytree-recovery-design.md`.
- Worktree: `/Users/anicca/anicca-project/.worktrees/cfo-m0-business-registry`; branch
  `feature/cfo-moneytree-daily-report`; remote `canonical`; push with `git push canonical HEAD`.
- One active task. Each task closes RED → minimum GREEN → focused tests → `npm run test:cfo` →
  `git diff --check` → focused stage → commit → push → fresh task review.
- Never stage another session's files. Re-read `git status` immediately before every stage.
- Maximum three changed files per task. Production files target ≤130 LOC and tests target ≤220 LOC; split instead of
  adding an abstraction when exceeded.
- No new dependency, scheduled Moneytree credential, generic incident service, queue, scheduler mutation, sleep in
  production, Steel/browser fallback, launchctl change, or direct table REST write.
- No real Moneytree failure, live owner correction, live alert/delivery claim, Telegram call, transfer, trade,
  withdrawal, payment, publication, or other financial write.
- Inputs/options/receipts are closed plain objects. Proxies, accessors, symbols, non-enumerable keys, custom
  prototypes, cycles, changing getters, and unexpected fields fail closed before effects.
- Errors and reports never expose UID, amount, account ref/number, raw provider body, URL, credential, callback error,
  stack, cookie, or token. Fixed errors only.
- Unknown/stale/unavailable values never become zero, `complete`, or `recovered`.
- Final live stdout contains only named booleans/counts. No URL, SQL, response, UID, snapshot ref, run ID, source
  payload, amount, or secret.

---

### Task 1: Pure bounded Moneytree recovery executor

**Files:**
- Create: `apps/life-call/lib/cfo-moneytree-recovery.js`
- Create: `apps/life-call/lib/cfo-moneytree-recovery.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: `composeMoneytreeRead({source,state})` from `cfo-moneytree-state.js`.
- Produces: `recoverMoneytreeRead({reportingDate,observedAt}, {read,repair,wait})`.

- [ ] **Step 1: Add exact failing executor tests and wire them into `test:cfo`**

Create tests with synthetic closed Moneytree bundles only. The load-bearing cases are:

```js
test("first fresh read returns fresh with one read and no repair or wait", async () => {
  const calls = [];
  const outcome = await recoverMoneytreeRead(INPUT, effects({
    read: async () => { calls.push("read"); return { ok: true, moneytreeRead: validRead() }; },
  }));
  assert.equal(outcome.status, "fresh");
  assert.deepEqual(calls, ["read"]);
  assert.equal(outcome.attempts, 1);
  assert.equal(outcome.repair, null);
  assert.equal(outcome.action, null);
});

test("repair callback success cannot recover without a separate fresh reconciled reread", async () => {
  const reads = [
    { ok: false, kind: "timeout" },
    { ok: true, moneytreeRead: staleOrActionRequiredRead() },
    { ok: true, moneytreeRead: validRead() },
  ];
  const outcome = await recoverMoneytreeRead(INPUT, effects({ read: async () => reads.shift() }));
  assert.equal(outcome.status, "recovered");
  assert.equal(outcome.attempts, 3);
  assert.deepEqual(outcome.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
});
```

Also assert all four transient classes; immediate `reconsent` for `unauthorized|forbidden|expired|revoked`; fixed
waits exactly `[1000,5000]`; maximum calls `read=3,repair=2,wait=2`; contract failure maps to `provider_outage`;
`nextRetryAt` equals input `observedAt + 30 minutes`; exact output keys; deep freeze; no logging; hostile inputs,
callbacks, throws, promises, and return shapes fail with `^cfo_moneytree_recovery_failed:[a-z0-9_]+$` and leak none
of the sentinel strings.

- [ ] **Step 2: Run RED and record the expected missing-module failure**

Run:

```bash
cd apps/life-call
node --test lib/cfo-moneytree-recovery.test.js
```

Expected: non-zero with `Cannot find module './cfo-moneytree-recovery.js'`. A syntax/fixture failure is not accepted
as RED.

- [ ] **Step 3: Implement the minimum closed executor**

The implementation begins with these closed constants and public shape:

```js
const TRANSIENT = new Set(["timeout", "network", "rate_limited", "provider_5xx"]);
const RECONSENT = new Set(["unauthorized", "forbidden", "expired", "revoked"]);
const WAITS_MS = Object.freeze([1000, 5000]);

async function recoverMoneytreeRead(input, options) {
  // exact/plain validation before callback reads
  // initial read; then at most two repair -> wait -> fresh read cycles
  // composeMoneytreeRead revalidation after every successful read
  // action_required.nextRetryAt = observedAt + 30 minutes
  // structuredClone + deep freeze before return
}

module.exports = { recoverMoneytreeRead };
```

`attempts` counts provider reads, so it is `1..3`. `repair({kind,attempt})` receives attempt `1` or `2`. `wait`
occurs after a truthy repair and before the corresponding fresh reread. A false repair result continues toward the
same bounded action-required result without treating repair as evidence. The executor catches all callback errors and
never interpolates them.

- [ ] **Step 4: Run focused GREEN and mutation-prove the recovery test**

Run focused test and require 0 failures. Then temporarily bypass the post-repair `composeMoneytreeRead` call; the
test named “repair callback success cannot recover…” must fail. Restore production code and rerun to PASS.

- [ ] **Step 5: Verify, commit, and push Task 1 only**

```bash
cd apps/life-call
node --test lib/cfo-moneytree-recovery.test.js
npm run test:cfo
git diff --check
cd ../..
git status --short
git add apps/life-call/lib/cfo-moneytree-recovery.js \
        apps/life-call/lib/cfo-moneytree-recovery.test.js \
        apps/life-call/package.json
git commit -m "feat(cfo): bound Moneytree recovery"
git push canonical HEAD
```

---

### Task 2: Recovery-aware daily report builder

**Files:**
- Modify: `apps/life-call/lib/cfo-daily-snapshot.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot.test.js`

**Interfaces:**
- Consumes: Task 1's exact recovery outcome.
- Produces: `buildCfoDailyReportFromRecovery({revision,recovery})` while preserving `buildCfoDailyReport`.

- [ ] **Step 1: Add failing report tests**

Add exact cases:

```js
test("recovered report uses only the fresh reread and preserves partial liabilities", () => {
  const report = buildCfoDailyReportFromRecovery({ revision: 2, recovery: recoveredOutcome() });
  assert.equal(report.revision, 2);
  assert.equal(report.state, "recovered");
  assert.equal(report.totals.assetsMinor, FRESH_TOTAL);
  assert.equal(report.totals.netWorthMinor, null);
  assert.deepEqual(report.repair, { sourceLabel: "Moneytree", freshReread: true, reconciled: true });
  assert.equal(report.action, null);
});

test("action-required report carries no stale amount and persists retry due time", () => {
  const report = buildCfoDailyReportFromRecovery({ revision: 1, recovery: actionOutcome() });
  assert.deepEqual(report.totals, { assetsMinor: null, liabilitiesMinor: null, netWorthMinor: null, changeMinor: null });
  assert.equal(report.sources[0].amountMinor, null);
  assert.equal(report.action.nextRetryAt, NEXT_RETRY_AT);
});
```

Also assert fresh parity with existing builder; exact input/outcome keys; revision positive safe integer; recovered
requires fresh reread and reconciliation; action source is unavailable with no accounts and
`evidence:moneytree_unavailable`; error prefix remains `cfo_daily_snapshot_invalid:`; output is cloned/frozen and
contains no callback/provider/private fields.

- [ ] **Step 2: Run RED**

Run `node --test lib/cfo-daily-snapshot.test.js`; expected failure is
`buildCfoDailyReportFromRecovery is not a function`.

- [ ] **Step 3: Implement the second builder entry point**

Use this signature and reuse the existing report assembly rather than copying amount arithmetic:

```js
function buildCfoDailyReportFromRecovery(input) {
  // exact {revision,recovery}; revalidate the outcome
  // fresh/recovered: build from recovery.moneytreeRead, then replace revision/state/repair
  // action_required: construct a closed unavailable Moneytree read/report with all totals null
}

module.exports = { buildCfoDailyReport, buildCfoDailyReportFromRecovery };
```

Do not broaden `buildCfoDailyReport({reportingDate,moneytreeRead})`; revision-1 callers remain unchanged.

- [ ] **Step 4: Run GREEN and all snapshot tests**

Run `node --test lib/cfo-daily-snapshot.test.js lib/cfo-moneytree-recovery.test.js`; require 0 failures.

- [ ] **Step 5: Verify, commit, and push Task 2 only**

Run `npm run test:cfo` and `git diff --check`, stage only the two files, commit
`feat(cfo): build recovery snapshots`, and `git push canonical HEAD`.

---

### Task 3: Action-required Telegram rendering contract

**Files:**
- Modify: `apps/life-call/lib/cfo-telegram.js`
- Modify: `apps/life-call/lib/cfo-telegram.test.js`

**Interfaces:**
- Consumes: Task 2 report action `{kind,sourceLabel,retryLabel,nextRetryAt}`.
- Produces: Japanese/English `reconsent` and `provider_outage` copy; no send side effect.

- [ ] **Step 1: Add failing renderer tests**

```js
test("provider outage tells the owner about automatic retry without blame or diagnostics", () => {
  const snapshot = actionRequiredSnapshot({ kind: "provider_outage", nextRetryAt: "2026-08-09T06:30:00Z" });
  const text = renderCfoTelegram({ locale: "ja", view: "summary", snapshot }).text;
  assert.match(text, /自動.*再確認|再試行/);
  assert.doesNotMatch(text, /接続更新.*お願い|stack|error|exception|503/i);
});
```

Assert reconsent asks for one connection update; both locales; exact four action keys; valid RFC3339 retry time;
null totals/no stale amount; provider outage and reconsent are the only action kinds; action copy remains escaped;
existing complete/partial/recovered/drill-down tests remain unchanged.

- [ ] **Step 2: Run RED**

Run `node --test lib/cfo-telegram.test.js`; expected failure is current `invalid_action` or unexpected action-key
rejection for the provider-outage fixture.

- [ ] **Step 3: Implement the closed action schema and copy**

Change only the action validation/render branches:

```js
const ACTION_KEYS = new Set(["kind", "sourceLabel", "retryLabel", "nextRetryAt"]);
const ACTION_KINDS = new Set(["reconsent", "provider_outage"]);
```

Validate RFC3339 with the same strict offset bounds used by the CFO RPC validator or one local equivalent. Render
plain-language owner action; never print the raw timestamp if the locale formatter cannot validate it.

- [ ] **Step 4: Run GREEN and CFO suite**

Run `node --test lib/cfo-telegram.test.js lib/cfo-daily-snapshot.test.js` and `npm run test:cfo`; all exit 0.

- [ ] **Step 5: Commit and push Task 3 only**

Run `git diff --check`, stage the two files, commit `feat(cfo): render recovery actions`, push canonical.

---

### Task 4: Append-only correction migration contract

**Files:**
- Create: `apps/life-call/migrations/2026-08-10-cfo-daily-snapshot-revisions.sql`
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision-migration.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: existing `lm_cfo_daily_snapshots`, `lm_cfo_daily_runs`, and revision-1 append RPC.
- Produces: `lm_append_cfo_daily_snapshot_revision(text,date,uuid,integer,integer,jsonb,jsonb)`.

- [ ] **Step 1: Add failing static migration contract tests**

Tests must assert actual SQL structure, including:

```js
assert.match(sql, /drop constraint\s+lm_cfo_daily_snapshots_revision_check/i);
assert.match(sql, /check\s*\(revision\s*>\s*0\)/i);
assert.match(sql, /foreign key\s*\(uid,\s*reporting_date,\s*run_id,\s*supersedes_revision\)/i);
assert.match(sql, /on conflict\s+do nothing/i);
assert.match(sql, /correction_conflict/i);
```

Also require: revision-1 supersedes null; revision N supersedes N-1; unique owner/date/revision and
owner/date/run/revision; exact six-key receipt; same payload/source retry; changed payload/source conflict;
predecessor lock; no UID/payload/source bundle in receipt; append-only trigger remains; service-role-only execution;
fixed search path; original revision-1 RPC not replaced.

- [ ] **Step 2: Run RED**

Run `node --test lib/cfo-daily-snapshot-revision-migration.test.js`; expected missing migration file failure.

- [ ] **Step 3: Write the additive/forward SQL migration**

The RPC shape is fixed:

```sql
CREATE OR REPLACE FUNCTION public.lm_append_cfo_daily_snapshot_revision(
  p_uid text, p_reporting_date date, p_run_id uuid,
  p_revision integer, p_supersedes_revision integer,
  p_report_payload jsonb, p_source_bundle jsonb
) RETURNS jsonb
```

Validate revision ≥2 and predecessor = revision-1, lock the predecessor `FOR UPDATE`, insert one row, then on
conflict read the same identity and compare report/source/supersedes exactly. Return only
`public_ref,reporting_date,run_id,revision,supersedes_revision,created_at`.

- [ ] **Step 4: Run GREEN and migration regressions**

Run the new static test plus `cfo-daily-snapshot-migration.test.js`, `cfo-daily-run-migration.test.js`, and
`cfo-telegram-delivery-migration.test.js`; all exit 0.

- [ ] **Step 5: Verify, commit, and push Task 4 only**

Run `npm run test:cfo`, `git diff --check`, stage exactly three files, commit
`feat(cfo): add immutable snapshot corrections`, and push canonical.

---

### Task 5: Real PostgreSQL correction proof

**Files:**
- Create: `apps/life-call/test/postgres/cfo-recovery-corrections-postgres.integration.sh`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: all CFO snapshot/run/delivery migrations plus Task 4 migration.
- Produces: npm script `test:cfo-recovery-corrections:postgres`.

- [ ] **Step 1: Create the PostgreSQL proof with one intentionally failing assertion**

Copy only lifecycle/cleanup/role fixture patterns from `cfo-reliable-run-postgres.integration.sh`. First prove the
new migration is absent by asserting revision 2 insertion succeeds before applying it; run and observe non-zero.
Then restore correct order and keep all assertions listed below.

- [ ] **Step 2: Prove schema, permissions, and correction semantics**

The script must prove:

```bash
# logical assertions, implemented with psql/jq and fail():
# revision 1 survives migration unchanged and existing append retry still matches
# revision 2 -> revision 1, revision 3 -> revision 2
# gap, wrong predecessor, wrong owner/date/run, zero UUID, malformed report/source all fail
# identical revision retry returns exact same six-key receipt
# changed report or source conflicts
# two concurrent revision-2 RPCs create one row and same receipt
# UPDATE/DELETE and anon/authenticated/PUBLIC access fail
# delivery FK accepts revision 2 exact snapshot and rejects cross identity
```

Use `PGOPTIONS='-c client_min_messages=warning'` for every psql path. Capture background stderr separately and require
empty files. Final stdout line is exactly `cfo-repair-corrections-postgres: PASS`.

- [ ] **Step 3: Run RED then GREEN with exact stdout proof**

```bash
npm run test:cfo-recovery-corrections:postgres
npm run test:cfo-recovery-corrections:postgres 2>/dev/null | tail -1
```

The second command must output only `cfo-repair-corrections-postgres: PASS`; assertions must not be skipped.

- [ ] **Step 4: Run sibling PostgreSQL and CFO regressions**

Run `npm run test:cfo-reliable-run:postgres`, `npm run test:cfo`, and `git diff --check`; all exit 0.

- [ ] **Step 5: Commit and push Task 5 only**

Stage the script and package file, commit `test(cfo): prove immutable snapshot corrections`, push canonical.

---

### Task 6: Strict snapshot-revision PostgREST client

**Files:**
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision.js`
- Create: `apps/life-call/lib/cfo-daily-snapshot-revision.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: Task 4 RPC and shared `createCfoSupabaseRpc` helpers.
- Produces: `appendCfoDailySnapshotRevision(input, opts)`.

- [ ] **Step 1: Add failing one-RPC client tests**

```js
test("appends one exact corrected revision RPC and freezes the echoed receipt", async () => {
  const calls = [];
  const receipt = await appendCfoDailySnapshotRevision(validInput(), opts(async (url, init) => {
    calls.push({ url, init });
    return response(RECEIPT);
  }));
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, /\/rpc\/lm_append_cfo_daily_snapshot_revision$/);
  assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body)).sort(), [
    "p_report_payload", "p_reporting_date", "p_revision", "p_run_id",
    "p_source_bundle", "p_supersedes_revision", "p_uid",
  ]);
  assert.equal(Object.isFrozen(receipt), true);
});
```

Also prove exact input and six-key receipt; revision ≥2 and predecessor equality; full report/source validation;
exact date/run/revision/predecessor echo; built-in fetch default; unknown options and hostile objects rejected before
network; one call only; non-2xx body never read; no retry/log/direct table path; fixed redacted errors.

- [ ] **Step 2: Run RED**

Run `node --test lib/cfo-daily-snapshot-revision.test.js`; expected missing-module failure.

- [ ] **Step 3: Implement by composing the shared RPC validator**

```js
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");

async function appendCfoDailySnapshotRevision(input, opts = {}) {
  // exact input/options; validate report/source before postRpc
  // one postRpc("lm_append_cfo_daily_snapshot_revision", exactPayload)
  // validate exact echo; structuredClone + deep freeze
}

module.exports = { appendCfoDailySnapshotRevision };
```

Do not duplicate `postRpc`, timestamp, UUID, date, deep-freeze, or option-schema behavior.

- [ ] **Step 4: Mutation-prove receipt echo checks and run GREEN**

Temporarily remove the `supersedes_revision` echo comparison; its mismatch test must fail. Restore and rerun focused
test to PASS. Then run `npm run test:cfo`.

- [ ] **Step 5: Commit and push Task 6 only**

Run `git diff --check`, stage exactly three files, commit `feat(cfo): persist corrected snapshots`, push canonical.

---

### Task 7: Live migration, no-write E2E, and CFO-1g3 closure

**Files:**
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`
- Modify: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md`
- Modify: `docs/superpowers/specs/2026-08-09-life-manager-cfo-moneytree-recovery-design.md`

**Interfaces:**
- Consumes: Tasks 1-6 and private env `SUPABASE_ACCESS_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
- Produces: installed live schema proof and `CFO-1g3 COMPLETE — CFO-1h2 NEXT` SSOT state.

- [ ] **Step 1: Run the complete local verification matrix**

From `apps/life-call` run:

```bash
npm ci --no-audit --no-fund
node --test lib/cfo-moneytree-recovery.test.js lib/cfo-daily-snapshot.test.js \
  lib/cfo-telegram.test.js lib/cfo-daily-snapshot-revision-migration.test.js \
  lib/cfo-daily-snapshot-revision.test.js
npm run test:cfo
npm run test:cfo-reliable-run:postgres
npm run test:cfo-recovery-corrections:postgres
npm test
git diff --check
```

Every command exits 0. Record counts only; no private fixture values.

- [ ] **Step 2: Create an ignored no-echo live runner**

Use the plan workspace path `.superpowers/sdd/2026-08-10-life-manager-cfo-moneytree-recovery/live-close.js`.
It reads the migration file, derives the project ref from `SUPABASE_URL`, calls the Management API database-query
endpoint once, runs `NOTIFY pgrst, 'reload schema'`, and performs catalog/privilege checks only. It must not call any
Moneytree, snapshot append/revision, delivery, Telegram, or direct table mutation endpoint.

- [ ] **Step 3: Apply migration and run no-write live proof**

The runner stdout is one exact JSON object:

```json
{
  "migrationSuccess": true,
  "schemaReloadSuccess": true,
  "recoverySchemaInstalled": true,
  "correctionSchemaInstalled": true,
  "privilegesClosed": true,
  "liveCorrectionsCreated": 0,
  "liveDeliveryRowsCreated": 0,
  "payloadPrivacy": true
}
```

Before/after counts are read privately and compared; only zero deltas print. HTTP body, SQL, URL, identifiers, and
credentials never print. A migration failure stops with one fixed redacted stderr line.

- [ ] **Step 4: Obtain fresh final Sol review**

Generate a whole-slice review package from the commit before Task 1 to HEAD. Review spec compliance, task quality,
TDD evidence, PostgreSQL concurrency, installed live schema, no-write boundary, privacy, and deferred CFO-1h send.
Critical and Important findings enter one Luna fix wave followed by one scoped re-review.

- [ ] **Step 5: Update SSOTs, commit, push, and close**

Mark CFO-1g3 complete only after Step 4 is clean. Record exact local counts and the eight live booleans/counts; do not
record private values. Set next item to CFO-1h2. Then:

```bash
git diff --check
git add docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md \
        docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md \
        docs/superpowers/specs/2026-08-09-life-manager-cfo-moneytree-recovery-design.md
git commit -m "docs(cfo): close bounded Moneytree recovery"
git push canonical HEAD
git status --short --branch
```

Final worktree status is clean and branch equals `canonical/feature/cfo-moneytree-daily-report`.

