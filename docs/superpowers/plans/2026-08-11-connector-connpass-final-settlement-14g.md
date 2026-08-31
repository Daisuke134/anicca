# Connector Connpass final-effect settlement Item 14G plan

## Goal

Keep the one Connpass final click on its owned page until the parent observes real `registered|pending`, or stop the wake as `effect_unknown`; never continue to another provider while the registration effect is still settling.

## Measured root cause

- After the 14F readback repair, official wake `wake-f56a23d2571628dbcb718a70` correctly refused the old false pending. It clicked the native final form once, completed the aggregate Harness action in 808ms, then continued to Peatix because the immediate Connpass readback was not yet terminal.
- At wake completion the bundle/Connpass evidence delta was zero. A subsequent read-only canonical check returned exact `registered`, proving the one click succeeded asynchronously after the Harness had already left its provider stage.
- The current Harness already has a 30-second, per-read deadline-bounded, never-resolving-safe final-effect poll for the Peatix final click. The missing behavior is Connpass binding to that same mechanism.

## Ponytail full gate

- Reuse the existing final-effect poll, deadline race, one-click timing, provider readback, and `effect_unknown` result. Generalize names only where needed; add no second poller, timer system, action, page, state field, cache, or module.
- Change only the existing Harness production/test files.
- Connpass settlement applies only when all are true: provider `connpass`; control is the unique submittable button with exact label `申し込みを確定する`; current URL is exact case-sensitive root/one-subdomain `/event/<positive-id>/join/`; candidate is exact `connpass-event://event/<same-id>`; parent Connpass reader exists.
- Begin the poll before the click and release it exactly when the click begins, as for Peatix. A real `registered|pending` returns the verified provider state to the adapter. Timeout, rejected readback, never-resolving readback, wrong identity, or unavailable reader fails closed; an ambiguous post-click timeout is `effect_unknown` so the minimal runner stops before later candidates/providers.
- Preserve Peatix final settlement byte-for-byte in behavior and preserve the Connpass one-submit latch.

## Luna implementation slice

Ownership:

1. `apps/mr-bot/lib/connector-production-browser-harness.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.test.js`

Soft target: 2 files; production net `+8–30 LOC`; tests `+35–70 LOC`.

### RED

1. Exact Connpass join + same candidate: final click returns immediately, parent becomes registered after 10ms; result must be completed with one click, exact provider state, and no second observation/submit.
2. Same exact final click with a never-resolving parent readback must finish at the existing 30-second fake-timer boundary as failed `effect_unknown`, click exactly once, and perform no later action.
3. Wrong join URL, wrong event identity, wrong label, non-submittable/duplicate control, and missing reader must not arm settlement or claim a verified effect.
4. Existing Peatix delayed and never-resolving tests remain unchanged and green.

### GREEN and verification

- Generalize the existing Peatix final-effect helper to accept a strictly bound Connpass final control and choose the matching workflow reader in `performAction`.
- Run Harness plus adapter/runner/minimal production/Connpass provider/workflow/RSVP/evidence and Peatix regressions, syntax, diff check.
- Fresh Sol review checks delayed-effect correctness, same-event URL binding, one click, bounded never-promise behavior, no later provider action after unknown effect, and Peatix non-regression.
- Commit/push before the next official wake. Because the real Connpass registration now exists, the wake must pre-readback it with Submit 0 and create the missing Connpass evidence/Calendar/Telegram/applied bundle. Item 14 closes only on that durable bundle and cleanup.

## Result

- RED: the three Connpass final cases failed on delayed settlement, wrong-URL click admission, and never-resolving bounded completion (51/54).
- GREEN generalized the existing final-effect helper only. Exact Connpass URL/event/unique-final/reader gates precede the one click; delayed provider state is returned, and never-resolving readback returns `effect_unknown` at the existing 30-second boundary.
- Diff after Ponytail trim: production 28/14, tests 69/2. Luna and Sol independently passed the relevant 94/94, Harness 54/54, syntax, and diff check.
- Pushed commit `f5e761557`. Fresh Sol review: `ship`, Critical 0, Important 0; Peatix semantics and Connpass one-submit latch are preserved.
- Schedule remains unloaded. The next official wake is the no-resubmit recovery and durable bundle gate for Item 14.
