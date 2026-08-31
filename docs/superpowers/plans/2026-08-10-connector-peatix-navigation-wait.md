# Peatix exact navigation wait plan

## Goal

Close the first live Peatix application boundary observed in `wake-d6050c563e395e783ba6b2c7`: a successful ticket selection click must wait for the exact same-event `/form` URL before the direct provider inspects the form. Apply the same rule to the existing form-to-confirm transition so the next boundary is not hidden by the same timing defect.

## Measured evidence

- Official foreground runner used pushed commit `96bd8e36a`, with scheduling and all Connector launchd labels unloaded.
- Calendar, Luma, Connpass, and Peatix discovery actions succeeded. Peatix observed/normalized/window/free-open/calendar-free counts were `100/100/87/56/18`.
- Three Peatix direct attempts returned after `987ms`, `707ms`, and `367ms`; the final report was `circuit_open / peatix_form_navigation_failed / 3`.
- Current production code clicks `#next-button` and immediately reads `page.url()` without awaiting navigation. The synchronous unit fixture cannot reproduce the live timing.
- The fallback then saw the ticket page at step 1 (`control_4`, `control_5`, `control_12`), selected `control_12`, and saw the larger form control set at step 2. This confirms the click eventually navigated and the direct check ran too early.

## Ponytail full gate

- Do not add a new agent, browser rail, cache, state field, provider abstraction, or retry loop.
- Reuse Playwright's existing `page.waitForURL` and the existing strict `stepUrl` identity predicate.
- Keep candidate eligibility, ticket identity, final-click validation, readback, evidence, and scheduling unchanged.

## Implementation slice

Files owned by Luna:

1. `apps/mr-bot/lib/peatix-browser-provider.test.js`
2. `apps/mr-bot/lib/peatix-browser-provider.js`

Soft target: 2 implementation files; production +15–25 LOC; tests +20–35 LOC.

### RED

Add an asynchronous-navigation fixture where `#next-button` and `#form-submit-button` change the page URL only after the click promise begins. The old immediate `page.url()` check must fail the measured happy path. Keep or add a wrong-event navigation assertion proving no later form/final action occurs.

### GREEN

Add one private helper that starts an exact `page.waitForURL` before clicking, waits for `domcontentloaded`, uses the existing bounded 30-second timeout, and returns true only when `stepUrl(page.url(), candidateId, expectedStep)` is exact. Use it for tickets-to-form and form-to-confirm. Missing `waitForURL`, timeout, wrong host/event/step, query, or fragment must fail closed with the existing safe reason.

### Verify

- `node --test apps/mr-bot/lib/peatix-browser-provider.test.js`
- Adjacent Peatix workflow, production factory/harness, minimal runner, and native entrypoint tests.
- `node --check` for modified JavaScript.
- `git diff --check`.
- Fresh Sol correctness review, then SSOT update, commit, push, and one official foreground wake with schedule unloaded.

## Result

- RED reproduced the live defect: delayed ticket navigation returned `form_navigation_failed` under the old immediate URL check.
- GREEN starts the strict `waitForURL` before each click and validates the same event and expected `/form` or `/confirm` step after `domcontentloaded` within 30 seconds.
- Missing `waitForURL` and wrong-event navigation fail closed before later form/final actions.
- Luna: provider 13/13 and planned adjacent 72/72 PASS. Sol: expanded adjacent 75/75 PASS, both JavaScript syntax checks PASS, `git diff --check` PASS.
- Fresh Sol review: `ship` (Critical 0, Important 0).
- Final implementation diff: provider +11/-4, tests +29/-2. No browser, model, provider submit, Calendar, evidence, Telegram, state/profile, schedule, or launchd action occurred during implementation or test.
