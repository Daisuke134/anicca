# Life Manager CFO Immutable Daily Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and persist one truthful, immutable, idempotent native-JPY Moneytree daily snapshot.

**Architecture:** A pure builder converts the existing closed Moneytree bundle into the exact existing Telegram
snapshot shape. A PostgreSQL append-only table and RPC own concurrency and retry identity. A small REST client builds
and appends the record without logging financial payloads.

**Tech Stack:** Node.js 20+, CommonJS, `node:test`, PostgreSQL/Supabase, built-in `fetch`; no new dependency.

**Status:** ACTIVE — Task 1 next.

## Global Constraints

- Design SSOT: `docs/superpowers/specs/2026-08-09-life-manager-cfo-daily-snapshot-design.md`.
- Parent SSOT: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`; only CFO-1g is active.
- Sol owns specs/plans/state. Luna alone writes production code, tests, SQL, and executes live migration/E2E.
- Native Moneytree JPY only. No FX, Fleet amount, Binance, business P&L, tax, scheduler, or Telegram send.
- Unknown liabilities, prior-day change, and net worth remain `null`; report state stays `partial`.
- Never print/store raw Moneytree JSON, provider/account IDs, UID, chat ID, credentials, response bodies, or live
  amount in implementation reports. Only the private user chat may display the amount.
- Each task changes at most three files. Production above 100 LOC or more than three files requires another slice.
- Each task closes RED, GREEN, fresh task review, commit, and push before the next task.

---

### Task 1: Pure Native-JPY Report Builder

**Files:**
- Create: `apps/life-call/lib/cfo-daily-snapshot.js`
- Create: `apps/life-call/lib/cfo-daily-snapshot.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: `composeMoneytreeRead({ source, state })` from `cfo-moneytree-state.js`.
- Produces: `buildCfoDailyReport({ reportingDate, moneytreeRead }) => deeplyFrozenReport`.

- [ ] **Step 1: Write RED contract tests**

Build only synthetic Moneytree bundles through the existing validators. Test:

```js
const report = buildCfoDailyReport({ reportingDate: "2026-08-09", moneytreeRead });
assert.deepEqual(report.totals, {
  assetsMinor: 336594,
  liabilitiesMinor: null,
  netWorthMinor: null,
  changeMinor: null,
});
assert.equal(report.state, "partial");
assert.deepEqual(report.excluded, [{ label: "負債", reason: "Moneytreeの接続範囲が不明" }]);
assert.doesNotThrow(() => renderCfoTelegram({ locale: "ja", view: "summary", snapshot: report }));
```

Also prove exact root/source keys, revision 1, JPY only, provider-reported status, no Fleet fields, safe-integer sum
overflow rejection, invalid date rejection, unavailable/stale/complete-liability bundle rejection, clone/deep-freeze,
input mutation isolation, Proxy/accessor/custom-prototype/cycle/unknown-key rejection inherited through revalidation,
and no account number/raw/secret-shaped key in serialized output.

- [ ] **Step 2: Run focused RED**

```bash
cd apps/life-call
node --test lib/cfo-daily-snapshot.test.js
```

Expected: FAIL only because `cfo-daily-snapshot.js` or `buildCfoDailyReport` does not exist.

- [ ] **Step 3: Implement the minimum builder**

Implementation shape:

```js
"use strict";
const { composeMoneytreeRead } = require("./cfo-moneytree-state.js");

function buildCfoDailyReport(input) {
  // Require exact input keys and a valid YYYY-MM-DD.
  // Revalidate once: composeMoneytreeRead({ source, state }).
  // Require successful/valid/partial Moneytree JPY evidence with unknown liabilities.
  // Sum provider-reported accounts with Number.isSafeInteger after every addition.
  // Construct the exact design §3 report, structuredClone it, recursively freeze it, return it.
}

module.exports = { buildCfoDailyReport };
```

Do not create a generic currency engine, snapshot class, schema library, or shared validator refactor.

- [ ] **Step 4: Register and prove GREEN**

Append `lib/cfo-daily-snapshot.test.js` exactly once to `test:cfo`, then run:

```bash
cd apps/life-call
node --test lib/cfo-daily-snapshot.test.js
npm run test:cfo
wc -l lib/cfo-daily-snapshot.js lib/cfo-daily-snapshot.test.js
git diff --check
```

Expected: all pass; production ≤100 LOC, tests ≤200 LOC, diff clean.

- [ ] **Step 5: Commit and push**

```bash
git add apps/life-call/lib/cfo-daily-snapshot.js apps/life-call/lib/cfo-daily-snapshot.test.js apps/life-call/package.json
git commit -m "feat(cfo): build partial daily snapshot"
git push canonical HEAD
```

Write the RED/GREEN commands, counts, LOC, commit, and privacy scan to the task report.

---

### Task 2: Append-Only Snapshot SQL Contract

**Files:**
- Create: `apps/life-call/migrations/2026-08-09-cfo-daily-snapshots.sql`
- Create: `apps/life-call/lib/cfo-daily-snapshot-migration.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Produces table `public.lm_cfo_daily_snapshots`.
- Produces RPC `public.lm_append_cfo_daily_snapshot(text,date,uuid,jsonb,jsonb) => jsonb`.

- [ ] **Step 1: Write the RED migration test**

Read the SQL fixture and assert it contains:

```js
assert.match(sql, /UNIQUE\s*\(uid,\s*reporting_date,\s*revision\)/i);
assert.match(sql, /UNIQUE\s*\(uid,\s*reporting_date,\s*run_id\)/i);
assert.match(sql, /BEFORE UPDATE OR DELETE/i);
assert.match(sql, /ON CONFLICT DO NOTHING/i);
assert.match(sql, /run_id_conflict/i);
assert.match(sql, /reporting_date_conflict/i);
assert.match(sql, /REVOKE UPDATE, DELETE ON TABLE public\.lm_cfo_daily_snapshots FROM service_role/i);
```

Also assert RLS, service-role-only SELECT/INSERT/function execute, SECURITY INVOKER, fixed search path, JSON object
checks, non-zero UUID check, revision 1 enforcement in the RPC, report date/revision/currency consistency checks, and
no UPDATE branch.

- [ ] **Step 2: Run focused RED**

```bash
cd apps/life-call
node --test lib/cfo-daily-snapshot-migration.test.js
```

Expected: FAIL because the migration does not exist.

- [ ] **Step 3: Implement the exact additive migration**

Use the proven `lm_score_outcomes` pattern. The RPC algorithm is exact:

```sql
INSERT INTO public.lm_cfo_daily_snapshots
  (uid, reporting_date, run_id, revision, report_payload, source_bundle)
VALUES (p_uid, p_reporting_date, p_run_id, 1, p_report_payload, p_source_bundle)
ON CONFLICT DO NOTHING
RETURNING * INTO candidate;

IF candidate.id IS NOT NULL THEN
  RETURN to_jsonb(candidate) - 'id' - 'uid' - 'report_payload' - 'source_bundle';
END IF;

SELECT * INTO existing
FROM public.lm_cfo_daily_snapshots
WHERE uid = p_uid AND reporting_date = p_reporting_date AND run_id = p_run_id;

IF existing.id IS NOT NULL THEN
  IF existing.report_payload IS NOT DISTINCT FROM p_report_payload
     AND existing.source_bundle IS NOT DISTINCT FROM p_source_bundle THEN
    RETURN to_jsonb(existing) - 'id' - 'uid' - 'report_payload' - 'source_bundle';
  END IF;
  RAISE EXCEPTION 'run_id_conflict' USING ERRCODE = '23505';
END IF;

RAISE EXCEPTION 'reporting_date_conflict' USING ERRCODE = '23505';
```

Before INSERT, reject null/non-object JSON, zero UUID, report `reportingDate` mismatch, report revision other than 1,
currency other than JPY, and source bundle whose source/state IDs are not `moneytree_mufg`. Return no amount or UID.

- [ ] **Step 4: Register and prove GREEN**

Append the migration test exactly once to `test:cfo`, then run:

```bash
cd apps/life-call
node --test lib/cfo-daily-snapshot-migration.test.js
npm run test:cfo
wc -l migrations/2026-08-09-cfo-daily-snapshots.sql lib/cfo-daily-snapshot-migration.test.js
git diff --check
```

Expected: all pass; SQL ≤160 LOC, test ≤100 LOC, diff clean.

- [ ] **Step 5: Commit and push**

```bash
git add apps/life-call/migrations/2026-08-09-cfo-daily-snapshots.sql apps/life-call/lib/cfo-daily-snapshot-migration.test.js apps/life-call/package.json
git commit -m "feat(cfo): add immutable snapshot ledger"
git push canonical HEAD
```

---

### Task 3: Supabase Append Client

**Files:**
- Create: `apps/life-call/lib/cfo-daily-snapshot-store.js`
- Create: `apps/life-call/lib/cfo-daily-snapshot-store.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes `buildCfoDailyReport({ reportingDate, moneytreeRead })`.
- Produces `appendCfoDailySnapshot({ uid, reportingDate, runId, moneytreeRead }, opts)`.

- [ ] **Step 1: Write RED store tests**

With injected `fetchImpl`, prove:

```js
const receipt = await appendCfoDailySnapshot(input, { supaUrl, supaKey, fetchImpl });
assert.equal(calls.length, 1);
assert.equal(calls[0].url, `${supaUrl}/rest/v1/rpc/lm_append_cfo_daily_snapshot`);
assert.deepEqual(Object.keys(JSON.parse(calls[0].init.body)).sort(),
  ["p_report_payload", "p_reporting_date", "p_run_id", "p_source_bundle", "p_uid"]);
assert.equal(receipt.revision, 1);
assert.ok(Object.isFrozen(receipt));
```

Also prove exact UUID/date/uid validation, closed five-key receipt, date/run/revision echo match, non-2xx stable status
category, invalid JSON/shape fail closed, no retry inside the client, no direct table URL, no log call, and no secret,
UID, raw response, account ref, or amount in thrown errors.

- [ ] **Step 2: Run focused RED**

```bash
cd apps/life-call
node --test lib/cfo-daily-snapshot-store.test.js
```

Expected: FAIL only because module/function is absent.

- [ ] **Step 3: Implement the minimum store client**

Implementation shape:

```js
"use strict";
const { buildCfoDailyReport } = require("./cfo-daily-snapshot.js");

async function appendCfoDailySnapshot(input, opts = {}) {
  // Validate exact input, build report internally, require credentials/fetch.
  // POST one RPC request with service headers and the normalized bundle only.
  // Parse and close-validate the five-key receipt; clone/freeze; stable redacted errors.
}

module.exports = { appendCfoDailySnapshot };
```

- [ ] **Step 4: Register and prove GREEN**

Append the test exactly once to `test:cfo`, then run focused and CFO tests, LOC, and diff check. Expected production
≤100 LOC and tests ≤200 LOC.

- [ ] **Step 5: Commit and push**

```bash
git add apps/life-call/lib/cfo-daily-snapshot-store.js apps/life-call/lib/cfo-daily-snapshot-store.test.js apps/life-call/package.json
git commit -m "feat(cfo): append daily snapshots"
git push canonical HEAD
```

---

### Task 4: Real Migration, Idempotency E2E, and Closure

**Files:**
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`
- Modify: `docs/superpowers/specs/2026-08-09-life-manager-cfo-daily-snapshot-design.md`
- Modify: `docs/superpowers/plans/2026-08-09-life-manager-cfo-daily-snapshot.md`

**Interfaces:**
- Consumes the live Moneytree App response, Supabase management credentials, owner Telegram binding, and Task 3 client.
- Produces privacy-safe live evidence and activates CFO-1g2.

- [ ] **Step 1: Run dependency-clean verification**

```bash
cd apps/life-call
npm ci --no-audit --no-fund
node --test lib/cfo-daily-snapshot.test.js lib/cfo-daily-snapshot-migration.test.js lib/cfo-daily-snapshot-store.test.js
npm run test:cfo
npm test
git diff --check
```

- [ ] **Step 2: Apply the migration once**

Load `SUPABASE_ACCESS_TOKEN`, `SUPABASE_URL`, and service role from the existing private runtime env. Derive the
project ref from the URL. POST the migration text as `{ "query": sql }` to
`https://api.supabase.com/v1/projects/<derived-ref>/database/query`, then execute
`NOTIFY pgrst, 'reload schema';`. Print only HTTP success booleans; never print credentials, URL query strings, SQL
response bodies, or project/user identifiers.

- [ ] **Step 3: Run the real no-echo idempotency E2E**

In one controller process:

1. read Moneytree accounts through the installed App;
2. adapt and compose the normalized bundle with an ephemeral reference key;
3. privately resolve exactly one `lm_users.uid` matching the configured owner Telegram chat ID;
4. use Tokyo's current `YYYY-MM-DD` and one random non-zero UUID;
5. call `appendCfoDailySnapshot` twice with identical input;
6. query the table by the same owner/date/run and prove count 1;
7. attempt no UPDATE/DELETE and print no live amount.

Output exactly booleans/count/hash fields: connector success, adapter/bundle success, first append success, retry
same public ref, database row count one, report partial, unknown liabilities preserved, payload privacy, and exit 0.

- [ ] **Step 4: Fresh Sol review**

Review Tasks 1–3 diffs and the redacted E2E evidence. Every Critical/Important finding receives a Luna regression,
minimum fix, focused/full rerun, fix commit, push, and scoped re-review.

- [ ] **Step 5: Close CFO-1g**

Sol changes status to `CFO-1g COMPLETE — CFO-1g2 NEXT`, checks CFO-1g, records commit/test/LOC/live boolean evidence
without amounts/identifiers, commits `docs(cfo): close immutable daily snapshot`, pushes, and sends one `Codex:::`
Telegram milestone with provider message ID. The daily finance report remains 7/7; this milestone must not claim it.

## Completion Boundary

CFO-1g closes only after all three implementation tasks pass scoped review, the migration is live, two same-run
appends produce one immutable row and one receipt identity, full tests pass, docs are pushed, and the Telegram
milestone receipt is recorded. Then CFO-1g2 is the only active item.
