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

1. `apps/mr-bot/lib/connector-production-browser-harness.test.js`
2. `apps/mr-bot/lib/connector-production-browser-harness.js`
3. `apps/mr-bot/lib/connector-minimal-production.test.js` — update the one default-inspector selector fixture from the old selector to the new selector; no behavior change.
4. `apps/mr-bot/lib/connector-minimal-runner.test.js` — one regression proving ambiguous final effect stops before the next candidate.
5. `apps/mr-bot/lib/connector-minimal-runner.js` — recognize only the exact bounded fallback `effect_unknown` result and immediately finish the wake `circuit_open / effect_unknown`.

Soft target: 5 files; no new module/service/state; Harness production/tests contain the strict DOM and settlement contract; runner production is one exact early-stop branch with one regression; adjacent fixture remains +1/-1 line.

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

### Fresh review fix-first amendment

Fresh review reproduced two Important failures in the first final-control GREEN, so it is not shippable:

1. The exact final click returned success before Peatix navigation/readback settled. Immediate parent readback observed `absent`, the fallback returned `agent_action_failed`, and the same fixture became registered 10 ms later. Because the outer runner performs post-submit readback only after a completed fallback, this can advance to another candidate after a real registration and create duplicate external effects.
2. A CSS-hidden exact `a#confirm-button` was still mapped to `kind=button`, `submittable=true`.

Required fix: start a bounded final-effect wait before the exact final click and do not return action success until either same-event registered/pending readback can be observed or an exact safe terminal boundary proves no effect. Timeout/ambiguous state must stop the candidate sequence and must never authorize the next candidate as though no effect occurred. Add RED coverage proving a delayed registration yields one click, one final outcome, and no next-candidate action. Require the exact final anchor to be browser-visible in addition to the existing provider/host/path/event/tag/ID/label/enabled/unique/no-form-association/required-answer gates; CSS-hidden, hidden-attribute, zero-size, detached, or otherwise non-visible variants remain non-submittable.

The three-file Harness slice can preserve a bounded timeout/click exception as `failed / effect_unknown`, but the existing minimal runner treats every non-completed fallback alike and advances to the next candidate. Expand ownership only to `connector-minimal-runner.js` and its test. After the fallback returns the exact safe reason `effect_unknown`, increment the failure count once, report `circuit_open / effect_unknown`, and return before any next-candidate navigation, direct action, Harness action, or registration effect. Do not change handling for any other fallback failure and do not synthesize `pending`, `registered`, or success.

### Fresh re-review bounded-readback amendment

The first settlement GREEN checked the 30-second deadline only between polling iterations. A single unresolved `readProviderState()` promise could therefore block forever and violate the bounded wake contract. Race every parent readback attempt against the remaining overall settlement budget; clear the losing timer when readback settles; and return `failed / effect_unknown` when the remaining budget expires even if the provider promise never resolves. Add a deterministic RED with a never-resolving readback and controlled time proving one click, bounded completion, exact `effect_unknown`, and runner no-next-candidate behavior. Do not add an unbounded retry, production-configurable weaker timeout, fake success, or a second final click.

## Verify

- Focused Harness tests and adjacent minimal runner/factory/Luna judgment/Peatix provider-workflow/evidence/native suites.
- Both JavaScript syntax checks and `git diff --check`.
- Fresh Sol correctness review focused on accidental final external effects and cross-event identity.
- Fresh-review regressions for delayed final readback/no-next-candidate and hidden final anchors.
- SSOT update, commit, push, clean preflight, then one official schedule-unloaded foreground wake. Acceptance is new parent `registered`/`pending` plus a durable `applied_bundle`, or an exact next safe boundary with zero duplicate final effects.

## Result

- Initial confirm-control RED exposed the omitted exact anchor and the form-transition race. The first GREEN reached focused 39/39 and adjacent 90/90.
- Fresh review reproduced two unsafe boundaries: delayed registration could be misclassified as failure and advance to another candidate, and a hidden exact anchor could be admitted. The fix added strict browser visibility, bounded parent settlement, preserved final provider state, and exact `effect_unknown` propagation.
- The three-file Harness boundary could not stop the outer candidate loop, so the plan was explicitly expanded to the existing minimal runner and one runner test. Only exact fallback `effect_unknown` now reports `circuit_open / effect_unknown` after one failure and before another candidate; ordinary failures retain the three-consecutive contract.
- Fresh re-review then found a never-resolving parent readback could bypass the outer deadline. Per-readback remaining-budget racing and deterministic fake-time coverage closed it without weakening the fixed production 30-second budget.
- Final evidence: Harness 42/42, runner 15/15, planned expanded adjacent 108/108, changed-file syntax and `git diff --check` PASS. Full Connector regression was 304/307; all three failures reproduce on clean HEAD (two stale provider-cursor expectations and one required-email fixture), so new failures are zero. Final fresh Sol review: Critical 0, Important 0, `ship`.
