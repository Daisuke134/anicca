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

1. `apps/life-manager/lib/connector-production-browser-harness.test.js`
2. `apps/life-manager/lib/connector-production-browser-harness.js`

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

