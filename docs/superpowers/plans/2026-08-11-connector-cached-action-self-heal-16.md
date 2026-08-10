# Connector cached-action self-heal Item 16 plan

## Goal

Prove the existing production cache/router/runner path repairs one stale selector on the same owned page, promotes it only after parent registration readback, and completes the next wake with zero agent calls.

## Ponytail full gate

- Reuse `createConnectorActionCache`, `createProductionProviderRouter`, `createBrowserHarnessAdapter`, and `runMinimalConnectorWake` directly.
- Add no production code, provider skill, selector registry, self-heal service, agent daemon, repository editor, merge/deploy path, state schema, or retry.
- Use one cached submit action so the single replacement is exactly the broken action; do not pretend that a multi-action merge contract exists.
- Test-only target: one existing file, +70–110 LOC. No browser/provider/Calendar/Telegram/live state/launchd/schedule effect.

## TDD slice

Luna owns only `apps/life-manager/lib/connector-minimal-production.test.js`.

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

Pending Luna composed TDD verification.
