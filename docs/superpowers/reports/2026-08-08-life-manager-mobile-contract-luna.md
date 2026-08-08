# Life Manager mobile contract — Gate 2 SDD report

## Scope

This worktree freezes the smallest English-only `/api/mobile/v1` decoder contract needed by the
native simulator demo: session restoration/exchange shapes, connected bootstrap, profile name and
home, direct next-event analysis, structured route projection, semantic English chat/cursor, and
manual refresh/idempotency rules.

The active private demo assumes a pre-connected Calendar session. The contract records the real
demo boundary as event-derived `Shipathon Roppongi` origin → `Tokyo Tower` destination, with no
coordinates or Core Location. A missing origin is represented by `needs_information`. The contract
records the backend-owned exactly-once travel-block requirement without fabricating a write receipt.

Excluded by instruction: Japanese, soft paywall, APNs, phone/calls, late notice, account deletion,
TestFlight/App Store, production router/store/migration, scheduler, and cost-guard route/cache work.

## Worktree and baseline

- Worktree: `/Users/anicca/anicca-project/.worktrees/lm-mobile-contract-luna`
- Branch: `feat/lm-mobile-contract-luna`
- Base: `canonical/main` at `cdd1ad950`
- Root checkout: left untouched (it had pre-existing unrelated dirty files)
- Baseline command: `cd apps/life-manager && npm test`
- Baseline observation: 41 tests passed, then the installed baseline stopped at missing dependency
  `viem` in `lib/taskmarket-award-handoff.test.js`; no mobile files were involved.

## TDD evidence

### RED

Before fixtures existed:

```text
node --test test/mobile-calendar-session-contract.test.js \
  test/mobile-profile-contract.test.js test/mobile-analysis-terminal-state.test.js \
  test/mobile-route-projection.test.js test/mobile-chat-cursor.test.js \
  test/mobile-v1-surface-contract.test.js
```

Observed `12` failing tests (`ENOENT` for the not-yet-created contract fixtures), `0` passing.

### GREEN

After the minimum fixtures, manifest, semantic outbox row, and contract assertions:

```text
cd apps/life-manager
node --test test/mobile-*.test.js
```

Observed `15` passing, `0` failing. The focused run covers session, profile/bootstrap, all five
terminal analysis states, route honesty/nullable provider facts, semantic outbox, cursor stability,
English script checks, structured errors, and the approved/excluded surface list.

Additional check:

```text
git diff --check
```

Result: pass.

## Changed files

Contract fixtures and README:

- `apps/life-manager/contracts/mobile-v1/contract.json`
- `apps/life-manager/contracts/mobile-v1/session-start.json`
- `apps/life-manager/contracts/mobile-v1/session.json`
- `apps/life-manager/contracts/mobile-v1/bootstrap.json`
- `apps/life-manager/contracts/mobile-v1/profile-patch.json`
- `apps/life-manager/contracts/mobile-v1/analysis-route_ready.json`
- `apps/life-manager/contracts/mobile-v1/analysis-needs_information.json`
- `apps/life-manager/contracts/mobile-v1/analysis-no_upcoming_event.json`
- `apps/life-manager/contracts/mobile-v1/analysis-route_unavailable.json`
- `apps/life-manager/contracts/mobile-v1/analysis-failed.json`
- `apps/life-manager/contracts/mobile-v1/route.json`
- `apps/life-manager/contracts/mobile-v1/chat-page.json`
- `apps/life-manager/contracts/mobile-v1/semantic-outbox.json`
- `apps/life-manager/contracts/mobile-v1/error.json`
- `apps/life-manager/contracts/mobile-v1/README.md`

Contract tests:

- `apps/life-manager/test/mobile-contract-support.js`
- `apps/life-manager/test/mobile-calendar-session-contract.test.js`
- `apps/life-manager/test/mobile-profile-contract.test.js`
- `apps/life-manager/test/mobile-analysis-terminal-state.test.js`
- `apps/life-manager/test/mobile-route-projection.test.js`
- `apps/life-manager/test/mobile-chat-cursor.test.js`
- `apps/life-manager/test/mobile-semantic-outbox-contract.test.js`
- `apps/life-manager/test/mobile-error-contract.test.js`
- `apps/life-manager/test/mobile-v1-surface-contract.test.js`

## Claim boundary

GREEN proves the shared contract fixtures and invariants only. It does not claim a live API route,
Supabase schema, Calendar mutation, provider route response, simulator build, or TestFlight receipt.
Gate 3 must implement the server adapter and prove the real pre-connected Calendar journey against
staging before the iOS demo can be called complete.
