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

The production cutover and post-cutover route/ledger/downtime readbacks are
recorded below after the canonical commit is deployed.

## Post-cutover readback

Pending canonical merge and Railway source cutover.
