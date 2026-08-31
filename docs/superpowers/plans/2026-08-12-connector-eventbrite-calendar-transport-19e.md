# Eventbrite Calendar Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the existing gog Calendar evidence pipeline to create events for the two canonical Eventbrite event URL forms while rejecting normalized or ambiguous identities before `gog` executes.

**Architecture:** Extend only `connectorCanonicalUrl` in the existing Calendar adapter. Match the current Eventbrite workflow path grammar, reconstruct the exact expected URL, require raw/canonical equality, and return fixed `sourceTitle:"Eventbrite"`; reuse the unchanged create/idempotency/readback path.

**Tech Stack:** Node.js CommonJS, `node:test`, injected `gog` runner.

## Global Constraints

- Modify exactly `apps/mr-bot/lib/transport/calendar-gog.js` and `apps/mr-bot/lib/transport/transport-gog.test.js`.
- Production soft target: +8–16 LOC. Test soft target: +45–75 LOC. No new file, dependency, helper abstraction, state, or schema.
- Use strict TDD: both accepted Eventbrite URL forms fail before the minimum branch is added.
- Accept exact `https://www.eventbrite.com/e/<slug>-tickets-<positive ID>` and exact `https://www.eventbrite.com/e/<positive ID>`, using the same slug grammar as `connector-eventbrite-workflow.js`.
- Reject HTTP, non-www/wrong/subdomain host, uppercase raw host, credentials, explicit port, query, fragment, trailing slash, invalid/zero ID, slug without `-tickets-`, extra path, and listing/search paths before injected `run`.
- Each accepted `gog calendar create` argv must contain exact description/source-url, a single fixed `--source-title=Eventbrite`, and the unchanged private idempotency property.
- Preserve Luma, Peatix, Connpass, Meetup, Doorkeeper, Calendar receipt validation, argv guards, and all non-Connector methods unchanged.
- Do not change Eventbrite workflow/Harness, minimal evidence chain, native order, launchd, schedule, or live state.
- Luna owns production/test edits and RED/GREEN reporting. Sol owns review, SSOT, commit, push, and later official wake.

---

### Task 1: Add strict Eventbrite canonical URL handling to gog Calendar

**Files:**
- Modify: `apps/mr-bot/lib/transport/calendar-gog.js`
- Test: `apps/mr-bot/lib/transport/transport-gog.test.js`

- [ ] **Step 1: Write failing accepted/rejected URL tests**

Add one accepted test looping over:

```js
[
  "https://www.eventbrite.com/e/tokyo-free-event-tickets-1997468673573",
  "https://www.eventbrite.com/e/1997468673574",
]
```

For each, assert returned receipt, exact description/source-url, exactly one source title `Eventbrite`, and private idempotency property.

Add a rejection table with at least HTTP, root host, wrong subdomain, uppercase raw host, credentials, `:443`, query, fragment, trailing slash, zero/nonnumeric ID, slug without `-tickets-`, extra path, listing URL, and search URL. Assert every rejection is `connector calendar invalid` and total injected `run` calls are 0.

- [ ] **Step 2: Verify RED**

```bash
node --test apps/mr-bot/lib/transport/transport-gog.test.js
```

Expected: existing tests stay green and the new accepted Eventbrite test fails at the Peatix fallback; the rejection table may already pass for an unknown provider.

- [ ] **Step 3: Add the minimum Eventbrite branch**

After Doorkeeper and before final Peatix fallback, match exact `www.eventbrite.com` and the current workflow's two event paths. Reconstruct `https://www.eventbrite.com${pathname}`, require `raw === expected` and canonicalized `url === expected`, and return `{url:expected, sourceTitle:"Eventbrite"}`. Do not alter shared URL canonicalization or create/readback code.

- [ ] **Step 4: Verify GREEN and guard sensitivity**

```bash
node --test apps/mr-bot/lib/transport/transport-gog.test.js apps/mr-bot/lib/connector-minimal-evidence.test.js
node --check apps/mr-bot/lib/transport/calendar-gog.js
git diff --check
```

If the rejection table was green before implementation, temporarily remove only Eventbrite raw equality, prove the named rejection test fails with a positive `run` count for normalized raw variants, restore the guard, and rerun the full command.

- [ ] **Step 5: Self-review and report without commit**

Confirm exact two-file scope, both URL forms accepted, all rejected variants cause `run` 0, fixed source title occurs exactly once, existing providers unchanged, and external live effects 0. Write RED/GREEN counts, mutation evidence, LOC, and concerns to the assigned report. Do not commit or push.
