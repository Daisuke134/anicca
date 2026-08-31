# Peatix known submit control plan

## Goal

Allow the bounded parent to click Peatix's measured registration submit control after all required answers are complete, while continuing to reject cookie, filter, navigation, generic, duplicate, and early-submit controls.

## Measured evidence

- Official wake `wake-07aceaf5f2c3aeb0f14f1fbf` on pushed commit `106d350b7` completed Calendar, Luma, Connpass, and Peatix discovery, then ended `circuit_open / peatix_unknown_required_field / 3`; Telegram provider ID `10850`.
- Peatix aggregate was `100 observed / 100 normalized / 87 in-window / 57 free-open / 19 Calendar-free`.
- Candidate 1 completed `氏名` and organizer privacy. Candidate 3 completed `お名前（漢字）`, `お名前（ひらがな）`, and `電話番号`. Neither produced a submit proposal after required answers were complete.
- A value-free no-submit diagnostic used the same actual Calendar inventory and Peatix discovery. The first three candidates all had exactly one required-answer form. Their real submit element was exactly one `input#form-submit-button[type=button]`, `disabled=false`, with no HTML form association. Therefore the generic HTML submit/form-association gate correctly rejected it but cannot complete the measured Peatix JavaScript form.
- Cookie and filter controls had different IDs and were not form-associated. Candidate 2's subjective required answers remain unresolved and must still fail closed.

## Source grounding

- MDN, `<input type="button">`: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/button — `value` is the button label and the button has no default behavior; JavaScript supplies its action.
- MDN, `form` attribute: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/form — the attribute associates a form-associated element with a form. The measured Peatix control intentionally lacks that association.
- Playwright locators: https://playwright.dev/docs/locators — locators re-resolve current DOM state at action time; exact public contracts should be preferred. Peatix's existing direct provider already uses the exact `#form-submit-button` contract.

## Ponytail full gate

- Reuse the existing `inspectPageControls`, `submittable`, parent `performAction`, same-page duplicate signature, and Peatix provider selector.
- Add no new abstraction, model call, retry, state, cache, browser target, or provider service.
- Do not infer submit identity from visible words such as Apply, Accept, Save, or Submit.
- Do not expose answer values. Permit `input[type=button]` value as a public label only for the exact measured Peatix submit ID.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-production-browser-harness.test.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.js`

Soft target: 2 files; production +8–18 LOC; tests +25–45 LOC.

### RED

1. Model exactly one required-answer form plus exactly one `input#form-submit-button[type=button]` outside a form and unrelated cookie/filter buttons.
2. Prove required incomplete answers still suppress the Peatix submit.
3. Prove required-complete state exposes only the exact Peatix submit with its public `value` label.
4. Prove zero or duplicate `#form-submit-button`, a different ID, disabled control, or competing answer forms remain non-submittable.
5. Prove parent rejects injected non-submittable controls and the same-page duplicate-effect guard still blocks a second submit.

### GREEN

- In the in-page inspector, recognize a `knownPeatixSubmit` only when tag is `input`, type is `button`, ID is exactly `form-submit-button`, it is enabled, exactly one required-answer form exists, and exactly one such ID exists in the bounded observation.
- Map that element to sanitized `kind=button`, allow its `value` only as its public label, and mark it `submittable=true` without requiring HTML form association.
- Preserve the generic form-associated submit/image rule unchanged for all other controls.
- Preserve required-answer priority, parent enforcement, and same-page `submit:form-submit` dedupe unchanged.

## Verify

- Focused Harness tests and the adjacent minimal runner/factory/Luna judgment/Peatix/native entrypoint suites.
- `node --check` for both changed files and `git diff --check`.
- Fresh Sol correctness review.
- SSOT update, commit, push, then one official schedule-unloaded foreground wake. Acceptance is parent `registered`/`pending` readback plus `applied_bundle`, or an exact next safe boundary with no duplicate external effect.

## Fresh-review amendments

The first GREEN passed focused 31/31, Luna adjacent 82/82, and Sol expanded 103/103, but fresh Sol review found two Important fail-open paths. They are part of this same slice and must receive explicit RED/GREEN regressions before acceptance:

1. Bind the known Peatix exception to both `provider === "peatix"` and the strict canonical Peatix form page `https://peatix.com/sales/event/<id>/form`. The shared inspector must not mark the same DOM ID submittable for Luma, Connpass, another host, another Peatix path, or a stale registry observation. Pass provider into observation and bind cached observations to the same provider.
2. If any enabled, non-hidden required answer control cannot be represented as a sanitized labeled control, mark every submit non-submittable. The parent/proposer must never infer completeness from a filtered subset of required controls.

Add regressions that reproduce both findings: the same exact ID under `provider=luma`, wrong host/path, cross-provider registry reuse, and one unlabeled required input alongside an otherwise valid Peatix submit. Preserve the measured Peatix happy path and all original fail-closed variants.

## Result

- Initial RED/GREEN: focused 30/31 then 31/31. Initial Luna adjacent 82/82 and Sol expanded 103/103 passed.
- Fresh review returned `fix-first` with two Important findings: the exception was not provider/domain-bound, and an unlabeled required answer disappeared from the sanitized observation.
- Amendment RED reproduced three failures in 31/34: wrong provider/host/path, cross-provider registry reuse, and unlabeled required answer.
- Final GREEN: focused 34/34, Luna adjacent 85/85, Sol expanded 106/106, both JavaScript syntax checks, and `git diff --check` all passed.
- The inspector now receives provider and exact page URL context. The known exception is limited to `provider=peatix` and `https://peatix.com/sales/event/<id>/form`; the registry is provider-bound; any unrepresentable enabled/non-hidden required answer makes all submits non-submittable.
- Final fresh re-review returned `ship` with no Critical or Important findings.
- Final code delta: production +31/-18 and tests +75/-1 across the two owned files only. No browser, provider, Calendar, evidence, Telegram, state/profile, schedule, or launchd action occurred during implementation and tests.
