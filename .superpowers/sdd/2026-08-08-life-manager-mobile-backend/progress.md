# SDD ledger — plan: docs/superpowers/plans/2026-08-08-life-manager-mobile-backend.md

Setup: branch `feat/lm-mobile-backend-luna`, contract base `ada35f98c`.

Implementation checkpoint: `ada35f98c..0d8a9881c`; focused suite 85/85 PASS; fresh review returned nine Critical/Important findings, so Gate 3 is not complete.

Fix round 1/5: implementation complete through `8cf1486a1`. Finding 1 route/timezone/cache=`eed683458`,`806b4142f`; finding 2 contract=`9a0f22388`; findings 3–4 session secret/refresh replay=`2ba5493d0`,`8ae695e3b`; finding 5 APNs ownership=`61440a494`; finding 6 resumable deletion=`208c69103`,`d5f88c2e6`; finding 7 resumable questions=`f52c21a53`; finding 8 atomic call cap=`bc9bdaafd`; finding 9 verification harness/report=`4d00ac967`,`8cf1486a1`. Focused mobile suite 109/109 PASS. Scoped re-review is active. Live staging receipt remains absent and cannot be marked complete from the harness alone.

Fix round 1/5 review: findings 3–8 addressed; findings 1–2 remain open; finding 9 remains an explicit live deployment gate. Finding 1 requires persistent route-cache reuse and complete structured provider facts. Finding 2 requires real domain-handler/router output comparison rather than fixture-returning stubs.

Fix round 2/5: implementation complete at `87cbfdb6b`; mobile suite 112/112, real-router fixture suite 4/4 across 13 endpoints, route/store 14/14 PASS. Scoped re-review of `8cf1486a1..87cbfdb6b` is active. Live staging mutation remains deferred until code re-review passes.

Fix round 2/5 review: zero addressed, two open. Persistent cache conflict target is incompatible with the partial unique index and hides 409 write failure. Route/cursor runtime contract still injects fixture-derived route and cursor encoders.

Fix round 3/5: active for compatible persistent-cache upsert with surfaced failures and true route/cursor domain contract execution. Live staging remains deferred.

Fix round 3/5 implementation complete at `7fcbdcc05`: mobile 115/115, route/store/runtime 21/21, runtime contract 10/10 across 13 endpoints PASS. Scoped re-review of `87cbfdb6b..7fcbdcc05` is active. Live staging remains deferred.

Fix round 3/5 review: two addressed, zero open; verdict ship. Code findings 1–8 are closed.

Task 10 live staging: active with fresh implementer. Scope is distinct staging discovery, latest-main integration, migration/readback, Railway commit identity, User A/B isolation/idempotency, and real read-only Calendar/Transit provider evidence. Production must not be mislabeled or mutated as staging.

Task 10 live staging receipt — `BLOCKED` (2026-08-08): Railway read-only discovery found
`staging/life-call-staging` (`43d60679-42e5-4029-981d-b6fd67d3b08b`, commit
`6fc7e31496dd0fe0ca897fda80e00bac4c63936d`, source `Daisuke134/anicca-products`,
`apps/life-call`) and separate Railway Postgres, but its `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` exactly match production. The separate Railway Postgres is PostgreSQL
17.10 with no `lm_users`, `lm_route_cache`, `lm_mobile_*`, or mobile RPC functions, so it is not a
compatible Supabase Auth/REST/RPC staging DB. `canonical/main` was fetched at
`dcd9ad9ad3e25f1a7127ba40689653c1e2927e6b` without reset/merge/rollback; production remained
untouched. Migration was not applied, reviewed code was not deployed to the old staging source, and
no live A/B users/sessions were created. A code-level real-router/memory-store fallback recorded
User A/B scope separation, same-key replay (`200` identical), same-key/different-body
`409 idempotency_conflict`, and client-UID rejection (`400 unknown_profile_field`). A real public
Transit read-only request returned HTTP 200 with four journeys; Calendar was not read because no
distinct provider credentials exist. Fresh checks: mobile suite `115/115` and route/provider suite
`21/21`; full backend suite hit the installed baseline `viem` missing dependency after `41` passes.
Full receipt: `.superpowers/sdd/2026-08-08-life-manager-mobile-backend/task-10-report.md` and
`docs/superpowers/reports/2026-08-08-life-manager-mobile-contract-luna.md`.
