# Model words switch — 2026-11-20

## Design and implementation plan

Reuse `models/manager/product` (ChatLLMGenerator → validated weighted draw → SQLite commit). The authenticated app sends its synthetic user's categorical onboarding snapshot; home shows only the accepted chosen word, not the unselected candidates. A none decision or unavailable engine shows no intervention. Notification sender already uses this engine on current anicca-products main (PR #941); do not fork that sender here.

1. Add failing product tests for home conditioning, notification conditioning, durable ManagerBench rows, replay and unavailable generation.
2. Implement bounded categorical conditioning and a ManagerBench projection in the existing decision transaction, preserving unknown outcomes and actual propensity.
3. Connect Living home through the existing authenticated URLSession. Retain one decision per account/context/day/time band; remove catalog deck expansion and legacy cache reuse. Record generated provenance locally.
4. Run product tests and available E2E patterns; review; commit current branch without push or App Store submission.

No new dependency or paid API. Use the existing OpenRouter credit via configured DeepSeek V4.1 Flash engine. Astra Advisor is unavailable in this harness. Skills read: using-superpowers, brainstorming (questions opted out by explicit assignment), writing-plans, test-driven-development and writing-good-tests, verification-before-completion, repository loop-development. `scripts/verify-source-boundary.sh` fails because its legacy canonical root is absent; explicit assignment overrides this boundary. Current worktree and branch are retained as instructed.

## Primary-source inventory (before)

- Anicca base: `014f16a9c`. `FeedRootView.refreshToday` uses `PersonalizedNudgeSelector` / `QuoteProvider`; `buildDeck` fills up to 12 catalog cards. The daily store can retain an onboarding catalog selection. Home generated fraction: 0/selected cards by construction; prepared fraction 100%. This is a source-path measurement, not production exposure telemetry.
- The separate local anicca-products checkout at `48d95f2d70493f4cbebf1d7a13c70b65a5906dc7` still uses `quoteIdForSlot`; it is stale and is NOT evidence of current deployment.
- GitHub anicca-products PR #941 merged at `2026-11-19T23:45:10Z`, merge SHA `40fdbd5635e2f4cf885874153d1150d105bb2ec5`. Current `apps/api/src/jobs/problemNudgeApnsSenderJob.js`, fetched 2026-11-21, invokes `/manager/push-decisions`, sends `decision.chosen.text`, rejects old catalog rows and suppresses on error. Model-origin fraction among newly accepted send decisions: 100% by source path, prepared 0%. No-send decisions are excluded from the denominator.
- `SyntheticUser.deliveryPayload` already syncs categorical `answerIds` under profile personalization. The sender passes profile metadata but its top-level desired_state is `unknown`. Normalize that existing snapshot inside the engine; never send raw metadata to the LLM.
- Existing SQLite cases contain text, context, generator_model and assignment probability but lack the app's ManagerBench situation/stimulus/response projection.
- Production delivered/prepared/generated counts: **unknown**. No production journal or APNs receipt has been obtained; neither a source path nor a local stub proves real deliveries.


Ruling: the current sender is already merged in its own repository; this branch changes its shared engine rather than copying an obsolete sender. Home uses only the sampled word (one card), because displaying unselected candidates with fabricated uniform propensities would invalidate the intervention record. Other catalog surfaces (saved library/onboarding preview) are outside these two delivery paths.

## Implementation and verification

- Living home now calls the existing authenticated app proxy `/manager/decisions`. GitHub's current `apps/api/src/routes/manager.js` was independently read and confirms that route. It uses verified JWT subjects and forwards to the private product service. A pending notification tap is resolved immediately and takes precedence over an in-flight home request.
- Retries use the same UUID derived from account + local day/time band + timezone + language + categorical answers. The server replays its committed decision without another generation/draw. There is no local catalog/cache fallback. One sampled word is displayed; `none` yields no card. The daily button retries an empty home.
- Existing sender context is normalized from `profile.personalization.answerIds`/`answerVersion`; unrelated raw metadata is excluded from the model prompt. Home sends `SyntheticUser.answerSnapshot` through the same contract. Other local catalog surfaces remain (onboarding preview/saved library); they are not daily-home generation.
- Chosen text, configured model, conditioning snapshot, complete candidate distribution and conditional selection probability remain together in SQLite. `managerbench_case` is created in that same transaction, not as a non-atomic second journal write. `python -m models.manager.product.export_cases /private/cases.db` emits JSONL. No-send is `do_not_send`; outcomes are unknown until measured. Candidate IDs are unique to the decision. Local home cases retain the same text/model/probability fields.
- Probability means the sampling mass conditional on this generated candidate set. It is NOT token likelihood, efficacy or a human-response probability. Unobserved delivery is not a negative outcome. Notification delivery/outcome readback remains a separate provider join; this change does not fabricate it.
- The current [OpenRouter model catalog](https://openrouter.ai/api/v1/models), read 2026-11-21, lists `deepseek/deepseek-v4.1-flash-1017`; that is the default with existing OpenRouter credit. Existing explicit deployment model settings remain respected. OpenRouter keys are not forwarded to custom base URLs. No live key was configured in this VM; no model billing call was made.

### Evidence and limits

- RED: direct existing-store call rejected the new home synthetic context; the JSONL exporter did not exist. Subsequent regression tests caught missing default generator, cross-host key forwarding, and mismatched candidate/message IDs before their fixes. Python product tests also exercise per-person words through a real local chat HTTP stub, invalid conditioning, unavailable engine, replay, no-send and observation-window export. Stub content is explicitly not DeepSeek quality evidence.
- Local source-path ratio after: newly chosen home words prepared 0%, generated 100% (excluding `none`/errors); sender was already prepared 0%, generated 100% on current remote main. Actual production exposure ratios before/after remain **unknown**, not 0. No release or new app distribution occurred.
- Existing HTTP mount E2E ran against a temporary copy of the current Express manager router plus its existing JWT middleware, with Express installed only under `/tmp`: authenticated health 200, no configured generator 503, stopped upstream 503; no fallback. Initial attempt against the other checkout failed to boot because that checkout lacks Express; the isolated replay succeeded.
- Full repository `pytest -q --maxfail=1` stopped during collection at `apps/crowdworks-revenue/tests/test_paid_owner_observation_boundary.py` because the existing CrowdWorks chain needs `bs4`. A broad collection probe also encountered `skills/_shared/__tests__/test_ytdlp_parse.py` calling `sys.exit(0)` during import (4477 tests collected / 66 collection errors before abort). These unrelated suites are not claimed green.
- Swift/Xcode/Maestro are unavailable on this Linux VM. Added `ModelWordsTests.swift` for response validation, identity mismatch and propensity mismatch, but did not execute it. iOS compile, simulator/physical-device home, APNs receipt, live model quality and production journal readback remain unverified.
- Fresh read-only Sol review identified one blocking cross-host credential issue; fixed with a failing-then-passing regression test. Earlier route/cold-start concerns were resolved through primary-source readback and the immediate navigation fix.
- Legacy docs disagree with assignment about repository origin and recommend an OpenAI-key path; the explicit anicca assignment is followed, and this implementation uses existing OpenRouter credit only. No push, PR, merge, deployment, App Store submission or production mutation. Worktree remains for review on the assigned branch.

Final focused verification: `python -m pytest models/manager/product/tests apps/mobile/anicca-ios/scripts/tests -q` → **67 passed, 2 skipped, 10 subtests passed**. One Starlette/httpx deprecation warning in the temporary test environment. `git diff --check` passed. Final delta review: **0 findings / 0 blocking**. The branch-finishing workflow is applied as local commit only, as explicitly requested; no merge/cleanup/push menu or action.
