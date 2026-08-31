# Peatix Calendar self-recovery plan

## Goal

Let an already-registered Peatix candidate re-enter the evidence path when the only Calendar overlap is the Connector event created for that same canonical URL, while every unrelated overlap remains blocking.

## Measured boundary

- Official wake `wake-b6e743b9f56f32f6137b2298` on pushed commit `3f398e535` observed Peatix registered with zero submit and created exactly one Google Calendar event carrying private property `lm_connector_event=<sha256(canonical URL)>`.
- The initial evidence call did not reach a bundle. Read-only lookup proves exactly one Calendar event for the private idempotency value.
- A production-equivalent Telegram message retry returned positive ID `10946`; the privacy-safe receipt PNG send returned positive ID `10949`. These diagnostics prove both transports but are not an applied bundle acceptance.
- Recovery wake `wake-d66a62d5c9221ead4175454b` did not rediscover the registered event because its own Calendar event was treated as an ordinary conflict. It tried later candidates and stopped `circuit_open / effect_unknown`; bundle remained 2. This proves the missing boundary is discovery recovery, not provider, Calendar, or Telegram capability.
- Real gog readback exposes the Connector marker only at `extendedProperties.private.lm_connector_event`; the value is the expected 64-character lowercase SHA-256 and contains no title, URL, attendee, or calendar identity.

## Ponytail full gate

- Reuse the existing Google busy inventory, existing private Calendar property, existing Peatix calendar-free gate, and existing evidence idempotency hash.
- Add no continuation file, state schema, recovery service, provider registry, retry loop, schedule, browser target, or new external action.
- Three files are the minimum complete slice: busy inventory production, Peatix workflow production, and one combined contract test file. A separate inventory test file is deliberately avoided.
- Expose only the validated idempotency hash on a busy interval. Do not expose Calendar title, URL, location, account, provider receipt, or raw extended properties.
- Ignore an overlapping interval only when its validated marker exactly equals SHA-256 of the candidate's strict canonical URL. Any other or malformed overlap still blocks.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/google-calendar-busy-inventory.js`
2. `apps/mr-bot/lib/connector-peatix-workflow.js`
3. `apps/mr-bot/lib/connector-peatix-workflow.test.js`

Soft target: 3 files; production +12–24 LOC; tests +25–45 LOC.

### RED

1. A real-shaped raw Google event with valid `extendedProperties.private.lm_connector_event` produces a verified timed busy interval carrying only `connector_idempotency` plus existing safe fields.
2. Peatix discovery includes a candidate when its only overlap has the exact candidate URL hash.
3. The same candidate remains blocked when any second unrelated timed overlap exists.
4. Missing, uppercase, short, non-string, or wrong hash never bypasses a conflict; malformed raw Connector marker fails the verified inventory closed.
5. No raw URL/title/location/account/private-property object appears in the public busy interval.
6. On an active event, present-invalid `extendedProperties` or `private` containers (primitive, null, or array) fail the verified inventory closed; genuinely absent containers remain marker-free and valid.
7. Cancelled or transparent events are excluded before Connector marker parsing, so a malformed marker on an otherwise excluded event does not invalidate the inventory.

### GREEN

- Exclude cancelled and transparent events before parsing any Connector marker, preserving the existing exclusion contract.
- Parse the Connector marker from the exact raw Calendar private-property location; distinguish genuinely absent containers from present-invalid containers, accept absent or exact lowercase SHA-256 only, and reject malformed active-event shapes/values.
- Add `connector_idempotency` only for a valid marker on timed/all-day intervals; preserve all existing interval fields and verification.
- In Peatix `defaultCalendarFree`, compute SHA-256 of the already strict canonical URL and ignore only overlapping timed intervals with an exact matching marker.
- Preserve all existing candidate order, free/open/window gates, audit counts, and unrelated Calendar conflict behavior.

## Verify

- Focused Peatix workflow tests including real busy-inventory composition; busy inventory existing suite; minimal production/runner/evidence; Peatix provider/Harness; native entrypoint; changed-file syntax; `git diff --check`.
- Fresh Sol review for privacy, hash identity, malformed marker behavior, unrelated overlap safety, candidate canonicalization, and duplicate external effects.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded recovery wake. Acceptance is original event pre-submit registered, provider clicks zero, Calendar create zero/readback one, positive Telegram message/photo IDs, one new durable applied bundle, exact cleanup.

## Result

- Luna measured RED at 16/19: valid marker was absent from the safe inventory, same-event overlap still removed the candidate, and malformed marker values were not rejected. Existing sixteen workflow tests remained green.
- Initial GREEN changed only the planned three files and passed focused 19/19; Sol expanded was 122/122. Fresh Sol review then found two Important shape/order defects: active present-invalid containers were treated as absence, and excluded events parsed markers too early.
- The plan was tightened before the fix. Luna reproduced both findings at 18/20, then distinguished genuine absence from present-invalid containers and moved cancelled/transparent exclusion ahead of marker parsing.
- Final focused workflow is 20/20; busy inventory 3/3, evidence 8/8, minimal production/runner 25/25, provider/Harness 59/59, Sol expanded 123/123, changed-file syntax, and `git diff --check` all pass. The two native cursor failures are unchanged clean-HEAD baselines outside this slice.
- Fresh Sol re-review found no Critical or Important issue and returned `ship`. No browser, provider, Calendar, evidence, Telegram, state, profile, launchd, or schedule side effect occurred during implementation and test.
- Live acceptance remains the next step after push: the original registered event must re-enter discovery only through its exact hash marker, submit zero times, reuse the one Calendar event, produce positive Telegram message/photo IDs, persist one new applied bundle, and clean up exactly.

## Live acceptance

- Official schedule-unloaded wake `wake-57a417724891bb095e4b864b` on pushed commit `ae8837498` exited 0 with `applied_bundle`.
- The original `peatix-event://event/5075819` re-entered discovery through the exact same-event hash, parent readback returned registered in 17 ms, and provider cache/direct/Harness submit actions were all zero.
- The private idempotency readback returns exactly one Google Calendar event; no duplicate create occurred. The bundle stores that event ID and independent readback timestamp.
- Bundle count increased 2 to 3. The new immutable mode-0600 bundle references the mode-0600 16,901-byte PNG whose measured SHA-256 exactly matches the bundle.
- Evidence Telegram message ID is `10971`, photo ID is `10973`, and every-wake report delivery ID is `10975`; all are positive. Process and lock are absent, target lease is empty, CDP remains healthy, Git is clean, and upstream is 0/0.
- This closes Item 10B and Item 11 and the Peatix substage of Item 19. Item 12 and later active gates remain open; the production schedule remains unloaded.
