# Connector Harness Required-control Parent Method Plan

**Status:** GREEN、fresh review `ship`。live acceptanceはSSOT進捗266以降で継続する。

> **For Luna:** Use Superpowers test-driven-development. Own only the two Harness files below. Do not edit docs/spec, commit/push, browser/state/private profile, or external systems.

**Goal:** Prevent the model from selecting optional form answers or inventing a method incompatible with the chosen control, while preserving bounded same-page progress.

**Measured live failure:** In official wake `wake-c937e27dea6b55e51327e83e`, completed observation advanced candidate 2 from `control_4` to `control_6`, but `control_6` was a required-false text input and the model returned `ax_check`. The DOM action failed safely; registration remained 0.

**Architecture:** The model chooses only one sanitized actionable control token. The parent determines purpose/method from the observed control kind. Only incomplete required answer controls plus buttons/links are actionable. Required group semantics come from the element or its nearest existing form group. Reuse every current value resolver, completion boolean, duplicate-effect guard, fallback sequence, adapter, and parent readback.

**Ponytail scope:** Two files; production <= 30 changed LOC, tests <= 50. No new module/schema/store/profile field/provider/retry/session/target/page/model or external action.

**Files:**

- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## Contracts

1. RED first: a required-false text input currently remains in the proposer control enum and an agent-supplied `ax_check` reaches the Harness.
2. Default observation marks a control required when the element has `required`, `aria-required=true`, or its nearest existing `fieldset, dl.field, [role=group], .field` has class `required` or `aria-required=true`. It exposes only the boolean.
3. Actionable controls are:
   - incomplete `input`, `textarea`, `select`, `checkbox`, or `radio` with `required=true`;
   - `button` or `link` regardless of required;
   - never a completed or optional answer control.
4. The local agent JSON schema requires only one `control` from the actionable enum. It receives sanitized controls/required/completed/question but no value, URL, candidate identity, dynamic state, profile, or method authority.
5. Parent derives the exact action:
   - input/textarea: `{purpose:"fill", method:"ax_fill"}`;
   - select: `{purpose:"fill", method:"ax_select"}`;
   - checkbox/radio: `{purpose:"fill", method:"ax_check"}`;
   - button/link: `{purpose:"submit", method:"ax_click"}`.
6. Ignore/reject any extra agent purpose/method; only a validated returned control token affects the parent action. Unknown/missing token fails closed.
7. Preserve completed-control DOM rejection, exact question+option parent approval, same-page normalized-effect dedupe, path-transition allowance, fallback evidence sequence, max 10, and parent `registered|pending` readback.

## TDD and verification

1. Add focused RED for group-required observation, optional answer exclusion, control-only schema, wrong agent method non-authority, and each kind→parent action mapping.
2. Record RED before production edits; implement the smallest GREEN.
3. Run focused Harness+factory, runner adjacent, native contracts, syntax, and diff checks.
4. Return RED/GREEN evidence, LOC, and live limitation. Sol owns fresh review, SSOT, commit/push, and exactly one official live wake.
