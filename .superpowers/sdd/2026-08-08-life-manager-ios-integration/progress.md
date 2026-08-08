# SDD ledger — Life Manager iOS final integration

## Scope

- Worktree: `/Users/anicca/anicca-project/.worktrees/lm-ios-integration-final`
- Branch: `feat/lm-ios-integration-final`
- Base: `006a4d862` (`canonical/main` at integration start)
- No staging/production environment or deployment mutation is permitted in this slice.

## Integration checkpoint

- Reviewed provider-cost branch `2fd0edea6` merged with a normal `--no-ff` 3-way merge.
- Reviewed mobile-backend branch `fec844d5f` merged with a normal `--no-ff` 3-way merge.
- `apps/life-manager/server.js` retains provider budget wiring and `/api/mobile/v1` routing.

## Route-cache contract slice — RED/GREEN

RED was observed before implementation:

- provider store tests used an unscoped `cache_key` query and `on_conflict=cache_key`;
- mobile store wrote `route` plus fabricated `mobile:<digest>`, `mobile:v1`, and `time_bucket=0` legacy values;
- follow-up migration contract was absent.

GREEN after implementation:

```text
node --test lib/route-cache.test.js test/mobile-store.test.js test/route-cache-identity-migration.test.js
29 passing, 0 failing
```

The canonical identity is `(uid, cache_key)`. Provider reads accept `get(key,{uid})`, and
`makeRouteCache` passes the authenticated UID to all durable reads/writes. Both adapters persist
`route_result` and exact `on_conflict=uid,cache_key`; mobile reads `route_result` first and falls back
to `route` during migration. Legacy NOT NULL fields are populated from actual request/provider facts;
missing facts or HTTP persistence failures are surfaced as retryable failures. Cross-adapter reads,
identical keys across tenants, and conflict inference are covered.

The additive migration is
`apps/life-manager/migrations/2026-08-08-lm-route-cache-identity.sql`. It adds missing columns,
backfills `route` into `route_result` without deleting old rows, drops old global/legacy indexes,
creates a non-partial `(uid,cache_key)` unique index, and validates canonical rows with a staged
`NOT VALID`/`VALIDATE CONSTRAINT` check. No unsafe rolling column rewrite is present.

## Focused regression evidence

```text
node --test test/mobile-*.test.js
121 passing, 0 failing

node --test test/mobile-route.test.js test/mobile-store.test.js test/mobile-migration-contract.test.js \
  test/route-cache-identity-migration.test.js lib/route-cache.test.js
41 passing, 0 failing

node --test lib/provider-cost-adapters.test.js lib/provider-cost-imports.test.js lib/composio-budget.test.js \
  lib/mail-resend.test.js lib/ledger.test.js lib/travel-transit-wire.test.js lib/transit.test.js \
  lib/route-cache.test.js lib/travel-routes.test.js test/provider-cost-contract.test.js lib/provider-budget.test.js \
  test/provider-budget-gate.test.js test/testcall-amd-hangup-http-contract.test.js
119 passing, 0 failing
```

The provider run required the declared local dependencies (`npm ci --ignore-scripts`); it changed
only the untracked `node_modules` directory. No tracked package or lockfile changed.

## Remaining integration gates

- Fresh review of this integration diff.
- Live isolated staging migration/readback and HTTP route/provider evidence.
- iOS build/route/UI integration, Maestro evidence/video, signed TestFlight archive and real-device
  user validation. App Store submission remains blocked until TestFlight validation is complete.
