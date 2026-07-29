# x402 production source consolidation

## Scope

Railway production service `x402-agents` must keep serving the same nine paid
routes while its deploy source moves from the unavailable
`Daisuke134/anicca.ai` repository to canonical
`Daisuke134/life-manager/services/x402-endpoint`.

## Pre-cutover readback

| Check | Observed result |
|---|---|
| Railway service | `x402-agents`, service ID `0e526a0c-c596-424c-be47-f949966aa277` |
| Production source | `Daisuke134/anicca.ai` |
| Public domain | `x402-agents-production.up.railway.app` |
| Active deployment | `5ee685de-b623-4b7a-8d57-b12c027837be`, `SUCCESS` |
| Health | `GET /health` → HTTP 200 |
| Discovery | `GET /openapi.json` → HTTP 200, nine operations |
| Paid gate | `GET /funding-rates` without payment → HTTP 402 |

The running image is healthy, but the configured source repository is no
longer available through the GitHub repository API. The reproducible seller
source was recovered from the merged `anicca-products` history:

- [PR #375](https://github.com/Daisuke134/anicca-products/pull/375) — live
  funding-rate product and route tests.
- [PR #376](https://github.com/Daisuke134/anicca-products/pull/376) — single
  discovery/OpenAPI catalog.
- [PR #377](https://github.com/Daisuke134/anicca-products/pull/377) — public
  discovery metadata outside the paid rate limiter.
- [PR #378](https://github.com/Daisuke134/anicca-products/pull/378) — external
  discovery proof.

## Canonical migration verification

| Check | Result |
|---|---|
| Historical source baseline | 11 files / 68 tests PASS |
| TDD RED | canonical migration contract failed because `src/lib/discovery.js` did not exist |
| TDD GREEN | exact nine-route catalog and OpenAPI operations PASS |
| Canonical seller suite | 11 files / 68 tests PASS |
| Canonical migration contract | 1/1 PASS |
| Dependency audit | 0 vulnerabilities after aligned x402 2.20 packages, Vitest 4.1.10, and axios override |
| Secret pattern scan | 0 |
| `git diff --check` | PASS |

## Post-cutover readback

| Check | Result |
|---|---|
| Canonical PR | [#1295](https://github.com/Daisuke134/life-manager/pull/1295), exact-five security checks GREEN |
| Merge commit | `4d5c60b93921cbb6038c91e0142980204c01e211` |
| Railway source | `Daisuke134/life-manager` |
| Railway trigger | `Daisuke134/life-manager`, branch `main`, trigger `1a44aa21-8f65-498b-b28c-eb75c6a47c58` |
| Railway root/config | `services/x402-endpoint`, `/services/x402-endpoint/railway.toml` |
| Deployment | `cee9598d-e33d-4288-8eeb-fb9117d2be31`, `SUCCESS`, exact merge commit |
| Runtime manifest | Nixpacks, `/health`, `npx prisma generate && node src/server.js` |
| Paid route gate | all eight POST tools and `GET /funding-rates` returned HTTP 402 without payment |
| Public routes | `/health`, `/openapi.json`, `/settlements` returned HTTP 200 |
| Settlement observer | three public finalized rows; external funding-rate sale tx `0x1181e8c15039a9d83fb4b9b7c047178d9a652c84fe8bb2e6eba743d9d6233779` present exactly once |
| Life Manager ledger tests | 22/22 PASS after fresh `npm ci` |
| Real ledger loop | existing `ai.anicca.life-manager-x402-ledger` run count 403→404, exit 0; verified sale remained exactly one row (`recorded=0`, `duplicates=1`, `chain_rejected=0`) |
| Cutover availability | 251 consecutive `/health` samples from `2026-07-29T11:42:13Z` through `11:47:01Z`: HTTP 200 = 251, non-200 = 0 |
| Old source dependency | Railway service source, deployment trigger, root, config, and latest deployment contain zero `anicca.ai` dependency |

The source migration is complete. This proves reproducible canonical ownership
of the already-running seller; it does not claim a new external sale occurred
during this cutover.
