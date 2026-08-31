# Doorkeeper Minimal Evidence Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Doorkeeper registered-page evidence into the existing provider receipt, Calendar, Telegram, and durable `applied_bundle` chain without changing browser action behavior.

**Architecture:** Extend the current provider map in `connector-minimal-evidence.js` with the reviewed Doorkeeper store and a strict canonical URL parser. Reuse the Meetup current-page screenshot path: never replace or navigate away from the official registered page, validate the immutable receipt/artifact before any downstream effect, then use the unchanged Calendar/Telegram/checkpoint/bundle pipeline.

**Tech Stack:** Node.js CommonJS, `node:test`, existing filesystem evidence stores, injected Calendar/Telegram boundaries.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/connector-minimal-evidence.js` and `apps/mr-bot/lib/connector-minimal-evidence.test.js`.
- Production soft target: +25–40 LOC. Test soft target: +65–95 LOC. No new file, class, schema, dependency, or generic abstraction.
- Use strict TDD: new Doorkeeper behavior must fail before production wiring and pass after the minimum change.
- Accept only `doorkeeper-event://event/<positive integer>` paired with exact `https://<lowercase-group>.doorkeeper.jp/events/<same positive integer>`; reject `www`, uppercase, credentials, port, query, fragment, trailing slash, and mismatched IDs.
- Accept provider state `registered` only. Require the supplied owned page URL to equal the canonical event URL before screenshot or any downstream effect.
- Do not call `page.setContent`, `page.goto`, or `page.evaluate` for Doorkeeper evidence. Capture `{type:"png", fullPage:true}` from the official current page.
- Validate the newly recorded receipt and artifact through `readExternalReceipt` and `readArtifact` before Calendar, Telegram, or bundle writes.
- Preserve all existing Luma, Peatix, Connpass, Meetup behavior, bundle schema, checkpoints, idempotency, delivery recovery, privacy, and fail-closed boundaries.
- Do not modify Calendar transport, provider discovery/action/readback, browser Harness, native order, state, launchd, schedule, or live external systems.
- Luna owns production/test edits and RED/GREEN reporting. Sol owns review, SSOT, commit, push, and later live acceptance.

---

### Task 1: Add Doorkeeper to the minimal evidence provider map

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.js`
- Test: `apps/mr-bot/lib/connector-minimal-evidence.test.js`

**Interfaces:**
- Consumes: `createDoorkeeperEvidenceStore(options)` from `connpass-evidence-store.js` and the existing current-page capture/checkpoint pipeline.
- Produces: `createMinimalEvidenceChain(...).completeEvidence({provider:"doorkeeper", candidate, page, providerState:{status:"registered"}})` returning `applied_bundle` with `completion_disposition:"created"` or the exact idempotent `"reused"` bundle.

- [ ] **Step 1: Write failing Doorkeeper chain tests**

Add a literal candidate and isolated fixture beside the existing Meetup tests:

```js
function doorkeeperCandidate(extra = {}) {
  return {
    provider: "doorkeeper", event_ref: "doorkeeper-event://event/101",
    canonical_url: "https://tokyo-builders.doorkeeper.jp/events/101",
    title: "Community Event", starts_at: "2026-08-13T10:00:00.000Z", ends_at: "2026-08-13T11:00:00.000Z",
    venue_name: "Tokyo", ...extra,
  };
}

function doorkeeperFixture(options = {}) {
  const stateDir = fs.mkdtempSync(path.join(os.tmpdir(), "connector-minimal-doorkeeper-evidence-"));
  const png = Buffer.concat([PNG_SIGNATURE, Buffer.alloc(6_000, 19)]);
  const calls = [];
  const receipt = { id: "google-doorkeeper-1", htmlLink: "https://www.google.com/calendar/event?eid=doorkeeper-one" };
  let reads = 0;
  const calendar = {
    async findConnectorEvents(input) { calls.push(["calendar-read", input]); return reads++ === 0 ? [] : [receipt]; },
    async createConnectorEvent(input) { calls.push(["calendar-create", input]); return receipt; },
  };
  const chain = createMinimalEvidenceChain({
    stateDir, tenantId: "doorkeeper-test", calendar, calendarId: "primary", telegramTarget: "test-target",
    now: () => new Date("2026-08-12T08:30:00.000Z"),
    sendMessage: async (message, telegram) => { calls.push(["telegram-message", message, telegram]); return { messageId: 9601 }; },
    sendPhoto: async (bytes, telegram) => { calls.push(["telegram-photo", bytes, telegram]); return { messageId: 9602 }; },
  });
  const pageUrl = { value: options.pageUrl || "https://tokyo-builders.doorkeeper.jp/events/101" };
  const page = {
    async setContent() { calls.push(["set-content"]); throw new Error("Doorkeeper page replacement forbidden"); },
    async goto() { calls.push(["goto"]); throw new Error("Doorkeeper evidence navigation forbidden"); },
    async evaluate() { calls.push(["evaluate"]); throw new Error("Doorkeeper receipt render forbidden"); },
    url() { calls.push(["url"]); return pageUrl.value; },
    async screenshot(input) { calls.push(["screenshot", input]); return png; },
  };
  return { stateDir, calls, chain, page, candidate: doorkeeperCandidate(options.candidate), cleanup: () => fs.rmSync(stateDir, { recursive: true, force: true }) };
}
```

Add one happy/idempotent test and one fail-closed table:

```js
test("Doorkeeper captures the registered page and reuses immutable evidence without navigation or replacement", async () => {
  const fixture = doorkeeperFixture();
  try {
    const input = { provider: "doorkeeper", candidate: fixture.candidate, page: fixture.page, providerState: { status: "registered" } };
    const first = await fixture.chain.completeEvidence(input);
    assert.equal(first.provider, "doorkeeper");
    assert.equal(first.completion_disposition, "created");
    assert.match(first.provider_receipt_ref, /^provider-receipt:\/\/doorkeeper\/[0-9a-f]{64}$/);
    assert.deepEqual(fixture.calls.find(([name]) => name === "screenshot")[1], { type: "png", fullPage: true });
    assert.equal(fixture.calls.filter(([name]) => ["set-content", "goto", "evaluate"].includes(name)).length, 0);
    const effects = new Map(["screenshot", "calendar-create", "telegram-message", "telegram-photo"].map((name) => [name, fixture.calls.filter(([entry]) => entry === name).length]));
    const second = await fixture.chain.completeEvidence(input);
    assert.equal(second.completion_disposition, "reused");
    assert.equal(second.bundle_id, first.bundle_id);
    for (const [name, count] of effects) assert.equal(fixture.calls.filter(([entry]) => entry === name).length, count, name);
  } finally { fixture.cleanup(); }
});

test("Doorkeeper identity, registered state, and current page URL fail closed before downstream effects", async () => {
  const cases = [
    { candidate: { event_ref: "doorkeeper-event://event/0" } },
    { candidate: { event_ref: "doorkeeper-event://event/102" } },
    { candidate: { canonical_url: "https://www.doorkeeper.jp/events/101" } },
    { candidate: { canonical_url: "https://Tokyo-builders.doorkeeper.jp/events/101" } },
    { candidate: { canonical_url: "https://tokyo-builders.doorkeeper.jp/events/101/" } },
    { candidate: { canonical_url: "https://tokyo-builders.doorkeeper.jp/events/101?x=1" } },
    { candidate: { canonical_url: "https://tokyo-builders.doorkeeper.jp/events/102" } },
    { status: "pending" }, { status: "absent" },
    { pageUrl: "https://tokyo-builders.doorkeeper.jp/events/102" }, { pageUrl: "about:blank" },
  ];
  for (const value of cases) {
    const fixture = doorkeeperFixture(value);
    try {
      await assert.rejects(fixture.chain.completeEvidence({ provider: "doorkeeper", candidate: fixture.candidate, page: fixture.page, providerState: { status: value.status || "registered" } }));
      assert.equal(fixture.calls.filter(([name]) => ["screenshot", "calendar-read", "calendar-create", "telegram-message", "telegram-photo"].includes(name)).length, 0);
    } finally { fixture.cleanup(); }
  }
});
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
cd apps/mr-bot
node --test lib/connector-minimal-evidence.test.js
```

Expected: the two Doorkeeper tests fail at the missing provider contract while all 31 existing evidence-chain tests remain green.

- [ ] **Step 3: Add the minimum production wiring**

Make these bounded changes only:

```js
const { createConnpassEvidenceStore, createMeetupEvidenceStore, createDoorkeeperEvidenceStore } = require("./connpass-evidence-store.js");
const DOORKEEPER_EVENT_REF = /^doorkeeper-event:\/\/event\/([1-9][0-9]*)$/;
const DOORKEEPER_RECEIPT_REF = /^provider-receipt:\/\/doorkeeper\/([0-9a-f]{64})$/;
```

Add this strict canonical parser:

```js
function doorkeeperUrl(value, eventRef) {
  if (typeof eventRef !== "string" || typeof value !== "string") invalid();
  const eventMatch = DOORKEEPER_EVENT_REF.exec(eventRef);
  let url;
  try { url = new URL(value); } catch { invalid(); }
  const groupMatch = /^([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.doorkeeper\.jp$/.exec(url.hostname);
  const expected = eventMatch && groupMatch
    ? `https://${groupMatch[1]}.doorkeeper.jp/events/${eventMatch[1]}` : "";
  if (!expected || groupMatch[1] === "www" || url.protocol !== "https:" || url.username || url.password || url.port
    || url.pathname !== `/events/${eventMatch[1]}` || value !== expected) invalid();
  return expected;
}
```

Instantiate `doorkeeperEvidenceStore`, add the `doorkeeper` provider map entry with state `["registered"]`, and include the store in dependency validation.

Treat Doorkeeper exactly like Meetup at the three current-page boundaries:

```js
providerName === "connpass" || providerName === "meetup" || providerName === "doorkeeper"
providerName !== "connpass" && providerName !== "meetup" && providerName !== "doorkeeper"
input.provider === "connpass" || input.provider === "meetup" || input.provider === "doorkeeper"
input.provider === "meetup" || input.provider === "doorkeeper"
```

The implementation must screenshot the current official page and validate the first persisted receipt/artifact before Calendar.

- [ ] **Step 4: Verify GREEN and adjacent stores**

Run:

```bash
cd apps/mr-bot
node --test lib/connector-minimal-evidence.test.js lib/connpass-evidence-store.test.js
node --check lib/connector-minimal-evidence.js
git diff --check
```

Expected: 39 tests pass, zero failures; syntax and diff checks exit 0.

- [ ] **Step 5: Self-review and report without commit**

Confirm only the two owned files changed, no Doorkeeper page replacement/navigation/render path exists, invalid identity/state/current URL causes zero screenshot/Calendar/Telegram effects, and no browser/live state/launchd effect occurred. Write RED/GREEN commands, exact counts, LOC, and concerns to the assigned report file. Do not commit or push.
