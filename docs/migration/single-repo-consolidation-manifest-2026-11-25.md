# Single-Repo Consolidation — Migration Manifest

- Plan: anicca-ops `files/single-repo-consolidation-plan-2026-11-25.md` (canonical, private repo)
- Destination: this repo, `Daisuke134/anicca` (PUBLIC)
- Sources: `Daisuke134/anicca-products` (PUBLIC), `Daisuke134/anicca-ops` (PRIVATE, public-class content only)
- Rule: nothing private moves here. Credentials, personal data, KYC/ID material, raw PII ledgers stay in the private layer (`private/` submodule → anicca-ops, Phase 4). `.gitignore` in this repo carries explicit blocks for the vault filename, `private/`, `**/credentials*.json`, and `me-data/` as defence-in-depth.

## Status

| Phase | Content | Status |
|---|---|---|
| 0 | Guardrails: plan + this manifest + .gitignore hardening | IN PROGRESS (2026-11-25) |
| 1 | anicca-products → `products/` (de-duplicate `apps/landing` first) | not started |
| 2 | anicca-ops `files/` public class → `ops/company/` (squashed snapshot, provenance per batch) | not started |
| 3 | anicca-ops Class S (ACTIVITY / team-outbox) sanitised copies | not started |
| 4 | `private/` submodule wiring (→ anicca-ops) | not started |

## Batch log

| Date | Batch | Source → Dest | Files | Bytes | Scan | Commit |
|---|---|---|---|---|---|---|
| 2026-11-25 | Phase 0 | — (manifest + .gitignore only) | 2 | — | n/a | (this file's commit) |

## Measured source sizes (GitHub API, 2026-11-25)

- anicca (this repo): 1,769,867 KB, PUBLIC
- anicca-ops: 671,434 KB, PRIVATE — `files/` = 1,974 files, `team-outbox/` = 31 lanes
- anicca-products: 1,397,273 KB, PUBLIC
