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
| 1. Persistent geocodes | GREEN | missing-module | 6/6 focused + 43/43 baseline | `3381cf717` |
| 2. Durable route cache | GREEN | original suite + new scope tests | 15/15 route/transit + 62/62 travel regression | `826d2837d` |
| 3. Transit facts/fallback | GREEN | structured projection + anchor tests | 31/31 transit/route tests; 59/59 combined focused | `19f411f39` |
| 4. Truthful cost event | GREEN | 5 contract failures (missing API) | 12/12 ledger contract | `062663d73` |
| 5. Provider instrumentation | GREEN | adapter module/import module missing | 77/77 provider + focused regression | `0c6616b86` |
| 6. Budget policy | GREEN | missing-module | 12/12 budget/gate + 90/90 full focused | `a7604f2a6` |
| 7. Owner report/deploy/measure | code-only pending | — | — | — |
| Review fix 1. Durable route writer | GREEN | 2 route contract failures | 37/37 route/transit | `d3406be56` |
| Review fix 2. Status/classification | GREEN | 9 ledger/adapter/import failures | 25/25 provider cost | `a14e05c84` |
| Review fix 3. Google attempts | GREEN | failure-path/request-id contracts | 17/17 geocode/adapters | `f95183d04` |
| Review fix 4. Atomic budget/voice | GREEN | 2 migration/RPC contracts | 106/106 complete focused | `e6967878d` |
| Review follow-up. Voice-only read | GREEN | default reader scope gap | 14/14 budget | `290cf460c` |
| Review follow-up. Persisted estimate | GREEN | persisted-threshold E2E gap | 7/7 geocode | `5abcb6cdb` |
| Final fix 1. RPC privileges | GREEN | missing SECURITY DEFINER revoke/grant contract | 15/15 budget | `8baf3c602` |
| Final fix 2. Atomic daily cap + Google fallback claims | GREEN | missing SQL daily-cap params and per-attempt gate | 60/60 baseline + 37/37 guard | `5a5dd201c` |
| Final fix 3. Conflict replay/idempotent retries | GREEN | duplicate 409/replay returned failure | 33/33 budget/ledger/import | `a30e1d3ea` |
| Final fix 4. Telnyx reservation propagation/settlement | GREEN | reservation ID stopped at dial boundary | 24/24 reservation contracts + syntax checks | `85e6a1de6` |
| Final fix 5. Telnyx legacy summary dual-write | GREEN | new dimensions were invisible to businessSummary | 20/20 adapter/summary contracts | `e4b9b1cdd` |
| Final verification fixture | GREEN | HTTP test-call fixture did not model the paid-call budget claim | 123/123 combined focused | `301bd770e` |

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

## Task 4 receipt

- RED: `node --test lib/ledger.test.js test/provider-cost-contract.test.js` → legacy 7 tests passed, all 5 new contract tests failed (missing migration failure table and `recordProviderCost`).
- GREEN: same command → 12/12 passed.
- `recordProviderCost` validates all dimensions, preserves nullable actual billing, defaults absent actuals to `actual_status="unknown"`, and rejects contradictory/invalid statuses without writing.
- Ledger failures return `false` and emit a structured `provider_cost_ledger_write_failed` event through the configured owner alert and durable outbox seam.
- Migration adds additive ledger columns, actual-status check, request idempotency index, and service-role-only failure outbox table.

## Task 5 receipt

- RED: `node --test lib/provider-cost-adapters.test.js` failed at module load with `Cannot find module './provider-cost-adapters.js'`.
- GREEN (adapter core): the new recorder adapters cover Google Geocoding/Routes, Transit, Composio, Gemini, Telnyx CDR, Resend, Railway, and Supabase; `node --test lib/provider-cost-adapters.test.js` → 10/10 passed.
- GREEN (runtime wiring): geocode misses, Google Routes/legacy transit, Transit `/plan` + guidance, Composio calls, Resend sends, Gemini Live sessions, and Telnyx call sessions now emit complete events. Cache hits do not emit provider spend.
- GREEN (scheduled imports): `provider-cost-imports.js` imports Telnyx CDR actuals and Railway/Supabase allocations; loader failures return a failure receipt and write no synthetic zero row. `node --test lib/provider-cost-imports.test.js` → 3/3 passed.
- GREEN focused verification: `node --test lib/provider-cost-adapters.test.js lib/provider-cost-imports.test.js lib/composio-budget.test.js lib/mail-resend.test.js lib/ledger.test.js lib/travel-transit-wire.test.js lib/transit.test.js lib/route-cache.test.js lib/travel-routes.test.js test/provider-cost-contract.test.js` → 77/77 passed.

## Task 6 receipt

- RED: `node --test lib/provider-budget.test.js` failed at module load with `Cannot find module './provider-budget.js'`.
- GREEN: pure policy covers normal/warning/degraded/stopped thresholds at `$0.50/$1.00/$2.00`, preserves unknown billing as a reason, and enforces independent user/global voice caps.
- GREEN: cached route/calendar/geocode reads bypass budget reads; denied Google geocoding/fallback, nonessential Composio refresh, and Telnyx calls make zero paid-provider requests. Gemini Live checks the gate before opening a session.
- GREEN: migration adds unique `(uid,budget_day,request_id)` atomic claim identity; `claimProviderBudget` provides the service-role insert seam.
- Verification: `node --test lib/provider-budget.test.js test/provider-budget-gate.test.js` → 12/12 passed; the complete plan verification command (baseline + geocode + cost adapters/imports + budget + all contract tests) → 90/90 passed. The original pre-change baseline remains the recorded 43/43; the 54/54 route/ledger/Composio run includes the Task 5 Composio assertion added afterward.

## Fresh review fix 1 receipt — durable route writer

- RED: added route-store contract tests failed because `uid/from_geo/to_geo/time_bucket/duration_secs` were sent as NULL and the cache ignored a `set()` false result (2 failures).
- GREEN: `node --test lib/route-cache.test.js lib/travel-transit-wire.test.js lib/travel-routes.test.js` → 37/37 passed.
- Route records now carry canonical uid/geos/time bucket through the cache boundary; the REST writer serializes legacy `text` geos, rejects incomplete NOT NULL rows, uses `on_conflict=cache_key`, and propagates failed durable writes instead of returning an unpersisted result.
- Migration replaces the prior partial cache-key index with a non-partial unique index usable by Supabase conflict resolution. Cross-instance contention and failed writes are covered by tests.

## Fresh review fix 2 receipt — actual status contract and SKU estimates

- RED: contract tests rejected the old `measured|estimated|unknown` status model and exposed missing `cost_classification`/legacy `est_usd` dual writes (9 failures across ledger/adapters/imports).
- GREEN: `node --test lib/provider-cost-adapters.test.js lib/provider-cost-imports.test.js lib/ledger.test.js test/provider-cost-contract.test.js` → 25/25 passed.
- `actual_status` is now only `known|unknown`; measured/estimated/fixed/unknown move to `cost_classification`. The migration normalizes prior rows before installing both checks.
- Provider writes include `cost_classification` and atomically dual-write `estimated_usd` plus legacy `est_usd`. Google Geocoding, Routes, and Directions Transit have versioned non-zero per-SKU projections; Telnyx/imported allocations use `known` + `measured` when an actual amount exists.

## Fresh review fix 3 receipt — Google attempt accounting

- RED: added failure-path and request-identity tests required a geocode ledger row for empty/HTTP-error/thrown responses and distinct IDs for concurrent Google SKUs.
- GREEN: `node --test lib/geocode-cache.test.js lib/provider-cost-adapters.test.js` → 17/17 passed.
- Geocoding records exactly once immediately before each actual Google request, including failures and empty results; cache hits and budget-denied calls remain unrecorded. Routes/legacy Transit and free transit plan/guidance now append a UUID to every actual-attempt request ID, preventing provider/request uniqueness collisions.

## Fresh review fix 4 receipt — atomic budget/voice claims and production wiring

- RED: migration/RPC tests failed because budget claims were an optional REST insert and there were no voice reservation/settlement buckets (2 failures).
- GREEN: complete focused guard suite → 106/106 passed.
- Added `lm_provider_voice_buckets`, idempotent settlements, and transactional `lm_claim_provider_budget`/`lm_settle_provider_voice` RPCs. The claim locks user then global daily buckets and atomically accounts for reservations; known Telnyx CDRs settle actuals without turning unknown into zero.
- Production authorization now claims every billable provider operation with a unique request ID and non-zero projection (Telnyx default `$0.05`, Gemini `$0.023`, Google SKU defaults, Composio/Resend defaults); cache-hit exits before reads/claims. Telnyx dial, Gemini Live, Composio, Resend, CDR webhook/imports, Railway/Supabase scheduled measurement loaders are wired.
- Follow-up regression: the default voice reader now passes `voiceOnly=true` to the ledger query (not just the in-memory aggregation), and its URL filter is covered by `node --test lib/provider-budget.test.js` → 14/14.
- Follow-up persisted-threshold regression: an empty Google response through the real ledger writer stores `estimated_usd > 0`, `actual_billed_usd = null`, and `actual_status = unknown`; `node --test lib/geocode-cache.test.js` → 7/7.

## Final review fix round receipt

- Security: both SECURITY DEFINER RPCs now explicitly revoke `PUBLIC`, `anon`, and `authenticated`, then grant only `service_role`. The migration contract checks exact function signatures and grants.
- Atomic cap: the claim RPC always locks the user/day bucket, reads settled `lm_api_cost` amounts and outstanding reservations in the same transaction, and rejects a projected request at the daily cap. Voice reservations still lock global after user; unknown/null billing is not coerced to zero.
- Google fallback: Routes and Directions are sequential. Each concrete provider attempt gets a distinct request ID and claim immediately before its request; a denied Directions claim emits no Directions request. Existing in-flight URLs remain valid through the legacy eight-field HMAC fallback when no reservation field is present.
- Replay: claims use `ON CONFLICT ... DO NOTHING RETURNING`; ledger/provider/import 409 conflicts are successful no-ops. Concurrent ledger retries are covered by a two-writer test.
- Telnyx reservation: generated dial reservation IDs travel through signed stream context, client state, webhook CDR, scheduled imports, and exact voice settlement. Settlement has a unique `(uid,budget_day,reservation_request_id)` index and releases the matching `reserved_usd` exactly once.
- Legacy summary: Telnyx CDR and call-session rows dual-write provider dimensions plus `kind=telnyx_call`, `meta`, and `est_usd` compatibility fields; a 60-second fixture produces one call and one minute in `businessSummary`.
- Focused verification: plan baseline command → 60/60 passed; cost guard command → 37/37 passed; final combined geocode/budget/ledger/route/Telnyx/HTTP suite → 123/123 passed. The HTTP `/test-call` fixture permits exactly one atomic budget claim while still rejecting wake-log and unrelated Supabase traffic. No production env/deploy was performed.
- Full-suite verification after `npm ci`: `npm test` reached the existing legacy-path scanner and reported exactly one pre-existing failure in `scripts/scan-legacy-paths.test.js` for the two connector runtime `${HOME}/.openclaw/.env` lines; no changed provider-cost test failed. Before the clean install, direct HTTP tests were temporarily blocked by absent declared modules (`canonicalize`, `ws`); `npm ci` restored them.
- Final full-suite verification after the HTTP fixture update: `npm test` reported 17/18 in the existing `test:legacy-paths` target; the only failure remains the same two pre-existing connector runtime `${HOME}/.openclaw/.env` references (`connector-host-bridge-boot.sh:6`, `deploy-connector-runtime.sh:7`). The 123/123 focused provider-cost/Telnyx/HTTP suite remains green. This baseline is intentionally untouched.
