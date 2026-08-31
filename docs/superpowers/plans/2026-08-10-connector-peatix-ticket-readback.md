# Peatix registered-ticket readback plan

## Goal

Recognize the measured Peatix post-registration ticket state by exact event identity so an already successful registration is never submitted again and can continue through Calendar, PNG, Telegram, and the durable applied bundle.

## Measured evidence

- Official schedule-unloaded wake `wake-877cc479184926f7e70c1d65` on pushed commit `45614f420` completed Calendar and all provider discovery. Peatix audit was `100/100/87/55/18`.
- Candidate 1 direct action returned non-completed, then the Browser Harness ran 35,195 ms. The wake stopped immediately as `circuit_open / effect_unknown / 1`; Telegram provider ID `10906`; no second candidate navigation or submit occurred.
- A dedicated read-only CDP target found one new authenticated dashboard ticket for event `5075819`, proving the final external effect succeeded. No Calendar evidence or applied bundle was created.
- The exact ticket page is `https://peatix.com/event/5075819/ticket` and contains one `body.webticket`, one `section.ticket`, one `#qr-code img.js-qrcode-image`; the public ticket ID is not present in the DOM.
- The exact canonical event page `https://peatix.com/event/5075819` contains one browser-visible link to `https://peatix.com/event/5075819/ticket`, zero checkout controls, and zero legacy registration markers. The current parent reader recognizes neither real success shape, so the bounded settlement correctly ended `effect_unknown`.

## Ponytail full gate

- Reuse `readPeatixRegistrationStateOnPage`, its strict Peatix URL checks, existing normalized `registered|absent|unavailable` output, and the live-measured DOM. Add no new browser, provider, retry, model call, state, cache, or evidence path.
- Registration is an event-level external effect. Bind success to the exact candidate event ID; do not invent a ticket-ID marker that Peatix does not expose.
- Do not click, submit, open Calendar, or create evidence during implementation/tests. The next external action is one official schedule-unloaded foreground wake after review and push.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/peatix-browser-provider.test.js`
2. `apps/mr-bot/lib/peatix-browser-provider.js`

Soft target: 2 files; production +15–25 LOC; tests +35–55 LOC.

### RED

1. Exact authenticated `/event/<same-id>/ticket` with exactly one `body.webticket`, `section.ticket`, and `#qr-code img.js-qrcode-image` returns `registered`.
2. Exact authenticated canonical `/event/<same-id>` with exactly one browser-visible exact same-event `/ticket` anchor returns `registered` before any submit path.
3. Alternate provider target, authentication redirect, missing or duplicated ticket markers, hidden or zero-size ticket link, competing event link, or checkout controls cannot become registered.
4. The existing unregistered canonical/tickets/form/confirm states remain `absent` or `unavailable` exactly as before, and a pre-registered state makes direct submission an idempotent no-op with final click count zero.

### GREEN

- Extend the parent observation with only privacy-safe booleans/counts for the measured canonical-ticket link and ticket-page shell.
- Return `registered` only when the current strict URL and the corresponding exact measured DOM contract match the same candidate event ID and authentication is intact.
- Preserve legacy explicit markers and every existing failure code. Do not expose title, attendee identity, QR payload, ticket contents, URL query, or DOM text.

### Fresh review fix-first amendment

Fresh review reproduced that a malformed observation with `markers: ""` can satisfy `markers.length === 0` and fabricate `registered` when paired with ticket-shell booleans; an absent `markers` field throws `TypeError`. Before either measured ticket/canonical success branch, require `Array.isArray(observed.markers)`. Add RED cases for string, object, null, and missing markers; all must return privacy-safe `unavailable` without throwing, submitting, or unlocking downstream evidence. Preserve the valid empty-array success case and legacy exact marker handling.

## Verify

- Focused Peatix provider suite, Peatix workflow, production Harness, minimal production/runner/native entrypoint adjacent suites, changed-file syntax, and `git diff --check`.
- Fresh Sol review focused on false registered states, event mismatch, idempotency, privacy, and duplicate external effects.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded wake. Acceptance is pre-submit parent `registered` with no new Peatix click, followed by Calendar/PNG/Telegram and one durable `applied_bundle`; otherwise stop at the exact safe boundary and re-diagnose without another final click.

## Result

- RED reproduced both missing live success shapes: the ticket shell returned `unavailable`, while the canonical event page advanced toward another submit. The strict negative matrix already failed closed.
- GREEN added only the measured event-level parent readback contract. Provider 16/16 and named adjacent 83/83 passed; an isolated read-only live call on canonical event `5075819` returned exact `registered` with no submit.
- Fresh review found malformed `markers` could either fabricate registration or throw. The fix added an array schema guard before every measured/legacy length branch and regressions for string/object/null/missing payloads.
- Final provider 17/17, expanded relevant 108/108, syntax, and `git diff --check` passed. Serialized full Connector regression was 308/311; the three failures reproduce on clean HEAD (two stale provider-cursor expectations and one required-email fixture). One default-concurrency synthetic 100 ms navigation fixture was transient under load and passed alone in 11 ms and in the serialized suite.
- Fresh Sol re-review: Critical 0, Important 0, `ship`.
