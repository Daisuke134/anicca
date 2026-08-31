# Peatix evidence page reset plan

## Goal

Render the deterministic Peatix receipt on the already-owned page without waiting on Peatix's stuck `setContent` lifecycle, then continue the existing PNG, Calendar, Telegram, and immutable applied-bundle chain.

## Measured evidence

- Official schedule-unloaded wake `wake-8acecb7a754670f673321262` on pushed commit `aa61ffafb` completed Calendar and all provider discovery. Peatix was `100/100/87/55/18`.
- Candidate 1 parent pre-readback returned registered in 32 ms. Provider cache, direct action, Browser Harness, and all Peatix clicks were zero, proving the no-resubmit contract.
- `completeEvidence` then threw `Connector minimal pass unavailable` before any evidence file, Calendar write, Telegram delivery, wake report, or applied bundle. Baselines remained bundle 2, message receipt 3, photo receipt 2.
- An isolated owned-CDP-page diagnostic reproduced `page.setContent` timing out after 30 seconds on the registered Peatix page. `waitUntil: domcontentloaded` and an `about:blank` reset did not make `setContent` settle.
- On the same exact page, strict `about:blank` navigation followed by parent-owned `document.open/write/close` of the existing escaped `receiptHtml` succeeded; screenshot was a valid 16,901-byte PNG. The diagnostic created no file, Calendar event, Telegram delivery, or state row and closed its exact target.

## Ponytail full gate

- Reuse the existing owned page, escaped deterministic `receiptHtml`, screenshot validation, provider evidence store, Calendar idempotency, Telegram delivery, and immutable bundle writer.
- Add no browser target, renderer, library, service, retry loop, state schema, or provider abstraction.
- Change only the Peatix receipt-render step. Luma keeps its existing `setContent` path.
- The only allowed navigation is exact `about:blank` after parent registration authority has already been established. It cannot trigger a provider effect.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-evidence.test.js`
2. `apps/mr-bot/lib/connector-minimal-evidence.js`

Soft target: 2 files; production +12–22 LOC; tests +30–50 LOC.

### RED

1. A Peatix fixture whose `setContent` never settles must still complete through exact `goto("about:blank")`, parent-owned fixed receipt write, PNG, Calendar, Telegram, and `applied_bundle`; `setContent` call count remains zero.
2. Missing `goto`/`evaluate`, reset failure, non-`about:blank` readback, receipt-write throw, false receipt validation, invalid PNG, or provider mismatch fails before store/Calendar/Telegram/bundle.
3. The rendered HTML contains only escaped provider/status/event reference and no title, attendee identity, ticket/QR payload, canonical URL, or private values.
4. Existing Luma evidence continues to use `setContent`, with no `goto` or DOM-write behavior change.

### GREEN

- For provider `peatix` only, require `page.goto`, `page.url`, and `page.evaluate`; navigate exact `about:blank` with `waitUntil: domcontentloaded`, 30-second timeout, and verify exact URL readback.
- Parent-write the already generated `receiptHtml` with `document.open/write/close` and return a strict boolean proving the expected receipt skeleton exists before screenshot.
- Keep the existing screenshot signature/size, immutable provider receipt, Calendar create/readback, Telegram message/photo, and bundle gates unchanged.

## Verify

- Focused minimal evidence suite, minimal runner/production, Peatix provider/workflow/Harness, native entrypoint adjacent suites, changed-file syntax, and `git diff --check`.
- Fresh Sol review focused on parent-owned HTML, navigation scope, privacy, Luma non-regression, duplicate external effects, and partial-side-effect ordering.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded wake. Acceptance is pre-submit `registered`, zero Peatix clicks, one evidence/Calendar/message/photo increment, and one durable `applied_bundle` with exact cleanup.

## Result

- Luna reproduced RED on the clean starting diff: a never-settling Peatix `setContent` exceeded the 250 ms test bound, and missing reset APIs did not fail before downstream effects.
- GREEN changes only `connector-minimal-evidence.js` and its test. Peatix now resets the already-owned page to exact `about:blank`, verifies the URL, parent-writes the existing escaped `receiptHtml`, validates the exact three-pair receipt skeleton, then resumes the unchanged screenshot/evidence/Calendar/Telegram/bundle chain. Luma keeps `setContent`.
- Luna focused evidence was 8/8 and adjacent was 83/83. Sol independently ran the expanded Peatix/Harness/native-entrypoint set at 116/116; changed-file syntax and `git diff --check` passed.
- Fresh Sol review found no Critical or Important issue and returned `ship`. No browser, provider, Calendar, evidence, Telegram, profile, state, launchd, or schedule side effect occurred during implementation and test.
- Live acceptance remains the next step after push: the official schedule-unloaded wake must observe registered before submit, perform zero Peatix clicks, and persist one complete durable `applied_bundle` with exact cleanup.
