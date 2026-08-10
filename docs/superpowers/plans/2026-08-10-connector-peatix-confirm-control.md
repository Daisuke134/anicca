# Peatix exact confirm control plan

## Goal

After the bounded parent completes the Peatix organizer form, wait for the exact same-event confirm page and expose only the measured final `a#confirm-button` registration effect. Parent readback and the existing applied-bundle chain remain the only success authority.

## Measured evidence

- Official wake `wake-a85aefe7a153ce0513e7d7df` on pushed commit `f8c257bd2` completed all provider discovery. Peatix was `100/100/87/56/19`.
- Candidate 3 selected `control_4 → control_5 → control_8 → control_9`; step 4 was the newly recognized exact form submit. The Harness action then threw during the immediate transition/readback cycle, so the wake ended `circuit_open / peatix_unknown_required_field / 3`; Telegram provider ID `10868`; provider/Calendar/PNG/bundle increments remained zero.
- A private-value-safe no-final-submit diagnostic reproduced the same candidate. The exact form submit returned `status=success` and navigated to `/sales/event/5104728/confirm`.
- On the confirm page, the required Kana family/given and public display-name controls were already completed. No control was submittable.
- The measured final registration control was exactly one enabled `a#confirm-button`, public label `チケットを申し込む`, no HTML form association. It was omitted because the bounded selector admits only `a[role=button]`, and every ordinary link is intentionally rejected.

## Ponytail full gate

- Reuse the existing strict provider/page binding, representable-required gate, sanitized `submittable`, parent enforcement, same-page duplicate-effect signature, Peatix direct-provider ID/text contract, and Playwright `waitForURL` pattern.
- Add no new provider abstraction, model call, retry loop, state, cache, browser target, or evidence path.
- Do not admit arbitrary anchors or infer final action from marketing words. The exception must require provider `peatix`, strict same-event confirm URL, tag `a`, exact ID `confirm-button`, exact public label `チケットを申し込む`, enabled, and unique bounded ID.
- Do not perform a final registration click in diagnostics or tests. The first final external effect after implementation is the official schedule-unloaded foreground wake.

## Implementation slice

Luna owns only:

1. `apps/life-manager/lib/connector-production-browser-harness.test.js`
2. `apps/life-manager/lib/connector-production-browser-harness.js`
3. `apps/life-manager/lib/connector-minimal-production.test.js` — update the one default-inspector selector fixture from the old selector to the new selector; no behavior change.

Soft target: 3 files; production +15–30 LOC; Harness tests +35–60 LOC; adjacent fixture +1/-1 line.

### RED

1. Model the strict Peatix confirm page with completed required answers, one exact `a#confirm-button`, and unrelated anchors/cookie/filter controls. Prove current observation exposes no submit.
2. Prove pending, unlabeled, or competing-form required answers keep the final control non-submittable.
3. Prove wrong provider, host, path, event identity, tag, ID, label, disabled state, or duplicate ID remains non-submittable.
4. Prove generic anchors and injected links remain parent-rejected.
5. Reproduce that form submit can advance the adapter before exact confirm navigation settles; require a bounded same-event form→confirm wait before subsequent readback/observation.

### GREEN

- Extend the bounded DOM selector only with `a#confirm-button`.
- Derive `knownPeatixConfirm` only from the complete strict contract above and map only that exact anchor to sanitized `kind=button`, `submittable=true`.
- Preserve every ordinary anchor as `kind=link`, non-submittable, and parent-rejected.
- For the exact Peatix form submit, start a `page.waitForURL` for the same event's strict `/confirm` path before click and require it to settle before returning action success. A mismatch or timeout returns failed and never exposes/clicks the final control.
- Keep the final click bounded to one same-page submit effect; the adapter then invokes existing Peatix parent readback. Only `registered`/`pending` may continue to evidence.

### Primary audit amendment

The first GREEN used the final label on the form-transition test, but live DOM proved the form submit label is `確認画面へ進む` and the final anchor label is `チケットを申し込む`. Keep separate exact constants and privileges: only the first can start form→confirm navigation wait; only the second can become the final submittable anchor. A final-label control on the form must remain without transition privilege. The final anchor also requires exactly one non-null required-answer form; zero form association fails closed. Do not add a production legacy-selector fallback. Update the single adjacent default-inspector fixture to the new bounded selector instead.

## Verify

- Focused Harness tests and adjacent minimal runner/factory/Luna judgment/Peatix provider-workflow/evidence/native suites.
- Both JavaScript syntax checks and `git diff --check`.
- Fresh Sol correctness review focused on accidental final external effects and cross-event identity.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded foreground wake. Acceptance is new parent `registered`/`pending` plus a durable `applied_bundle`, or an exact next safe boundary with zero duplicate final effects.
