# Connector cached-action self-heal Item 16 plan

## Goal

Prove the existing production cache/router/runner path repairs one stale selector on the same owned page, promotes it only after parent registration readback, and completes the next wake with zero agent calls.

## Ponytail full gate

- Reuse `createConnectorActionCache`, `createProductionProviderRouter`, `createBrowserHarnessAdapter`, and `runMinimalConnectorWake` directly.
- Add no production code, provider skill, selector registry, self-heal service, agent daemon, repository editor, merge/deploy path, state schema, or retry.
- Use one cached submit action so the single replacement is exactly the broken action; do not pretend that a multi-action merge contract exists.
- Test-only target: one existing file, +70–110 LOC. No browser/provider/Calendar/Telegram/live state/launchd/schedule effect.

## TDD slice

Luna owns only `apps/mr-bot/lib/connector-minimal-production.test.js`.

### RED

Add one composed test that initially asserts the complete Item 16 behavior before adding any test composition helper necessary to make it pass:

1. A private mode-0600 action cache contains one stale submit selector for exact provider/workflow/page-state/effect.
2. First wake uses one owned page. Cached replay attempts the stale selector and fails; direct script also fails; the real bounded Harness adapter proposes and executes one replacement selector on that exact page.
3. Parent workflow readback returns `registered`; only then does the real cache replace the exact entry. Cache contains one replacement action and no stale action.
4. Reset only the synthetic page state, not the cache. Second wake replays the replacement, parent readback verifies `registered`, and direct plus Harness/proposer calls are zero.
5. Each wake completes its synthetic evidence/report dependencies and closes its owned page. No repo edit/merge/deploy or external effect is invoked.

Because the production capability is expected to exist, RED may be an initial missing composed acceptance test rather than a production failure. If the composed test fails against production, Luna stops and reports the exact missing boundary before changing production ownership.

## Verify

- New composed test, full minimal production/runner/action-cache/Harness adapter groups, native entrypoint, syntax, `git diff --check`.
- Fresh Sol review checks same-page identity, fallback boundedness, parent readback before save, exact one-action replacement, cache mode/privacy, second-wake agent zero, and absence of repo-wide mutation.
- Update SSOT, commit, push, mark Item 16 complete only after review. Keep schedules unloaded until the Item 17 cutover.

## Result

- Luna added one composed test in the planned existing production test file; no production file changed. Initial RED iterations exposed two fixture-only expectation mismatches and no production API blocker.
- The final test directly composes the real action cache, production provider router, bounded Harness adapter, and minimal runner. First wake executes stale cache failure, direct failure, exactly one replacement action, Harness readback, parent `registered` readback, and real cache save in order. The exact cache entry then contains the replacement only, no stale selector, and remains mode 0600.
- After resetting only synthetic page state, the second wake replays the replacement through the cache and parent readback. Direct, fallback, proposer, and Harness action counts do not increase; cache bytes are unchanged. Both wakes complete synthetic evidence/report and owned-page cleanup on the same page.
- Luna composed production was 11/11 and full minimal production/runner/action-cache/Harness/evidence/operations was 90/90. Sol independently ran 90/90. Syntax and diff checks passed. Native entrypoint retained only the two known cursor baseline failures. Diff is one test file, +98 LOC; external and repository-wide edit/merge/deploy effects are zero.
- Sol review returned `ship`, Critical 0 / Important 0, with independent focused/adjacent 55/55. Item 16 is complete and the production schedule may now proceed to the separate Item 17 cutover gate.
