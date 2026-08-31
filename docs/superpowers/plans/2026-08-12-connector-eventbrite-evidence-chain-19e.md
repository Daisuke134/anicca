# Eventbrite Minimal Evidence Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire verified Eventbrite registered-page evidence into the existing provider receipt, Calendar, Telegram, and durable `applied_bundle` chain without changing the completed Eventbrite action/readback workflow.

**Architecture:** Extend the current provider map in `connector-minimal-evidence.js` with the reviewed Eventbrite store and a canonical URL parser matching the current Eventbrite workflow's two event paths. Reuse the registered current-page screenshot path: no navigation or DOM replacement, durable receipt/artifact readback before downstream effects, then the unchanged Calendar/Telegram/checkpoint/bundle pipeline.

**Tech Stack:** Node.js CommonJS, `node:test`, existing filesystem evidence stores, injected Calendar/Telegram boundaries.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/connector-minimal-evidence.js` and `apps/mr-bot/lib/connector-minimal-evidence.test.js`.
- Production soft target: +28–45 LOC. Test soft target: +75–110 LOC. No new file, dependency, schema, class, or generic abstraction.
- Use strict TDD: new Eventbrite chain behavior must fail before production wiring and pass after the minimum change.
- Accept exact `eventbrite-event://event/<positive ID>` paired with either exact `https://www.eventbrite.com/e/<slug>-tickets-<same ID>` or exact `https://www.eventbrite.com/e/<same ID>`. Match the existing workflow slug grammar; reject HTTP, non-www/wrong host, uppercase raw host, credentials, port, query, fragment, trailing slash, invalid/zero/mismatched ID, and extra paths.
- Accept provider state `registered` only. Require supplied owned parent page URL to equal the canonical Eventbrite URL before screenshot or downstream effect.
- Do not call `page.setContent`, `page.goto`, or `page.evaluate` for Eventbrite evidence. Capture `{type:"png", fullPage:true}` from the official registered parent page; action/readback already proves child checkout completion before this boundary.
- Validate the newly recorded Eventbrite receipt and artifact through `readExternalReceipt` and `readArtifact` before Calendar, Telegram, or bundle writes.
- Preserve Luma, Peatix, Connpass, Meetup, Doorkeeper behavior, bundle schema, checkpoints, idempotency, delivery recovery, privacy, and fail-closed boundaries.
- Do not modify Calendar transport, Eventbrite discovery/action/readback, browser Harness, native order, state, launchd, schedule, or live systems.
- Luna owns production/test edits and RED/GREEN reporting. Sol owns review, SSOT, commit, push, and later live acceptance.

---

### Task 1: Add Eventbrite to the minimal evidence provider map

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-evidence.js`
- Test: `apps/mr-bot/lib/connector-minimal-evidence.test.js`

**Interfaces:**
- Consumes: `createEventbriteEvidenceStore(options)` and `completeEvidence({provider:"eventbrite", candidate, page, providerState:{status:"registered"}})`.
- Produces: the existing `applied_bundle` with `completion_disposition:"created"` or exact idempotent `"reused"`.

- [ ] **Step 1: Write failing Eventbrite chain tests**

Add an isolated fixture beside Doorkeeper tests using a valid 5,000+ byte PNG, injected Calendar create/readback, positive injected Telegram IDs, and parent page methods whose `setContent`, `goto`, and `evaluate` throw if called.

Add:

1. A happy/idempotent test for slug form `https://www.eventbrite.com/e/tokyo-free-event-tickets-1997468673573`, asserting created Eventbrite receipt/bundle, one exact full-page screenshot, forbidden page methods 0, and second invocation reused with screenshot/Calendar/Telegram counts unchanged.
2. A direct-ID canonical acceptance using a separate fixture for `https://www.eventbrite.com/e/1997468673574`.
3. A fail-closed table covering invalid/mismatched event refs, non-www and uppercase raw hosts, HTTP, credentials, port, trailing slash, query, fragment, invalid/extra path, `pending`/`absent`, and current page mismatch/about:blank. Assert screenshot, Calendar, and Telegram effects exact 0.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
node --test apps/mr-bot/lib/connector-minimal-evidence.test.js
```

Expected: existing tests remain green; new positive Eventbrite cases fail at the missing provider contract. If the rejection table already passes because the provider is absent, perform the reversible canonical-guard mutation in Step 4.

- [ ] **Step 3: Add the minimum production wiring**

- Import `createEventbriteEvidenceStore`.
- Add exact Eventbrite event/receipt refs and a parser aligned to the existing `connector-eventbrite-workflow.js` event-path grammar. Reconstruct expected `https://www.eventbrite.com${pathname}`, require its embedded ID equals the event ref, and require raw/canonical exact equality with no credentials/port/query/hash.
- Instantiate the store, add provider map entry with states `["registered"]`, and include its `record` dependency validation.
- Treat Eventbrite like Doorkeeper at current-page capture, no-render, checkpoint receipt schema validation, and initial receipt/artifact readback boundaries.
- Do not change any shared downstream pipeline.

- [ ] **Step 4: Verify GREEN, mutation sensitivity, and adjacent stores**

```bash
node --test apps/mr-bot/lib/connector-minimal-evidence.test.js apps/mr-bot/lib/connpass-evidence-store.test.js
node --check apps/mr-bot/lib/connector-minimal-evidence.js
git diff --check
```

If the negative test was green before implementation, temporarily remove only Eventbrite's raw/canonical equality guard, run the named fail-closed test and prove at least one normalized variant reaches a forbidden downstream boundary or misses expected rejection, restore the guard, and rerun the full command.

- [ ] **Step 5: Self-review and report without commit**

Confirm exact two-file scope; both canonical path forms work; no Eventbrite navigation/replacement/render path exists; invalid identity/state/current URL causes zero screenshot/Calendar/Telegram effects; first persisted receipt/artifact is read before Calendar; no live effect occurred. Write RED/GREEN counts, mutation evidence, LOC, and concerns to the assigned report. Do not commit or push.
