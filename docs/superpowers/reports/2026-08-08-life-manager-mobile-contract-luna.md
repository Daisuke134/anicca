# Life Manager mobile backend — Gate 3 SDD brief

## Scope

This worktree implements the authenticated `/api/mobile/v1` Gate 3 contract: session/auth,
bootstrap/profile, direct analysis, structured anchored route providers, semantic localized chat and
cursor, resumable question replies, confirmed/rate-limited calls, APNs device ownership, and
resumable account deletion.

The active private demo assumes a pre-connected Calendar session. The contract records the real
demo boundary as event-derived `Shipathon Roppongi` origin → `Tokyo Tower` destination, with no
coordinates or Core Location. A missing origin is represented by `needs_information`. The contract
records the backend-owned exactly-once travel-block requirement without fabricating a write receipt.

Excluded by instruction: late notice, scheduler, cost-guard state, iOS source, TestFlight/App Store,
and live production/staging migration, provider, or deployment execution.

## Worktree and baseline

- Worktree: `/Users/anicca/anicca-project/.worktrees/lm-mobile-backend-luna`
- Branch: `feat/lm-mobile-backend-luna`
- Base: `ada35f98c94a6dbff583064547c0ffcbbf63a03a` (`canonical/feat/lm-mobile-contract-luna`)
- Root checkout: left untouched (it had pre-existing unrelated dirty files)
- Baseline command: `cd apps/life-manager && npm test`
- Baseline observation: 41 tests passed, then the installed baseline stopped at missing dependency
  `viem` in `lib/taskmarket-award-handoff.test.js`; no mobile files were involved.

## Explicit implementation file list

Required router mounting and migration:

- `apps/life-manager/server.js`
- `apps/life-manager/migrations/2026-08-08-lm-mobile-v1.sql`

Mobile backend libraries:

- `apps/life-manager/lib/mobile-account.js`
- `apps/life-manager/lib/mobile-analysis.js`
- `apps/life-manager/lib/mobile-bootstrap.js`
- `apps/life-manager/lib/mobile-calendar.js`
- `apps/life-manager/lib/mobile-call.js`
- `apps/life-manager/lib/mobile-device.js`
- `apps/life-manager/lib/mobile-idempotency.js`
- `apps/life-manager/lib/mobile-localization.js`
- `apps/life-manager/lib/mobile-outbox.js`
- `apps/life-manager/lib/mobile-profile.js`
- `apps/life-manager/lib/mobile-question.js`
- `apps/life-manager/lib/mobile-route.js`
- `apps/life-manager/lib/mobile-session.js`
- `apps/life-manager/lib/mobile-staging-verification.js`
- `apps/life-manager/lib/mobile-store.js`
- `apps/life-manager/lib/mobile-utils.js`
- `apps/life-manager/lib/mobile-v1-router.js`

Gate 3 fixtures:

- `apps/life-manager/contracts/mobile-v1/account-deletion.json`
- `apps/life-manager/contracts/mobile-v1/apns-device.json`
- `apps/life-manager/contracts/mobile-v1/call.json`
- `apps/life-manager/contracts/mobile-v1/contract.json`
- `apps/life-manager/contracts/mobile-v1/device-deleted.json`
- `apps/life-manager/contracts/mobile-v1/question-reply.json`
- `apps/life-manager/contracts/mobile-v1/README.md`
- `apps/life-manager/contracts/mobile-v1/session-revoked.json`

Mobile tests:

- `apps/life-manager/test/mobile-account-deletion.test.js`
- `apps/life-manager/test/mobile-analysis.test.js`
- `apps/life-manager/test/mobile-bootstrap.test.js`
- `apps/life-manager/test/mobile-calendar.test.js`
- `apps/life-manager/test/mobile-device.test.js`
- `apps/life-manager/test/mobile-idempotency.test.js`
- `apps/life-manager/test/mobile-localization.test.js`
- `apps/life-manager/test/mobile-migration-contract.test.js`
- `apps/life-manager/test/mobile-outbox.test.js`
- `apps/life-manager/test/mobile-profile-contract.test.js`
- `apps/life-manager/test/mobile-profile.test.js`
- `apps/life-manager/test/mobile-question-reply.test.js`
- `apps/life-manager/test/mobile-route.test.js`
- `apps/life-manager/test/mobile-session.test.js`
- `apps/life-manager/test/mobile-staging-verification.test.js`
- `apps/life-manager/test/mobile-store.test.js`
- `apps/life-manager/test/mobile-test-call-contract.test.js`
- `apps/life-manager/test/mobile-v1-router.test.js`
- `apps/life-manager/test/mobile-v1-runtime-contract.test.js`
- `apps/life-manager/test/mobile-v1-surface-contract.test.js`

## TDD and verification evidence

### RED

Before fixtures existed:

```text
node --test test/mobile-calendar-session-contract.test.js \
  test/mobile-profile-contract.test.js test/mobile-analysis-terminal-state.test.js \
  test/mobile-route-projection.test.js test/mobile-chat-cursor.test.js \
  test/mobile-v1-surface-contract.test.js
```

The Gate 2 contract branch observed `12` failing tests (`ENOENT` for the not-yet-created contract
fixtures), `0` passing before its fixture slice.

### GREEN

After the minimum fixtures, manifest, semantic outbox row, and contract assertions:

```text
cd apps/life-manager
node --test test/mobile-*.test.js
```

Current Gate 3 focused run:

```text
cd apps/life-manager && node --test test/mobile-*.test.js
112 passing, 0 failing
```

The focused run covers session, profile/bootstrap, all five terminal analysis states, production-
shaped structured route provider/cache wiring, timezone preservation, semantic localized outbox,
cursor stability, token replay protection, refresh-family replay, question resumption, APNs transfer,
atomic call day guards, account deletion, fixture-validated router output, and the staging evidence
boundary.

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

GREEN proves code-level and injected-adapter contracts only. It does not claim live staging API
responses, a Supabase migration receipt, Calendar mutation, APNs registration, call placement,
provider route response, simulator build, or TestFlight receipt. The committed staging plan remains
`planned_not_executed`; review must complete before any isolated staging evidence is recorded.

## Gate 3 review fix round 2/5 — SDD ledger append

### Finding #1 — persistent route cache and structured provider facts

RED evidence (before the fix):

```text
cd apps/life-manager && node --test test/mobile-route.test.js
9 passing, 2 failing
- reconstructed providers invoked Transit twice instead of reusing the mobile store cache
- accessWalkSecs was absent from the structured route
```

GREEN evidence:

```text
cd apps/life-manager && node --test test/mobile-route.test.js test/mobile-store.test.js
14 passing, 0 failing
```

The mobile store now owns `readRouteCache`/`writeRouteCache` for the Supabase-backed
`lm_route_cache` rows. The request digest is tenant-scoped and covers event anchor, direction,
origin, destination, and IANA timezone; the complete route is retained in `route` while legacy
Gate 1 columns stay populated for pruning/observability. The process-global structured-route
`Map` is no longer the production default. Transit and Google shaping preserves access/egress
walking seconds, fare, leg train type, headsign, platform, provider timestamps, and availability
when returned, while unsupported entrance/car-position facts remain absent. Unknown event
timezones still fail closed.

### Finding #2 — real router contract validation

The tautological fixture-returning handler overrides were removed from
`mobile-v1-runtime-contract.test.js`. The test now drives the real router, authentication,
session, bootstrap, profile, analysis, outbox/chat, question, call, APNs, and deletion handlers
for all 13 approved endpoints. Only Calendar/route/call provider and store seams are deterministic;
the response is deep-compared to the frozen fixture for every case.

RED evidence during replacement included the expected failures for random session state, profile
shape, stable analysis message/cursor, call/device IDs, and deletion clock. GREEN evidence:

```text
cd apps/life-manager && node --test test/mobile-v1-runtime-contract.test.js
4 passing, 0 failing (including all 13 endpoint cases)

cd apps/life-manager && node --test test/mobile-*.test.js
112 passing, 0 failing
```

The route fixture text was corrected from `8:35 AM` to `1:35 AM` because its authoritative
timestamp is `08:35Z` and its preserved IANA timezone is `America/Los_Angeles`; this corrects a
fixture contradiction without dropping fields or weakening assertions. No live migration,
provider, Calendar, APNs, call, account-deletion, staging, or production side effect was run.

Implementation commits for this round: `54eb58d1e` (persistent route cache/facts),
`2dc2c0b42` (real router fixture validation). Finding #9 remains the separate truthful live-staging
verification gate and is intentionally `planned_not_executed`.
