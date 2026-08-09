# Life Manager CFO Snapshot Receipt Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan
> task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Sol owns plan, review, live E2E, state, commit, and
> push. Only Luna writes production code and tests.

**Goal:** Make the revision-1 snapshot client accept the real corrected database receipt without weakening its closed
contract or changing its stable five-key return value.

**Architecture:** The already-applied correction migration adds exactly `supersedes_revision: null` to the legacy
revision-1 RPC receipt. The client accepts either the original exact five-key provider shape or the corrected exact
six-key provider shape, requires the added field to be `null`, and projects both to the existing frozen five-key
application receipt. No database, migration, scheduler, connector, or Telegram code changes.

**Tech Stack:** Node.js 22, `node:test`, existing Supabase/PostgREST client.

## Global Constraints

- Ponytail full: reuse the existing validator; no abstraction, dependency, migration, retry, log, or fallback query.
- One active item only. Changed files: exactly two. Production addition soft target: <=15 LOC; test addition <=40 LOC.
- Preserve fail-closed exact keys, UUID/date/run/revision/timestamp checks, fixed redacted errors, single RPC call,
  immutable output, and no private payload in logs or errors.
- The returned application receipt remains exactly
  `public_ref,reporting_date,run_id,revision,created_at`; `supersedes_revision` is validated but not exposed.

---

### Task 1: Accept the corrected revision-1 receipt

**Files:**
- Modify: `apps/life-call/lib/cfo-daily-snapshot-store.js`
- Modify: `apps/life-call/lib/cfo-daily-snapshot-store.test.js`

**Interfaces:**
- Consumes: `lm_append_cfo_daily_snapshot` provider receipt in either original five-key form or corrected six-key form.
- Produces: unchanged `appendCfoDailySnapshot(input, opts)` and unchanged frozen five-key receipt.

- [x] **Step 1: Write the focused failing test**

Add one test using the real observed provider shape:

```js
const corrected = { ...RECEIPT, supersedes_revision: null };
const receipt = await appendCfoDailySnapshot(input(), {
  supaUrl: URL, supaKey: KEY, fetchImpl: async () => response(corrected),
});
assert.deepEqual(receipt, RECEIPT);
assert.deepEqual(Object.keys(receipt).sort(), Object.keys(RECEIPT).sort());
assert.equal(Object.isFrozen(receipt), true);
```

In the same test, set `supersedes_revision` to `0` and prove one RPC call fails with the existing fixed
`cfo_snapshot_store_failed:invalid_receipt` error and no sensitive value.

- [x] **Step 2: Run RED**

Run from `apps/life-call`:

```bash
node --test lib/cfo-daily-snapshot-store.test.js
```

Expected: the corrected six-key receipt fails because the current exact validator allows only five keys.

- [x] **Step 3: Implement minimum GREEN**

Add one corrected-provider key set:

```js
const CORRECTED_RECEIPT_KEYS = new Set([...RECEIPT_KEYS, "supersedes_revision"]);
```

Inside `validateReceipt`, detect whether the provider owns `supersedes_revision`, validate against the matching exact
key set, require the corrected revision-1 value to be `null`, then build and freeze this stable projection:

```js
const projected = {
  public_ref: value.public_ref,
  reporting_date: value.reporting_date,
  run_id: value.run_id,
  revision: value.revision,
  created_at: value.created_at,
};
return freeze(structuredClone(projected));
```

Do not accept missing original keys, non-null predecessor values, or any seventh key.

- [x] **Step 4: Verify GREEN**

Run:

```bash
node --test lib/cfo-daily-snapshot-store.test.js
npm run test:cfo
npm test
wc -l lib/cfo-daily-snapshot-store.js lib/cfo-daily-snapshot-store.test.js
git diff --check
```

Expected: all exit 0; production addition <=15 LOC.

- [x] **Step 5: Review and real E2E**

Fresh Sol review must return no Critical/Important finding. Sol then calls the real revision-1 append client with the
already-stored current snapshot bundle, verifies a successful frozen five-key receipt, the same durable snapshot row
count, and zero Telegram calls. Output only named booleans/counts; no amount, UID, refs, URL, or credential.

- [x] **Step 6: Close**

Update this plan and the parent CFO spec with RED/GREEN/review/live evidence. Commit and push. Then make the
launchd-callable Moneytree reader the only active item.

## Definition of done

The exact client call that previously persisted a row and then threw `invalid_receipt` returns success against the
real live six-key provider response, while original five-key fixtures remain compatible and no new row or Telegram
message is created.

## Completion evidence

- RED: the real corrected six-key fixture failed with `cfo_snapshot_store_failed:invalid_receipt` before the change.
- GREEN: focused `5/5`, CFO `242/242`, and full `npm test` `875/875`; `git diff --check` passed.
- Scope: exactly two files; production change stayed below the 15-LOC soft target; no SQL, scheduler, Telegram,
  dependency, retry, or logging change.
- Fresh Sol review: `ship — Spec ✅` with no Critical or Important finding.
- Real idempotent E2E: the corrected receipt was accepted and projected to an exact frozen five-key receipt; the
  existing snapshot stayed one row before and after; Telegram claim/receipt counts stayed unchanged; Telegram calls
  were zero; no private field was printed.
- Status: **COMPLETE**. The only active item moves to the launchd-callable Moneytree reader.
