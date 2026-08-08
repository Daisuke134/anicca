# Life Manager iOS final integration — route-cache receipt

## Evidence

The integration worktree merged reviewed provider-cost `2fd0edea6` and reviewed mobile-backend
`fec844d5f` with normal three-way merges. The server still mounts `/api/mobile/v1` and preserves the
provider budget guard. No staging or production mutation was performed.

The route-cache identity is now `(uid, cache_key)`. The provider Supabase adapter scopes every read
and write by UID and uses `on_conflict=uid,cache_key`; `makeRouteCache` forwards the UID. Mobile and
provider rows use `route_result` as the canonical structured payload. Mobile reads the old `route`
column only as a migration-period fallback. Both writers derive the legacy required fields from the
real route request/result and fail closed when a required fact or persistence response is missing.

The follow-up migration preserves old rows, copies `route` to `route_result`, removes conflicting
global/old identity indexes, creates a non-partial `(uid,cache_key)` unique index, and uses staged
constraint validation without a rolling column rewrite.

## Verification

- Route/cache/migration contract: **29/29 PASS**.
- Full mobile focused suite: **121/121 PASS**.
- Route/store/migration regression: **41/41 PASS**.
- Provider-cost/budget/transit/route/HTTP focused suite: **119/119 PASS**.
- Local Postgres was unavailable (`pg_isready`: no response on `/tmp:5432`), so migration-order
  validation is recorded as exact SQL contract tests, per the integration task.

## Boundaries

This receipt does not claim live staging, Calendar/Transit deployment, iOS build, Maestro video,
TestFlight, APNs, or App Store readiness. Those gates require a fresh integrated review and real
environment/device evidence.
