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
115 passing, 0 failing
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

## Gate 3 review fix round 3/5 — SDD ledger append

### Finding #1 — conflict-compatible persistent route cache writes

RED evidence before the fix:

```text
cd apps/life-manager && node --test test/mobile-store.test.js test/mobile-migration-contract.test.js
3 passing, 2 failing
- migration still declared a partial (uid, cache_key) unique index, which cannot be inferred by ON CONFLICT (uid, cache_key)
- a Supabase 409 was returned as a successful fallback value instead of surfacing route-cache write failure
```

GREEN evidence:

```text
cd apps/life-manager && node --test test/mobile-store.test.js test/mobile-migration-contract.test.js
5 passing, 0 failing
```

The migration now drops/replaces the old partial index with a non-partial unique index on
`(uid, cache_key)`, matching the store's `ON CONFLICT` target. Route writes require a persisted
representation and surface 409 or missing-row responses as retryable `route_cache_write_failed`;
they never claim persistence on a failure. Tests cover insert, same-key update/read, Supabase
failure propagation, and the migration contract. The memory store also uses the authenticated UID
object when deriving its tenant-safe cache key.

### Finding #2 — real route domain and cursor contract

The runtime contract no longer injects a route handler that returns `route.json`, nor a fixture-based
cursor encoder. The analysis case drives the actual `computeMobileRoute` path with deterministic
geocoding and Transit provider payloads, then compares the router's localized projection to the
frozen fixture. Chat rows are real stored rows without prefilled cursors; the actual cursor encoder
and decoder are exercised across two pages.

RED evidence while removing the seams:

```text
cd apps/life-manager && node --test test/mobile-v1-runtime-contract.test.js
4 passing, 1 failing
- the real route path initially failed at the memory route-cache scope boundary

cd apps/life-manager && node --test test/mobile-*.test.js
113 passing, 2 failing
- actual cursor payloads were seven characters and violated the frozen opaque-token minimum
```

GREEN evidence:

```text
cd apps/life-manager && node --test test/mobile-v1-runtime-contract.test.js
10 passing, 0 failing (including all 13 endpoint cases and cursor round-trip)

cd apps/life-manager && node --test test/mobile-*.test.js
115 passing, 0 failing
```

Cursor encoding now uses a versioned `seq:<n>:v1` payload (with backward-compatible decoding),
and the route/chat fixtures record the actual encoded values. The structured route adapter applies
provider buffer seconds and preserves provider leg instructions while retaining nullable facts; no
unsupported precision is fabricated. Syntax checks for all changed mobile JS files and
`git diff --check` both passed. No live migration, provider, Calendar, APNs, call, deletion,
staging, or production side effect was run.

Implementation commits for this round: `341a8bfab` (cache upsert/failure semantics) and
`78bcadf98` (real route/cursor runtime contract). Finding #9 remains the separate truthful
live-staging verification gate and is intentionally `planned_not_executed`.

## Task 10 live staging attempt — blocked by production Supabase identity

### Scope and branch safety

The Task 10 worker ran from `/Users/anicca/anicca-project/.worktrees/lm-mobile-backend-luna`
on `feat/lm-mobile-backend-luna` at reviewed implementation HEAD `7fcbdcc055718c6104132234a5e8718d19d2b77c`.
`canonical/main` was fetched read-only at `dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b`; it was not
reset, rebased, merged, or rolled back. The latest main deployment identity was preserved in the
read-only comparison below. No production environment variable, database row, provider connection,
APNs device, call, or account was mutated.

### Railway environment and database identity (read-only)

Railway reports a distinct environment and service, but not a safe mobile staging data plane:

| Target | Environment/service | Deployment | Source identity | Public result |
|---|---|---|---|---|
| Production | `production` / `life-call` | `e284947e-fbc0-451a-943c-6d28c186395f` | `Daisuke134/life-manager`, `main`, `dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b`, `apps/life-manager` | `/health` 200, `lm2a-webhook-retry-v1` |
| Railway staging label | `staging` / `life-call-staging` | `43d60679-42e5-4029-981d-b6fd67d3b08b` | `Daisuke134/anicca-products`, `dev`, `6fc7e31496dd0fe0ca897fda80e00bac4c63936d`, `apps/life-call` | `/health` 200, `lm27-voicemail-v1` |

The staging service's `SUPABASE_URL` host exactly equals production's host, and its
`SUPABASE_SERVICE_ROLE_KEY` exactly equals production's key. The values are intentionally not
written here. A request routed to the staging-labelled service would therefore mutate/read the
production Supabase project, so it cannot be called an isolated staging target.

The Railway `Postgres` service in the staging environment is a separate PostgreSQL 17.10 instance.
Read-only identity was `database=railway`, `user=postgres`; no `public.lm_users`,
`public.lm_route_cache`, `public.lm_mobile_*` table, or `public.%lm_mobile%` function was found.
The mobile migration begins with `ALTER TABLE public.lm_users` and the adapter requires Supabase
Auth/REST/RPC, so this Railway database is not a compatible substitute. The production Railway
Postgres was not queried. `supabase projects list` could not discover/create a project because the
CLI reported `Access token not provided`; no project creation or configuration mutation was attempted.

### Migration and deployment receipt

Status: `BLOCKED`; migration `apps/life-manager/migrations/2026-08-08-lm-mobile-v1.sql` was **not
applied anywhere**. There is no migration readback receipt because the only DB with the right
Railway label points at the production Supabase identity, while the separate Railway Postgres lacks
the required schema. The reviewed backend was not integrated into the old `anicca-products/dev`
staging source and no Railway deployment was triggered. The latest reviewed implementation remains
`7fcbdcc05`; the pre-existing Railway production commit remains `dcd9ad9a…` and was not changed.

### Tenant/idempotency evidence

Live staging users and sessions were not created because doing so would use the production Supabase
identity. A one-shot, non-network harness drove the real mobile router and memory store with two
isolated users/sessions to retain useful code-level evidence without touching production:

```json
{
  "bootstrapA": {"status": 200, "id": "user-a", "name": "Alice"},
  "bootstrapBWithUidQuery": {"status": 200, "id": "user-b", "name": "Bob", "queryIgnored": true},
  "sameKeyReplay": {"firstStatus": 200, "replayStatus": 200, "identical": true},
  "sameKeyDifferentBody": {"status": 409, "code": "idempotency_conflict"},
  "crossTenantUidInjection": {"status": 400, "code": "unknown_profile_field"},
  "userAAfterAttempts": "Alice updated",
  "userBAfterAttempts": "Bob"
}
```

This is explicitly **not** a live staging receipt. It demonstrates that the reviewed router ignores a
client `uid` query, rejects a client `uid` profile field, scopes replay keys by authenticated UID,
returns the original response on same-key replay, and returns 409 for same-key/different-body.

### Provider evidence and pending side-effect gate

- Real public Transit read-only call: `https://api.transit.ls8h.com/api/v1/plan` for fixed
  Roppongi/Tokyo Tower coordinates returned HTTP 200, `journeyCount=4`, first duration `1187`
  seconds, and one first journey leg. This was a provider smoke check, not a staging router result.
- Real Calendar read was not attempted: staging has no distinct Composio/Calendar credentials and
  production Calendar data must not be used as staging data. Calendar readback remains part of the
  isolated-Supabase gate.
- No Telnyx call, APNs registration, account deletion, Calendar mutation, or other external side
  effect was invoked. A real-device/self-controlled-number call remains a separate pending gate;
  it cannot be claimed from this run.

### Verification commands

Fresh local evidence from the reviewed HEAD:

```text
cd apps/life-manager && node --test test/mobile-*.test.js
115 passing, 0 failing

cd apps/life-manager && node --test test/mobile-route.test.js test/mobile-route-projection.test.js lib/transit.test.js test/mobile-calendar.test.js
21 passing, 0 failing
```

The full installed backend suite stopped at the pre-existing dependency boundary after 41 passing
tests: `lib/taskmarket-award-handoff.test.js` fails because `viem` is missing from the installed
`node_modules`; no mobile test failed before that stop.

### Remaining gate

Provision/configure a genuinely non-production Supabase project (Auth + REST + RPC) and disposable
Calendar identity, wire a staging service to the reviewed `life-manager` source, apply and read back
the migration, deploy and verify the Railway `commitHash`/build, then repeat the live User A/User B
endpoint matrix and original-replay/conflicting-body checks. Keep Telnyx outside that run until an
explicitly self-controlled target and real-device gate exist.
