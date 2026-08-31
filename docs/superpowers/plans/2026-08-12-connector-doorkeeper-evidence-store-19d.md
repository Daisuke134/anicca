# Doorkeeper Evidence Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the immutable Doorkeeper provider receipt/artifact store required before the Doorkeeper `applied_bundle` evidence chain can be wired.

**Architecture:** Reuse the existing private `createBrowserProviderEvidenceStore` implementation that already backs Connpass and Meetup. Add one exact Doorkeeper wrapper and behavioral tests; do not add a new store class, schema, directory layout, or dependency.

**Tech Stack:** Node.js CommonJS, `node:test`, `node:assert/strict`, filesystem-backed mode-0600 immutable JSON/PNG objects.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/connpass-evidence-store.js` and `apps/mr-bot/lib/connpass-evidence-store.test.js`.
- Production soft target: +8–12 LOC. Test soft target: +40–70 LOC. No refactor of the existing generic store.
- Use strict TDD: add the behavioral tests, run them and observe the expected RED, then add the minimal production wrapper.
- Accept only `doorkeeper-event://event/<positive integer>` and `provider-receipt://doorkeeper/<64 lowercase hex>`.
- Preserve the existing deterministic provider-ID tuple, PNG signature/minimum length, exact receipt/marker schemas, immutable collision handling, mode 0600 files, and tenant privacy.
- Do not modify Connector discovery, action/readback, minimal evidence chain, Calendar transport, Telegram, browser/session/target, state, launchd, schedule, or SSOT checkboxes.
- Luna owns production/test edits and the RED/GREEN report. Sol owns review, SSOT, commit, and push.

---

### Task 1: Export the exact Doorkeeper evidence-store wrapper

**Files:**
- Modify: `apps/mr-bot/lib/connpass-evidence-store.js`
- Test: `apps/mr-bot/lib/connpass-evidence-store.test.js`

**Interfaces:**
- Consumes: private `createBrowserProviderEvidenceStore(options)` in `connpass-evidence-store.js`.
- Produces: `createDoorkeeperEvidenceStore(options = {})`, returning the same frozen `{record, readExternalReceipt, readArtifact}` contract as the Connpass/Meetup wrappers.

- [ ] **Step 1: Write the failing behavioral tests**

Extend the existing import and add these two behaviors with literal Doorkeeper identities:

```js
const {
  createConnpassEvidenceStore,
  createMeetupEvidenceStore,
  createDoorkeeperEvidenceStore,
} = require("./connpass-evidence-store.js");

test("Doorkeeper wrapper stores exact event receipt and private immutable artifacts", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "doorkeeper-evidence-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x65);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createDoorkeeperEvidenceStore({ dataDir: directory });
  const refs = await store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/101",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  assert.match(refs.external_receipt_ref, /^provider-receipt:\/\/doorkeeper\/[0-9a-f]{64}$/);
  const receipt = await store.readExternalReceipt("doorkeeper-test", refs.external_receipt_ref);
  assert.deepEqual(receipt, {
    kind: "provider_response", provider_id: refs.external_receipt_ref.split("/").at(-1),
    observed_at: "2026-08-12T01:02:03.000Z", event_ref: "doorkeeper-event://event/101",
    artifact_sha256: refs.artifact_ref.split("/").at(-1),
  });
  const root = path.join(directory, "tenants", "doorkeeper-test", "outbound", "doorkeeper");
  const artifactSha = refs.artifact_ref.split("/").at(-1);
  const files = [
    path.join(root, "provider-receipts", `${refs.external_receipt_ref.split("/").at(-1)}.json`),
    path.join(root, "artifacts", `${artifactSha}.json`),
    path.join(directory, "objects", "sha256", artifactSha),
  ];
  for (const file of files) assert.equal(fs.statSync(file).mode & 0o777, 0o600, file);
  assert.deepEqual(await store.readArtifact("doorkeeper-test", refs.artifact_ref), png);
  assert.equal(JSON.stringify(refs).includes("doorkeeper-test"), false);
});

test("Doorkeeper wrapper rejects wrong event identity and receipt tuple tampering", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "doorkeeper-evidence-hardening-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const png = Buffer.alloc(5_000, 0x66);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(png);
  const store = createDoorkeeperEvidenceStore({ dataDir: directory });
  await assert.rejects(store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/0",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  }));
  const refs = await store.record({
    tenantId: "doorkeeper-test", eventRef: "doorkeeper-event://event/101",
    observedAt: "2026-08-12T01:02:03.000Z", screenshot: png,
  });
  const providerId = refs.external_receipt_ref.split("/").at(-1);
  const file = path.join(directory, "tenants", "doorkeeper-test", "outbound", "doorkeeper", "provider-receipts", `${providerId}.json`);
  const receipt = JSON.parse(fs.readFileSync(file, "utf8"));
  fs.writeFileSync(file, `${JSON.stringify({ ...receipt, event_ref: "doorkeeper-event://event/102" })}\n`);
  await assert.rejects(store.readExternalReceipt("doorkeeper-test", refs.external_receipt_ref));
});
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd apps/mr-bot
node --test lib/connpass-evidence-store.test.js
```

Expected: the two new tests fail because `createDoorkeeperEvidenceStore` is not exported; all four existing tests remain green.

- [ ] **Step 3: Add the minimum production wrapper**

Add beside the existing Meetup wrapper:

```js
function createDoorkeeperEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "doorkeeper",
    eventRef: /^doorkeeper-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/doorkeeper\/([0-9a-f]{64})$/,
    collisionMessage: "Doorkeeper evidence collision",
  });
}
```

Export it with the two existing public factories. Do not change `createBrowserProviderEvidenceStore`.

- [ ] **Step 4: Verify GREEN and adjacent evidence behavior**

Run:

```bash
cd apps/mr-bot
node --test lib/connpass-evidence-store.test.js lib/connector-minimal-evidence.test.js
node --check lib/connpass-evidence-store.js
git diff --check
```

Expected: 37 tests pass, zero failures; syntax and diff checks exit 0.

- [ ] **Step 5: Self-review and report without commit**

Confirm only the two owned files changed, production is within +8–12 LOC, no private tenant value appears in returned references, and no external/browser/state/launchd effect occurred. Write the RED/GREEN commands and exact counts to the assigned report file. Do not commit or push; Sol performs review and integration.
