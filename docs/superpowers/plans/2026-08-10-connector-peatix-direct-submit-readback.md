# Connector Peatix Direct Submit/Readback Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Execute every checkbox, preserve exact RED/GREEN evidence, and commit only the two owned Peatix browser-provider files.

**Goal:** Add a fail-closed Peatix browser provider that uses one supplied owned page to select one measured free ticket, complete only the measured standard attendee fields, click the single final application boundary once, and return success only after an exact same-event provider readback.

**Architecture:** Keep public discovery unchanged. A new script-first browser provider receives an already-normalized candidate carrying exact Peatix event and ticket identities plus a private in-memory attendee profile. It navigates `tickets → optional form → confirm`, rejects unknown required controls before final Submit, clicks `#confirm-button` at most once, then independently classifies the resulting same-event page as `registered`, `absent`, or `unavailable`. It creates no browser/session/target and stores no private values.

**Tech Stack:** Node.js CommonJS, `node:test`, Playwright-compatible supplied page API.

## Ponytail gate and measured contract

- **Reuse:** existing Peatix owned page, canonical event identity, exact ticket ID from public `get_view_data`, and the minimal runner's parent readback contract.
- **Measured live flow:** `/sales/event/<event-id>/tickets` exposes `input[name=number_of_tickets_<ticket-id>]` and `#next-button`; this candidate then uses `/form` with required attendee name, account email, and one organizer privacy consent; `/confirm` exposes the sole external boundary `#confirm-button` with text `チケットを申し込む`.
- **Do not build:** login/signup/CAPTCHA automation, generic form AI, new page/target/session, retry, evidence, Calendar, Telegram, production router, provider promotion, registry, or schedule.
- **Plan size:** add two files. Target production is about 90 LOC and the focused safety contract about 90 LOC; the external-effect regression coverage justifies exceeding the 100 total-LOC soft target.

## Global constraints

- Accept only `provider=peatix`, matching numeric IDs in `event_ref`, `canonical_url`, and `ticket_id`.
- Accept only free/open candidates (`registration_status=available`, `ticket_price_status=free`, `ticket_price_minor=0`).
- Accept only an in-memory profile with nonempty `name`, valid `email`, and explicit `accept_organizer_privacy=true`; never log or return values.
- Use exactly the supplied page. Calls to `newPage`, `browser.close`, target creation, or popup acceptance are forbidden.
- Before any Submit, read current provider state; an already registered event returns registered with click count 0.
- Ticket selection must be the exact selector `input[name=number_of_tickets_<ticket-id>]`, quantity exactly 1, then `#next-button`.
- On `/form`, fill only required fields whose labels normalize exactly to attendee name or email, and check only the measured organizer privacy confirmation. Any other required visible control returns `needs_fallback / unknown_required_field` before `#confirm-button`.
- On `/confirm`, require exact event ID in the HTTPS Peatix path and exact button id/text before one click.
- Success is never inferred from the click. `registered` requires an exact same-event completion/ticket marker; unchanged checkout is `absent`; ambiguous navigation/DOM is `unavailable`.
- All navigation and selector failures return privacy-safe reasons. No raw HTML, URL query, name, email, token, or exception text is returned.

---

### Task 1: Add the direct Peatix browser provider

**Files:**
- Create: `apps/mr-bot/lib/peatix-browser-provider.js`
- Create: `apps/mr-bot/lib/peatix-browser-provider.test.js`

- [ ] **Step 1: Write failing validation and idempotency tests**

Import the missing module and assert invalid provider/event/ticket identity, paid/closed candidate, missing profile consent, and page without the required API fail closed. Assert a supplied pre-readback of `registered` returns without navigation or click.

- [ ] **Step 2: Write the failing measured-flow test**

Use a compact fake page state machine for `tickets → form → confirm → complete`. Assert exact ticket selector, quantity `1`, exact name/email fields, organizer privacy radio, one form-confirm click, one final `#confirm-button` click, and final `{ status: "registered" }`. Assert private profile values never occur in the returned outcome.

- [ ] **Step 3: Write failing destructive-boundary regressions**

Cover unknown required form control, wrong ticket id, wrong confirm event identity, wrong final button text, and post-click ambiguous page. Assert final click count is 0 for all pre-submit failures and 1 only for the ambiguous post-click case; ambiguous post-click must not be reported as success.

- [ ] **Step 4: Write failing readback tests**

Cover exact same-event completion/ticket marker as `registered`, unchanged exact checkout as `absent`, cross-event marker as `unavailable`, and unrelated/auth page as `unavailable`. Exact event identity must be present in both the candidate and observed completion/ticket evidence.

- [ ] **Step 5: Run focused RED**

```bash
node --test apps/mr-bot/lib/peatix-browser-provider.test.js
```

Expected: module-not-found or missing exported functions; no network and no external write.

- [ ] **Step 6: Implement the minimum provider**

Export only `submitPeatixOnPage` and `readPeatixRegistrationStateOnPage`. Keep candidate/profile validation private, use bounded Playwright calls, and return frozen privacy-safe outcomes. Do not catch and expose raw browser errors.

- [ ] **Step 7: Run focused GREEN**

```bash
node --test apps/mr-bot/lib/peatix-browser-provider.test.js
```

Expected: all pass, zero failures, no external access.

- [ ] **Step 8: Commit and push Luna-owned files**

```bash
git add apps/mr-bot/lib/peatix-browser-provider.js \
  apps/mr-bot/lib/peatix-browser-provider.test.js
git commit -m "feat(connector): add Peatix direct browser provider"
git push origin feature/connector-native-completion
```

After Luna reports exact RED/GREEN evidence, a fresh Sol reviewer inspects the diff. Sol then extends the discovery workflow to carry ticket identity and delegates production routing in separate slices. No live final Submit occurs until the provider, workflow, router, and parent readback are wired to the official Connector entrypoint.
