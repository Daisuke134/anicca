# Connector Peatix Public Discovery Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Implement this plan one checkbox at a time, preserve RED/GREEN evidence in the task report, and commit only the two owned files.

**Goal:** Add a discovery-only Peatix workflow that turns public Tokyo search results and Peatix public event JSON into the same strict 14-day/free/open/Calendar-free candidate contract as the existing providers. This slice must not submit, mutate Peatix, change production provider order, or claim Peatix production support.

**Architecture:** One Connector-owned Playwright page opens the public Peatix Tokyo/free search, extracts bounded canonical event identities, and reads each event's same-origin `/get_view_data` JSON. One module validates and normalizes those public values, applies the existing ordered eligibility gates, and emits privacy-safe aggregate counts. No new target, session, service, dependency, cache, persistence layer, or registry promotion is introduced.

**Tech Stack:** Node.js CommonJS, `node:test`, existing `zonedSlotInstant`, Playwright-compatible page API.

## Ponytail gate and measured contract

- **Do not build:** submit/fill/readback, account/OTP handling, evidence persistence, production router wiring, provider registry promotion, schedule, ranking, retry, agent fallback, database, or new abstraction.
- **Reuse:** the existing Connector candidate schema, Tokyo 14-day window semantics, Calendar overlap rule, stage-safe error pattern, and owned-page injection pattern from `connector-connpass-workflow.js`.
- **Measured public source:** search cards expose canonical `/event/<id>` links; each event page exposes same-origin `/event/<id>/get_view_data`; the JSON contains `event.status`, `isOpen`, `isFinished`, `datetime`, `datetimeEnd`, and `tickets[]` with `id`, `price`, `status`, `seatsAvailable`, and optional `salesEnds.datetime`.
- **Exact ticket gate:** a usable free ticket has `price === 0`, `status === 10`, integer `seatsAvailable > 0`, and no expired `salesEnds.datetime`. An observed `price: 0 / status: 100 / seatsAvailable: 0` ticket is closed and must never qualify.
- **Plan size:** two new files. Target production implementation is about 100 LOC; tests may exceed the soft LOC target because public JSON fixtures must retain all values that protect paid/closed/expired boundaries. No third module is justified for this slice.

## Global constraints

- Production provider order remains exactly `Luma → Connpass`; `DEFAULT_PROVIDERS` is unchanged.
- Search is bounded to at most 100 unique canonical event links and discovery result to at most 100 candidates.
- Use exact identities `peatix-event://event/<positive integer>` and `https://peatix.com/event/<positive integer>`.
- Parse Peatix wall-clock values as `Asia/Tokyo`; reject missing, invalid, or non-increasing intervals.
- Preserve source order and deduplicate by event identity.
- The acceptance window is today-inclusive 14 Tokyo calendar days.
- Calendar overlap uses `[start,end)` semantics and supports the existing array or `{ busy_intervals }` input.
- Emit only five aggregate integers: `observed_count`, `normalized_count`, `window_count`, `free_open_count`, `calendar_free_count`.
- Public navigation/read/validation failures expose only exact safe codes, never browser errors or page content.
- Connector Native, healthcheck, and Healer remain unloaded.

---

### Task 1: Implement the Peatix discovery-only workflow

**Files:**
- Create: `apps/mr-bot/lib/connector-peatix-workflow.js`
- Create: `apps/mr-bot/lib/connector-peatix-workflow.test.js`

**Exported interface:**

```js
const { createPeatixDiscoveryWorkflow } = require("./connector-peatix-workflow.js");

const workflow = createPeatixDiscoveryWorkflow({
  now,
  readSearchBindings, // optional test seam; receives the same owned page
  readEventViewData, // optional test seam; receives the same owned page and canonical URL
  isCalendarFree,    // optional existing Calendar contract
  onDiscoveryAudit,  // optional privacy-safe aggregate callback
});

await workflow.discoverCandidates({ page, calendar });
```

- [ ] **Step 1: Write the failing normalization and eligibility test**

Create a hand-checked fixture in source order containing: one event outside the 14-day window; one paid event; one `price: 0` ticket with `status: 100` and zero seats; one expired free ticket; one open free ticket that conflicts with Calendar; and one eligible open free ticket. Inject `readSearchBindings` and `readEventViewData`, then assert the result contains only the final candidate with exact provider, event ref, canonical URL, title, ISO start/end, `registration_status: "available"`, `ticket_price_status: "free"`, and `ticket_price_minor: 0`.

The test must assert every reader call receives the exact same `page` object and source ordering is preserved.

- [ ] **Step 2: Write the failing ordered audit test**

Capture `onDiscoveryAudit` once and assert exact monotonic counts from a minimal fixture:

```js
assert.deepEqual(audits, [{
  observed_count: 6,
  normalized_count: 6,
  window_count: 5,
  free_open_count: 2,
  calendar_free_count: 1,
}]);
```

`free_open_count` is after all event and free-ticket gates, including ticket status, inventory, and sales deadline.

- [ ] **Step 3: Write the failing bounded default-reader and safe-error tests**

Using a fake page with `goto` and `evaluate`, assert the default flow:

1. navigates once to `https://peatix.com/search?q=%E7%84%A1%E6%96%99&country=JP&l.text=Tokyo`;
2. extracts only canonical `https://peatix.com/event/<id>` identities, deduplicated in DOM order;
3. navigates to each event on the same page and reads that event's `/get_view_data` JSON;
4. rejects more than 100 bindings with `PEATIX_SEARCH_ROWS_CONTRACT_FAILED`;
5. maps navigation, search read, detail read, identity mismatch, candidate validation, and Calendar check failures to distinct `PEATIX_*_FAILED` codes without leaking the injected private error message.

- [ ] **Step 4: Run the new test and verify RED**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js
```

Expected: FAIL because `connector-peatix-workflow.js` does not exist.

- [ ] **Step 5: Implement the minimal workflow**

Implement only the exported factory and private helpers required by the tests:

- validate the owned `page` and injected functions;
- default search reader evaluates `a.event-card`, bounds to 100, canonicalizes exact event IDs, and deduplicates;
- default detail reader navigates on the same page and uses same-origin `fetch(`${canonicalUrl}/get_view_data`)` inside `page.evaluate`;
- validate `json_data.event.id` matches the binding identity;
- normalize Peatix `datetime`/`datetimeEnd` as Tokyo instants;
- derive available/free only from an event that is `OPEN`, `isOpen === true`, `isFinished !== true`, and has at least one exact usable free ticket;
- apply window, then free/open, then Calendar gates and call `onDiscoveryAudit` exactly once after successful discovery, including zero results;
- freeze returned arrays/candidates/audit and expose only safe stage errors.

Do not export reader internals, persist public JSON, or add direct-action/readback placeholders.

- [ ] **Step 6: Run focused GREEN**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js
```

Expected: all tests pass with zero failures.

- [ ] **Step 7: Run provider regression**

```bash
node --test \
  apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/connector-connpass-workflow.test.js \
  apps/mr-bot/lib/connector-luma-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

Expected: all tests pass, production provider order tests remain unchanged, and no test performs an external write.

- [ ] **Step 8: Commit the Luna-owned implementation**

```bash
git add apps/mr-bot/lib/connector-peatix-workflow.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js
git commit -m "feat(connector): add Peatix public discovery"
```

After Luna reports RED/GREEN and the commit, a fresh Sol reviewer inspects the exact diff. Sol then runs focused regression and an isolated read-only live discovery using one official Connector-owned browser target. Only after the live audit proves the contract does Sol plan the separate Peatix submit/readback/evidence slice. Peatix remains absent from production provider order during this task.
