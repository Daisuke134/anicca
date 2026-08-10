# Life Manager CFO-2a Business-Ledger Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize each existing `lm_api_cost` row into one deterministic, privacy-safe, honestly estimated financial-unit event.

**Architecture:** Add one pure function to the existing `apps/life-call/lib/ledger.js`; reuse the existing
`ledger.test.js`. The function performs no I/O and maps only four current Life Manager kinds. All persistence,
OpenTelemetry, aggregation, other businesses, and UI stay deferred.

**Tech Stack:** Node.js CommonJS, built-in `node:test`, built-in `node:assert/strict`; no new dependency.

## Global Constraints

- Ponytail full: modify exactly two existing files; add no file, dependency, migration, table, service, or scheduler.
- Soft target: at most 45 production LOC and 55 test LOC; at most 100 added LOC total.
- Sol owns this plan, final E2E/evidence, spec closure, and push. Luna owns production code, tests, test commands, and
  the implementation commit; Sol does not write production code or tests.
- Strict TDD: add each behavioral test first, run it, and record the expected RED before production implementation.
- Keep `lm_api_cost` unchanged. `normalizeApiCostEvent` is pure and receives a PostgREST row as its only input.
- `financial_unit_id` is the existing registry identity; never create or return a second `business_id`.
- Known kinds are exactly `gemini_live`, `telnyx_call`, `composio_call`, and `composio_poll`, all mapped to
  `life_manager_saas`. Every other valid snake-case kind is `unattributed` with `financial_unit_id: null`.
- `est_usd` always becomes `evidence_status: "locally_estimated"`; no path returns measured or confirmed.
- Invalid values throw only `cfo_business_ledger_invalid:<reason>` and never include source values or metadata.
- Do not copy `meta` or unknown source keys into the output.
- Tests use literal expected objects and the real exported function; no mocks, source-text assertions, or generated
  expected values.

---

### Task 1: Normalize existing cost rows

**Files:**
- Modify: `apps/life-call/lib/ledger.test.js`
- Modify: `apps/life-call/lib/ledger.js`

**Estimated change:** 45–55 test LOC, then 35–45 production LOC. Two files only.

**Interfaces:**
- Consumes: a plain JSON row with `id`, `ts`, `uid`, `kind`, `quantity`, `unit`, `est_usd`, and optional `meta`.
- Produces: exported synchronous `normalizeApiCostEvent(row)` returning the exact event in the CFO-2a spec.
- Downstream: CFO-2b may consume the normalized event later; this task adds no downstream caller or persistence.

- [ ] **Step 1: Add the three behavioral tests before production code**

Append these tests to `apps/life-call/lib/ledger.test.js`. The production break each test catches is respectively:
wrong fact mapping/private metadata leakage, guessed attribution, and invalid money silently becoming zero.

```js
test("normalizeApiCostEvent maps one known estimate without metadata leakage", () => {
  const row = {
    id: 42, ts: "2026-08-10T01:02:03Z", uid: "u1", kind: "gemini_live",
    quantity: 90, unit: "seconds", est_usd: "0.0345", meta: { secret: "META_SENTINEL" },
  };
  const before = structuredClone(row);

  assert.deepEqual(ledger().normalizeApiCostEvent(row), {
    schema_version: 1,
    source_ledger: "lm_api_cost",
    source_event_id: "lm_api_cost:42",
    occurred_at: "2026-08-10T01:02:03.000Z",
    owner_id: "u1",
    financial_unit_id: "life_manager_saas",
    attribution_status: "attributed",
    event_type: "operating_cost_estimate",
    cost_kind: "gemini_live",
    quantity: { value: "90", unit: "seconds" },
    amount: { value: "0.0345", currency: "USD" },
    evidence_status: "locally_estimated",
  });
  assert.deepEqual(row, before);
  assert.doesNotMatch(JSON.stringify(ledger().normalizeApiCostEvent(row)), /META_SENTINEL|secret|meta/i);
});

test("normalizeApiCostEvent leaves an unknown valid kind unattributed", () => {
  const event = ledger().normalizeApiCostEvent({
    id: "43", ts: "2026-08-10T01:02:04Z", uid: null, kind: "future_cost",
    quantity: "1", unit: "call", est_usd: 0, meta: {},
  });
  assert.equal(event.cost_kind, "future_cost");
  assert.equal(event.financial_unit_id, null);
  assert.equal(event.attribution_status, "unattributed");
  assert.equal(event.owner_id, null);
  assert.equal(event.amount.value, "0");
});

test("normalizeApiCostEvent rejects invalid identity and money with redacted errors", () => {
  const valid = {
    id: 44, ts: "2026-08-10T01:02:05Z", uid: "u1", kind: "telnyx_call",
    quantity: 1, unit: "seconds", est_usd: 0.001, meta: {},
  };
  const cases = [
    ["id", 0], ["quantity", -1], ["quantity", Number.NaN],
    ["est_usd", -1], ["est_usd", Number.POSITIVE_INFINITY],
    ["est_usd", "AMOUNT_SENTINEL"], ["unit", ""],
  ];
  for (const [field, value] of cases) {
    assert.throws(
      () => ledger().normalizeApiCostEvent({ ...valid, [field]: value }),
      (error) => /^cfo_business_ledger_invalid:[a-z_]+$/.test(error.message)
        && !/AMOUNT_SENTINEL|u1|0\.001/.test(error.message),
      field,
    );
  }
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
node --test lib/ledger.test.js
```

Expected: the existing seven tests pass and all three new tests fail because
`ledger().normalizeApiCostEvent is not a function`. Any syntax error or different failure must be fixed in the test
before production code is written.

- [ ] **Step 3: Add the minimal pure normalizer**

In `apps/life-call/lib/ledger.js`, reuse the existing CFO boundary validator by adding this import and projection
immediately after `"use strict"`; do not reimplement plain-object or RFC3339 validation.

```js
const { createCfoSupabaseRpc } = require("./cfo-supabase-rpc.js");
const {
  fail: costEventFail, plain: plainCostRow, timestamp: validCostTimestamp,
} = createCfoSupabaseRpc("cfo_business_ledger_invalid:");
```

Place the remaining constants/helpers immediately before `finite`, then add the function before `businessSummary`
and export it. Use this implementation; do not add options, I/O, registry loading, or classes.

```js
const DIRECT_COST_KINDS = new Set(["gemini_live", "telnyx_call", "composio_call", "composio_poll"]);
const COST_KIND = /^[a-z][a-z0-9_]*$/;
const NUMERIC_TEXT = /^(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/;

function positiveId(value) {
  if (typeof value === "number" && Number.isSafeInteger(value) && value > 0) return String(value);
  if (typeof value === "string" && /^[1-9]\d*$/.test(value)) return value;
  costEventFail("invalid_id");
}

function numericText(value, reason) {
  if (typeof value !== "number" && typeof value !== "string") costEventFail(reason);
  const text = String(value);
  if (!NUMERIC_TEXT.test(text) || !Number.isFinite(Number(text)) || Number(text) < 0) costEventFail(reason);
  return text;
}

function normalizeApiCostEvent(row) {
  if (!plainCostRow(row)) costEventFail("invalid_row");
  const id = positiveId(row.id);
  if (!validCostTimestamp(row.ts)) costEventFail("invalid_timestamp");
  const ownerId = row.uid === null ? null : row.uid;
  if (ownerId !== null && (typeof ownerId !== "string" || ownerId.length === 0 || ownerId.trim() !== ownerId))
    costEventFail("invalid_owner");
  if (typeof row.kind !== "string" || !COST_KIND.test(row.kind)) costEventFail("invalid_kind");
  if (typeof row.unit !== "string" || row.unit.length === 0 || row.unit.trim() !== row.unit)
    costEventFail("invalid_unit");
  const attributed = DIRECT_COST_KINDS.has(row.kind);
  return {
    schema_version: 1, source_ledger: "lm_api_cost", source_event_id: `lm_api_cost:${id}`,
    occurred_at: new Date(row.ts).toISOString(), owner_id: ownerId,
    financial_unit_id: attributed ? "life_manager_saas" : null,
    attribution_status: attributed ? "attributed" : "unattributed",
    event_type: "operating_cost_estimate", cost_kind: row.kind,
    quantity: { value: numericText(row.quantity, "invalid_quantity"), unit: row.unit },
    amount: { value: numericText(row.est_usd, "invalid_amount"), currency: "USD" },
    evidence_status: "locally_estimated",
  };
}
```

Change the existing export to:

```js
module.exports = {
  recordCost, recordDailyComposioPoll, monthlyComposioCallCount,
  normalizeApiCostEvent, businessSummary,
};
```

- [ ] **Step 4: Run GREEN and regression commands**

Run in `apps/life-call`:

```bash
node --test lib/ledger.test.js
npm run test:cfo
npm test
```

Expected: focused ledger tests report 10/10; CFO reports 254/254; full `npm test` exits 0. Output must contain no
`META_SENTINEL`, `AMOUNT_SENTINEL`, UID, or raw metadata outside test names/source diagnostics.

- [ ] **Step 5: Enforce the Ponytail size and scope gate**

Run:

```bash
git diff --check
git diff --stat
git diff --numstat -- apps/life-call/lib/ledger.js apps/life-call/lib/ledger.test.js
git status --short
```

Expected: only the two planned implementation files are modified; production additions are at most 45 lines, test
additions at most 55 lines, total additions at most 100, and `git diff --check` is silent. If exceeded, reduce scope;
do not widen the target.

- [ ] **Step 6: Commit the reviewed implementation**

After the controller's task review passes, commit only the two implementation files:

```bash
git add apps/life-call/lib/ledger.js apps/life-call/lib/ledger.test.js
git commit -m "feat(cfo): normalize estimated business costs"
```

Do not push. The Sol controller performs final evidence capture, spec closure, fetch, and push.
