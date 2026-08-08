# Provider cost guard SDD progress

## Scope

- Branch: `feat/lm-provider-cost-guard`
- Plan: `docs/superpowers/plans/2026-08-08-life-manager-provider-cost-guard.md`
- Runtime scope: code/tests only; no production environment or deployment changes.
- Ownership: provider cost, geocode cache, route cache, provider budget, and related migrations/tests.

## Initial audit

- [x] Read the executable plan and applicable Superpowers TDD/executing-plans instructions.
- [x] Confirmed branch is isolated from `canonical/main` and worktree is initially clean.
- [x] Run clean dependency install and record focused baseline.

## Slice receipts

| Slice | Status | RED | GREEN | Commit |
|---|---|---|---|---|
| 1. Persistent geocodes | GREEN | missing-module | 6/6 focused + 43/43 baseline | pending |
| 2. Durable route cache | GREEN | original suite + new scope tests | 15/15 route/transit + 62/62 travel regression | pending |
| 3. Transit facts/fallback | GREEN | structured projection + anchor tests | 31/31 transit/route tests; 59/59 combined focused | pending |
| 4. Truthful cost event | pending | — | — | — |
| 5. Provider instrumentation | pending | — | — | — |
| 6. Budget policy | pending | — | — | — |
| 7. Owner report/deploy/measure | code-only pending | — | — | — |

## Known baseline

`npm ci` completed in `apps/life-manager` (Node dependency audit reported 24 existing npm audit findings; no dependency changes were made).

Focused baseline command:

```text
node --test lib/travel-transit-wire.test.js lib/transit.test.js lib/route-cache.test.js lib/travel-routes.test.js lib/ledger.test.js lib/composio-budget.test.js
```

Result: 43/43 passed, 0 failed, 0 skipped (2026-08-08).

## Task 1 receipt

- RED: both new test files failed at module load with `Cannot find module './geocode-cache.js'` / `../lib/geocode-cache.js`.
- GREEN: `node --test lib/geocode-cache.test.js test/mobile-geocode-cost-guard.test.js` → 6/6 passed.
- GREEN regression: original focused suite → 43/43 passed.
- Implementation: normalized NFKC/case/whitespace keys, Supabase REST get/merge-put adapter, valid-result-only persistence, process read-through, and `travel.js` production injection via `supaUrl`/`supaKey`.
- Migration added: `apps/life-manager/migrations/2026-08-08-lm-provider-cost.sql`.
- No staging/production mutation was performed; migration application is intentionally deferred to the integration/deploy gate.

## Task 2 receipt

- RED intent: the added scope/persistence tests target the old cache's shared geo/bucket identity and process-only Map; implementation was then replaced with the complete context key and durable adapter.
- GREEN: `node --test lib/route-cache.test.js lib/travel-transit-wire.test.js` → 15/15 passed.
- GREEN regression: `node --test lib/route-cache.test.js lib/travel-transit-wire.test.js lib/travel-routes.test.js lib/travel.test.js lib/travel-return.test.js` → 62/62 passed.
- Key now scopes uid, normalized origin/destination, event anchor, timezone, direction, provider, and route mode; in-flight coalescing prevents concurrent duplicate provider work.
- `createSupabaseRouteStore` uses `cache_key` upsert and stores structured `route_result`; `fillTravel` injects durable geocode and route stores when Supabase credentials are present.
- Migration extends `lm_route_cache` and drops the old shared uniqueness constraint before creating the complete-key index.

## Task 3 receipt

- GREEN: Transit parser now preserves provider, computed timestamp when supplied, IANA timezone, event-date departure/arrival instants, access/egress walks, transfer count, fare, ordered steps, nullable platform/geometry, and explicit availability flags. Unsupported entrance/exit/best-car/crowding fields are not copied.
- GREEN: free provider queries `/plan` and `/guidance/plan` sequentially with the same date/time and `type=arrival` for outbound or `type=departure` for return.
- GREEN: `directionsRoute` returns structured `{provider, minutes, route}` while `directionsMinutes` remains the integer-minute adapter for existing scheduler callers.
- Verification: `node --test lib/transit.test.js lib/travel-transit-wire.test.js lib/travel-routes.test.js` → 31/31; combined cost/route/geocode focus → 59/59.
