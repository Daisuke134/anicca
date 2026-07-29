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

PR [#1295](https://github.com/Daisuke134/life-manager/pull/1295) merged as
`4d5c60b93921cbb6038c91e0142980204c01e211`. Its pull-request run and the
post-merge `main` run both passed the exact five security jobs.

| Check | Result |
|---|---|
| Railway source | `Daisuke134/life-manager`, branch `main` |
| Root / config | `services/x402-endpoint` / `/services/x402-endpoint/railway.toml` |
| Deployment | `1062874a-1f9b-4338-bf63-f89b319006ef`, `SUCCESS`, exact commit `4d5c60b93921cbb6038c91e0142980204c01e211` |
| Runtime initialization | Prisma client generated; x402 initialized on `eip155:8453`; payment middleware active |
| Health / discovery | HTTP 200 / HTTP 200 with exactly nine operations |
| Paid-route gate | all eight POST routes and `GET /funding-rates` returned HTTP 402 without payment |
| Settlement observer | HTTP 200; three bounded public records; all matched the closed public receipt schema |
| Ledger regression | `x402-sale-ledger` plus production observer tests 22/22 PASS |
| Old source dependency | Railway source/config contains no `Daisuke134/anicca.ai` dependency |
| Observed downtime | zero: five `/health` requests were HTTP 200 and Railway recorded no 5xx during the cutover window |

The cutover created overlapping builds because both source connection and the
explicit from-source deployment targeted the same commit. Railway retained the
newest healthy deployment and removed the superseded builds; only one
production deployment remains active.
