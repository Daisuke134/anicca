# Connector Peatix Bounded Search Coverage Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Execute every checkbox, preserve actual RED/GREEN evidence, and commit only the two owned Peatix files.

**Goal:** Replace Peatix DOM-render readiness with the measured public `/search/events` response contract and scan exactly five 20-result pages inside the current 14-day Tokyo date route, so discovery sees at most 100 unique event identities without transient false-zero results.

**Architecture:** The existing discovery workflow remains discovery-only. Before each same-page search navigation it registers a bounded `waitForResponse`, accepts only the matching Peatix JSON response for that page, extracts public event IDs, and stops after five pages or the first short page. Existing detail JSON normalization, free/open gates, Calendar overlap, and aggregate audit remain unchanged.

**Tech Stack:** Node.js CommonJS, `node:test`, Playwright-compatible page/response API, existing Tokyo date utilities.

## Ponytail gate and measured contract

- **Remove:** `a.event-card` / `.no-results` as readiness or identity sources. Live probing proved `.no-results` can exist transiently before a non-empty XHR finishes.
- **Reuse:** existing `createPeatixDiscoveryWorkflow`, strict `json_data.event`, ticket gates, candidate window, Calendar gate, and safe stage errors.
- **Measured request:** `/search/events?...&dr=range&dr_from=YYYY-MM-DD&dr_to=YYYY-MM-DD&p=N&size=20` returns `application/json` with `json_data.numFound`, `page`, and `events[]`; each event exposes a positive integer `id`.
- **Measured route:** public page query `dr=YYYY-MM-DD:YYYY-MM-DD` becomes the XHR `dr=range/dr_from/dr_to`. Five measured pages each returned 20 events; bounded probing found multiple free/open/Calendar-free identities.
- **Do not build:** direct API client outside the page, pagination cursor persistence, ranking, submit, login/OTP, readback, evidence, production router, registry promotion, schedule, retry, or new module.
- **Plan size:** modify two existing files. Target net production change is under 80 LOC; tests add only response ordering/contract and zero-result regression coverage.

## Global constraints

- Production provider order remains exactly `Luma → Connpass`.
- One supplied owned page, one target, one session; no new page/target/browser and no external write.
- Today-inclusive 14 Tokyo calendar days remains the final acceptance gate.
- Search route uses today through day 13 as the UI date range; final candidate window still rejects any source drift.
- Register `waitForResponse` before `goto` for each page.
- Match exact HTTPS host `peatix.com`, path `/search/events`, requested page `p`, and `size=20`; validate HTTP success, JSON wrapper, payload page, and at most 20 events.
- Extract only exact positive integer IDs and construct `peatix-event://event/<id>` / `https://peatix.com/event/<id>`.
- Preserve page/event order and deduplicate globally; fail if more than 100 unique identities.
- Stop after page 5 or when a response contains fewer than 20 events.
- A valid page-1 response with `events: []` is successful discovery and emits one frozen five-zero audit.
- Navigation/response/JSON/contract failures map to existing safe `PEATIX_SEARCH_*_FAILED` codes without raw error or payload leakage.
- Existing detail/free/open/Calendar behavior must not change.

---

### Task 1: Use the measured search response and scan five bounded pages

**Files:**
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.js`
- Modify: `apps/mr-bot/lib/connector-peatix-workflow.test.js`

- [ ] **Step 1: Write the failing response-before-navigation test**

Change the default-reader fake page to expose `waitForResponse`. Record call order and provide a fake response with exact URL, status/ok contract, and:

```js
{
  json_data: {
    page: 1,
    events: [{ id: 201 }, { id: 202 }],
  },
}
```

Assert `waitForResponse` is registered before `goto`, the predicate accepts only `https://peatix.com/search/events?...&p=1&size=20`, and detail navigation still uses the same page in response order. Assert the search route contains the exact Tokyo range derived from the injected `now` and `p=1`.

- [ ] **Step 2: Write the failing five-page/100-unique test**

Return 20 unique positive IDs for each payload page 1–5 and safe details for all 100. Assert:

- exactly five response registrations and five search navigations;
- 100 detail reads in page/event order;
- no page 6 request;
- result ordering remains source ordering after the existing eligibility gates.

Use compact generated fixtures; do not hand-write 100 event objects.

- [ ] **Step 3: Write the failing short-page and true-zero tests**

For a 20-event first page and 3-event second page, assert page 3 is not requested. For a valid page-1 `events: []` payload, assert result is frozen `[]` and `onDiscoveryAudit` is called exactly once with:

```js
{
  observed_count: 0,
  normalized_count: 0,
  window_count: 0,
  free_open_count: 0,
  calendar_free_count: 0,
}
```

No DOM selector is part of either test.

- [ ] **Step 4: Write the failing response-contract safety tests**

Cover wrong payload page, more than 20 events, missing `json_data.events`, invalid/non-positive ID, non-success HTTP response, JSON rejection, and response timeout. Assert only existing safe search stage codes/messages are exposed. Keep the existing injected `readSearchBindings` 101-unique versus 101-duplicate contract tests.

- [ ] **Step 5: Run focused test and verify RED**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js
```

Expected: failures because the current default reader has no `waitForResponse`, no date/page loop, and still reads DOM cards.

- [ ] **Step 6: Implement the minimal response reader**

Move the single `observed = now()` call before search discovery and pass it as a second argument to `readSearchBindings(page, observed)`. Build the Tokyo day-0/day-13 route deterministically. For page 1 through 5:

1. create the exact response promise;
2. navigate on the supplied page;
3. await and validate response URL/status/JSON/page/events;
4. append canonical IDs in response order with global dedupe;
5. stop on a short page.

Delete `SEARCH_RESULT_SELECTOR`, `waitForSelector`, and search DOM evaluation. Keep detail navigation/evaluation unchanged.

- [ ] **Step 7: Run focused and provider regression GREEN**

```bash
node --test apps/mr-bot/lib/connector-peatix-workflow.test.js

node --test \
  apps/mr-bot/lib/connector-peatix-workflow.test.js \
  apps/mr-bot/lib/connector-connpass-workflow.test.js \
  apps/mr-bot/lib/connector-luma-workflow.test.js \
  apps/mr-bot/lib/connector-minimal-runner.test.js
```

Expected: all pass, zero failures, no external access from tests.

- [ ] **Step 8: Commit and push the Luna-owned fix**

```bash
git add apps/mr-bot/lib/connector-peatix-workflow.js \
  apps/mr-bot/lib/connector-peatix-workflow.test.js
git commit -m "fix(connector): use bounded Peatix search responses"
git push origin feature/connector-native-completion
```

After Luna reports evidence, a fresh Sol reviewer inspects the exact diff. Sol then runs the official one-target read-only workflow with real Calendar inventory. This task is complete only when the audit observes nonzero normalized source rows without transient zero and the owned target/locks are cleaned. Peatix remains outside production provider order until submit/readback/evidence succeeds.
