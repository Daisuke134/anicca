# Browser Harness form-submit control plan

## Goal

After all parent-resolvable required fields are complete, expose only the actual form-associated submit control to the bounded agent. Never let cookie, preference, back, filter, cancel, arbitrary button, or link controls compete with registration submit.

## Measured evidence

- Official wake `wake-d3924a29861bd5e0e973d9e3` on pushed commit `70fd3acf1` crossed the repaired tickets-to-form boundary.
- Candidate 3 selected four controls in order: `control_4`, `control_5`, `control_8`, `control_11`. The first three were the exact Kanji name, Hiragana name, and phone fields and were parent-resolvable.
- A no-submit, value-free diagnostic filled those three fields with parent-owned values and then observed zero incomplete required answer controls.
- The remaining bounded enum contained eight public buttons: `Close`, `Accept all cookies`, `Back`, `Filter`, `Clear`, `Apply`, `Cancel`, and `Save preferences`. `control_11` was `Accept all cookies`.
- The actual Peatix form submit is an input submit control whose visible text is carried by its value. `inspectPageControls` does not use a button input's value as its public label, so the submit control is absent while arbitrary buttons and links are admitted.

## Ponytail full gate

- Do not add provider-specific selectors, another model call, a cache, state, retry, browser rail, or navigation abstraction.
- Reuse the current sanitized control contract and parent-derived action method.
- Add only a boolean form-submission property derived from the live DOM; never expose an input value except the public label of a submit-type button.
- Keep all private values parent-owned and keep final provider readback/evidence gates unchanged.

## Implementation slice

Files owned by Luna:

1. `apps/mr-bot/lib/connector-production-browser-harness.test.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.js`

Soft target: 2 files; production +20–35 LOC; tests +35–55 LOC.

### RED

1. Model a form containing three required fields, a form-associated input/button submit, and unrelated cookie/preferences/back/link controls.
2. Prove the current inspector omits the input submit label and marks no form-submission identity.
3. Prove the current proposer enum includes arbitrary buttons while required fields remain and after they complete.
4. Prove direct `performAction` can currently operate an arbitrary observed button.

### GREEN

- Extend the sanitized control shape with `submittable: boolean` (default false for compatible fixtures). It may be true only for a `button` kind derived from a form-associated DOM submit control.
- For an `input` whose type maps to button, use its `value` as a label source only when needed; do not use answer-input values.
- Derive `submittable` from DOM form association and submit type. Do not infer it from marketing text such as `Apply`, `Accept`, or `Submit` alone.
- In the proposer, if incomplete required answer controls exist, expose only those. Otherwise expose only `submittable` buttons. Arbitrary buttons and all links stay outside the enum.
- In parent `performAction`, independently reject non-submittable buttons and links even if an injected proposer returns them.
- The parent still derives `purpose=submit`, `method=ax_click`; the model returns only the control token.

### Verify

- Focused Harness tests including inspector, proposer, parent operation, repeated-action guard, and Peatix resolver cases.
- Adjacent minimal runner, production factory, Luna judgment, Peatix workflow/provider, and native entrypoint tests.
- `node --check` for both modified JavaScript files and `git diff --check`.
- Fresh Sol correctness review, SSOT update, commit, push, then one schedule-unloaded official foreground wake.

## Fresh-review amendments

The first GREEN passed its focused tests but fresh Sol review found three Important gaps. They are part of this slice and must be RED/GREEN before acceptance:

1. A submit-type control is `submittable` only when its form is the same form that contains the observed required answer controls. A cookie/preferences form submit must remain false even though it is form-associated and type submit. If the registration form has multiple submit controls, fail closed rather than expose multiple final effects.
2. Read `element.value` as a public label only for an `input` whose type is `submit` or `image`; never for a generic button or answer input.
3. Parent `performAction` must inspect the whole registered observation and reject a submit while any required answer control is incomplete, independent of the proposer.
4. Repeated submit prevention must use the same-page form-submit effect rather than a control token, so a second submit token or DOM reindex cannot trigger a duplicate action before the page path/readback state changes.
5. Exactly one required-answer form must exist in the bounded observation before any submit can be marked submittable. If a registration form and a cookie/preferences form both contain required answer controls, all submit controls fail closed. Add a regression with a required cookie checkbox and its own submit alongside the registration form.

Add regressions for a cookie form with its own submit, a generic button with a private-looking value, injected early submit with a pending required field, two submit tokens on one form, and a reindexed submit token on the same page. Preserve the existing ability to submit once after required completion and again only after an exact page-path transition.

## Result

- Initial RED: focused 21/24, reproducing input-submit label omission, arbitrary cookie-button proposal, and parent acceptance of arbitrary button/link actions.
- First GREEN passed 24/24, but fresh Sol review found three Important gaps: cookie-form submit scope/value privacy, parent early-submit refusal, and same-page alternate-token duplicate submit.
- Amendment RED/GREEN: 24/27 then 27/27. A second review found one remaining required-cookie-form ambiguity.
- Final RED/GREEN: 28/29 then 29/29. Exactly one required-answer form and one submit are now required; multiple answer forms or duplicate submits fail closed.
- Luna adjacent suite: 80/80 PASS. Sol expanded suite: 93/93 PASS. Both JavaScript syntax checks and `git diff --check` PASS. Final fresh re-review: `ship` (Critical 0, Important 0).
- No browser, model, provider submit, Calendar, evidence, Telegram, state/profile, schedule, or launchd action occurred during implementation and test.
