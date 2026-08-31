# Doorkeeper Calendar Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the existing Google Calendar evidence pipeline to create an event for one exact canonical Doorkeeper event URL while rejecting normalized or ambiguous identities before `gog` executes.

**Architecture:** Extend only `connectorCanonicalUrl` in the existing gog Calendar adapter. Reuse the current strict raw/canonical equality pattern and unchanged create/idempotency/readback path; add one provider branch returning `sourceTitle: "Doorkeeper"`.

**Tech Stack:** Node.js CommonJS, `node:test`, injected `gog` runner.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/transport/calendar-gog.js` and `apps/mr-bot/lib/transport/transport-gog.test.js`.
- Production soft target: +8–15 LOC. Test soft target: +35–60 LOC. No new file, dependency, helper abstraction, state, or schema.
- Use strict TDD: the exact Doorkeeper create case and rejection table fail before the minimum production branch is added.
- Accept only exact `https://<lowercase-group>.doorkeeper.jp/events/<positive integer>` where group labels are lowercase ASCII letters/digits/hyphens, start/end alphanumeric, length 1–63, and group is not `www`.
- Reject HTTP, uppercase raw host, `www`, root host, nested subdomains, credentials, explicit port, query, fragment, trailing slash, nonnumeric/zero ID, extra path, and search/listing paths before injected `run` is called.
- The accepted `gog calendar create` argv must contain exact `--description=<url>`, exact `--source-url=<url>`, and the single fixed `--source-title=Doorkeeper`; preserve private idempotency property behavior.
- Preserve Luma, Peatix, Connpass, Meetup, Calendar receipt validation, argv-injection guards, readback, and every non-Connector Calendar method unchanged.
- Do not change provider discovery/action/readback, browser Harness, minimal evidence chain, native order, schedule, launchd, or live external systems.
- Luna owns production/test edits and RED/GREEN reporting. Sol owns review, SSOT, commit, push, and later official live acceptance.

---

### Task 1: Add strict Doorkeeper canonical URL handling to gog Calendar

**Files:**
- Modify: `apps/mr-bot/lib/transport/calendar-gog.js`
- Test: `apps/mr-bot/lib/transport/transport-gog.test.js`

**Interfaces:**
- Consumes: `createConnectorEvent({canonicalUrl:"https://tokyo-builders.doorkeeper.jp/events/101", ...})`.
- Produces: the unchanged provider receipt after one exact `gog calendar create`, with Doorkeeper source metadata.

- [ ] **Step 1: Write the failing acceptance and rejection tests**

Add one accepted URL test asserting returned receipt, exact source URL/description, fixed source title, and private idempotency property. Add one table test containing at least:

```js
[
  "http://tokyo-builders.doorkeeper.jp/events/101",
  "https://Tokyo-builders.doorkeeper.jp/events/101",
  "https://www.doorkeeper.jp/events/101",
  "https://doorkeeper.jp/events/101",
  "https://east.tokyo-builders.doorkeeper.jp/events/101",
  "https://tokyo-builders.doorkeeper.jp:443/events/101",
  "https://user:pass@tokyo-builders.doorkeeper.jp/events/101",
  "https://tokyo-builders.doorkeeper.jp/events/101/",
  "https://tokyo-builders.doorkeeper.jp/events/101?x=1",
  "https://tokyo-builders.doorkeeper.jp/events/101#details",
  "https://tokyo-builders.doorkeeper.jp/events/0",
  "https://tokyo-builders.doorkeeper.jp/events/not-a-number",
  "https://tokyo-builders.doorkeeper.jp/events/101/tickets",
  "https://tokyo-builders.doorkeeper.jp/events",
]
```

Assert every variant rejects with `connector calendar invalid` and injected `run` remains exact 0.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
node --test apps/mr-bot/lib/transport/transport-gog.test.js
```

Expected: only the newly added Doorkeeper acceptance is RED because the current fallback reaches Peatix rejection; all existing transport tests stay green. If the rejection table is already green, temporarily remove the planned exact raw-equality or group-boundary guard after implementation, prove the named negative test fails, then restore it and record that reversible mutation.

- [ ] **Step 3: Add the minimum provider branch**

Inside `connectorCanonicalUrl`, after Meetup and before the final Peatix fallback, add a strict Doorkeeper match and exact expected URL reconstruction. Require `raw === expected` and `url === expected`; reject `www`; return `{url: expected, sourceTitle:"Doorkeeper"}`. Do not alter shared canonicalization or any create/readback logic.

- [ ] **Step 4: Verify GREEN and adjacent evidence chain**

```bash
node --test apps/mr-bot/lib/transport/transport-gog.test.js apps/mr-bot/lib/connector-minimal-evidence.test.js
node --check apps/mr-bot/lib/transport/calendar-gog.js
git diff --check
```

Expected: all focused and adjacent tests pass, syntax/diff checks exit 0.

- [ ] **Step 5: Self-review and report without commit**

Confirm only the two owned files changed; every invalid identity causes `run` 0; exact accepted argv contains one Doorkeeper source title; existing providers and external state are unchanged. Write RED/GREEN commands, exact counts, LOC, reversible mutation result if used, and concerns to the assigned report file. Do not commit or push.
