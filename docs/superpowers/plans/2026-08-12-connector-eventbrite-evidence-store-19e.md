# Eventbrite Evidence Store Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a private immutable Eventbrite provider-receipt/artifact wrapper to the existing browser-provider evidence store without changing the generic store or live workflow.

**Architecture:** Reuse `createBrowserProviderEvidenceStore` exactly as Connpass, Meetup, and Doorkeeper do. Add only an Eventbrite namespace wrapper/export and two matching tests for durable mode-0600 storage, deterministic receipt identity, readback, and tamper rejection.

**Tech Stack:** Node.js CommonJS, `node:test`, local filesystem, SHA-256.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/connpass-evidence-store.js` and `apps/mr-bot/lib/connpass-evidence-store.test.js`.
- Production soft target: +8–12 LOC. Test soft target: +40–70 LOC. No new file, dependency, schema, class, or generic refactor.
- Use strict TDD: import the new factory and add the two tests before production export/wrapper.
- Event identity is exact `eventbrite-event://event/<positive integer>`; receipt identity is exact `provider-receipt://eventbrite/<64 lowercase hex>`.
- Store under the existing private tenant root with provider segment `eventbrite`; preserve mode 0600, atomic immutable writes, content-addressed PNG object, deterministic provider ID, tenant non-disclosure, tuple validation, and fail-closed reads.
- Reject zero/nonnumeric/wrong-provider event refs and tampered receipt tuples. Reuse the existing shared implementation unchanged.
- Preserve Connpass, Meetup, Doorkeeper behavior and every existing receipt/artifact path.
- Do not change minimal evidence chain, Calendar transport, browser/action/readback, native order, launchd, schedule, or live external systems.
- Luna owns production/test edits and RED/GREEN reporting. Sol owns review, SSOT, commit, and push.

---

### Task 1: Add the Eventbrite evidence-store wrapper

**Files:**
- Modify: `apps/mr-bot/lib/connpass-evidence-store.js`
- Test: `apps/mr-bot/lib/connpass-evidence-store.test.js`

**Interfaces:**
- Produces: `createEventbriteEvidenceStore({dataDir})` with the unchanged `record`, `readExternalReceipt`, and `readArtifact` interface.

- [ ] **Step 1: Write two failing Eventbrite wrapper tests**

Import `createEventbriteEvidenceStore`. Add:

1. A happy test using `eventbrite-event://event/1997468673573`, a valid 5,000+ byte PNG, and an exact ISO instant. Assert the Eventbrite receipt ref, receipt tuple, Eventbrite tenant path, mode 0600 for receipt/marker/object, artifact readback equality, and tenant absence from returned refs.
2. A fail-closed test that rejects `eventbrite-event://event/0`, then records a valid event and proves a mismatched Eventbrite event ref in the stored receipt is rejected.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
node --test apps/mr-bot/lib/connpass-evidence-store.test.js
```

Expected: the existing six tests pass and the two new tests fail because the new factory is absent.

- [ ] **Step 3: Add the minimum wrapper/export**

Add only:

```js
function createEventbriteEvidenceStore(options = {}) {
  return createBrowserProviderEvidenceStore({
    ...options, provider: "eventbrite",
    eventRef: /^eventbrite-event:\/\/event\/[1-9][0-9]*$/,
    receiptRef: /^provider-receipt:\/\/eventbrite\/([0-9a-f]{64})$/,
    collisionMessage: "Eventbrite evidence collision",
  });
}
```

Export it beside the other three wrappers. Do not change `createBrowserProviderEvidenceStore`.

- [ ] **Step 4: Verify GREEN and adjacent chain**

```bash
node --test apps/mr-bot/lib/connpass-evidence-store.test.js apps/mr-bot/lib/connector-minimal-evidence.test.js
node --check apps/mr-bot/lib/connpass-evidence-store.js
git diff --check
```

Expected: all store and evidence-chain tests pass, syntax/diff checks exit 0.

- [ ] **Step 5: Self-review and report without commit**

Confirm exact two-file scope, generic implementation unchanged, mode 0600 and tamper checks are real filesystem assertions, and live/browser/Calendar/Telegram effects are 0. Write RED/GREEN commands, counts, LOC, and concerns to the assigned report. Do not commit or push.
