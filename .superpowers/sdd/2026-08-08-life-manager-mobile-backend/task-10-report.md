# Task 10 — Mobile v1 live staging receipt

Date: 2026-08-08 (Asia/Tokyo)
Status: `BLOCKED`
Worker branch: `feat/lm-mobile-backend-luna`
Reviewed code HEAD: `7fcbdcc055718c6104132234a5e8718d19d2b77c`

## Decision

Live staging execution is blocked. Railway has a staging-labelled service and a separate Railway
Postgres instance, but `life-call-staging` has the exact production Supabase URL and service-role
key. The separate Railway Postgres has no Life Manager mobile schema and is not the Supabase
Auth/REST/RPC database expected by the reviewed adapter. No migration, deploy, API mutation, call,
APNs registration, Calendar mutation, or production change was made.

## Read-only deployment identity

| Target | Railway identity | Observed deployment |
|---|---|---|
| Production | environment `production`, service `life-call`, service ID `ca978c74-639a-4fa1-af22-9cdd53c3f615` | deployment `e284947e-fbc0-451a-943c-6d28c186395f`, `SUCCESS`, branch `main`, commit `dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b`, repo `Daisuke134/life-manager`, root `apps/life-manager`, `/health` build `lm2a-webhook-retry-v1` |
| Staging-labelled service | environment `staging` (`0437b714-7f05-44d7-9c46-9409a6e3a99c`), service `life-call-staging`, service ID `9679f364-9e16-446d-a561-9ecbc3246e76` | deployment `43d60679-42e5-4029-981d-b6fd67d3b08b`, `SUCCESS`, branch `dev`, commit `6fc7e31496dd0fe0ca897fda80e00bac4c63936d`, repo `Daisuke134/anicca-products`, root `apps/life-call`, `/health` build `lm27-voicemail-v1` |

`canonical/main` was fetched read-only at `dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b`; the
reviewed branch was not reset, rebased, merged, or rolled back. The old staging source was not
rewired because its database identity is unsafe.

## Database identity and migration readback

- `life-call-staging` `SUPABASE_URL` host equals production's host exactly.
- `life-call-staging` `SUPABASE_SERVICE_ROLE_KEY` equals production's key exactly. Raw values are
  intentionally absent from this receipt.
- The staging Railway `Postgres` service is a different PostgreSQL 17.10 instance. Read-only
  identity: `database=railway`, `user=postgres`.
- Read-only schema/function probes found no `public.lm_users`, `public.lm_route_cache`, any
  `public.lm_mobile_*` table, or any `public` function whose name matches `%lm_mobile%`.
- Migration `apps/life-manager/migrations/2026-08-08-lm-mobile-v1.sql`: **not applied**. No
  migration readback exists because applying it to the staging-labelled service would hit the
  production Supabase project; applying it to Railway Postgres would target an incompatible DB.
- `supabase projects list` could not discover a separate project because the CLI reported
  `Access token not provided`; no project creation/configuration mutation was attempted.

## User A/B and idempotency

Live staging users/sessions were deliberately not created. The following code-level fallback used
the real `handleMobileV1Request` and memory store with two isolated users/sessions and no network:

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

This fallback is not live staging evidence. It only shows the reviewed router's tenant-derived
scope, no client `uid` authority, same-key response replay, and same-key/different-body 409.

## Provider evidence

- Real public Transit read-only request to `https://api.transit.ls8h.com/api/v1/plan` with fixed
  Roppongi/Tokyo Tower coordinates: HTTP 200, four journeys, first duration 1187 seconds, one
  first journey leg. It was not routed through the un-deployed staging service.
- Real Calendar read was not attempted. The staging-labelled service lacks distinct Calendar/
  Composio credentials, and production Calendar data is out of scope for staging evidence.
- Telnyx, APNs, account deletion, Calendar mutation, and all other irreversible provider actions
  were not invoked. Test-call execution remains a separate real-device/self-controlled-target
  gate.

## Verification

```text
cd apps/life-manager && node --test test/mobile-*.test.js
115 passing, 0 failing

cd apps/life-manager && node --test test/mobile-route.test.js test/mobile-route-projection.test.js lib/transit.test.js test/mobile-calendar.test.js
21 passing, 0 failing
```

The full installed backend suite reached 41 passing tests, then stopped at the installed baseline
dependency boundary: `lib/taskmarket-award-handoff.test.js` cannot load `viem` from `node_modules`.
No mobile test failed before that boundary.

## Remaining gate

Provide a genuinely non-production Supabase project with Auth/REST/RPC and disposable Calendar
identity; point a staging service at the reviewed `life-manager` source; apply/read back the
migration; deploy and verify Railway `commitHash`/build; then run live A/B endpoint, replay/conflict,
Calendar, and Transit checks. Keep Telnyx pending until a self-controlled target and real-device
approval gate are present.
