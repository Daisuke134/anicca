# TaskMarket external-work submission evidence

## Claim boundary

This evidence proves that Life Manager found a live, colony-external funded job,
built its deliverable, verified it in a real browser, and submitted the exact
artifact on Base. It does **not** prove external income. The requester has not
selected a winner, so verified external revenue remains `$0.00` and the
13c-SELL / 13c-WORK `$1.00` gate remains open.

## Live task

| Field | Readback |
|---|---|
| Marketplace | Daydreams TaskMarket |
| Task ID | `0xd87153806d9cce8012f352b6165d1ab6200d9cf462cc884286d0ed6b2450f486` |
| Requester | `0xa4d897959211c8e565F862080913b45Cc761Ac6A` |
| Mode | `bounty` |
| Reward | `2.5 USDC` escrowed |
| Status immediately before submission | `open`; `submissionWindowOpen=true` |
| Worker cost | `requiresPayment=false`; `stakeRequired=false` |
| Expiry | `2026-08-02T04:41:59.351Z` |

Primary protocol source: [TaskMarket documentation](https://docs-market.daydreams.systems/llms-full.txt).

## Dedicated worker identity

| Field | Readback |
|---|---|
| Base wallet | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| ERC-8004 agent ID | `60023` |
| Chain | Base mainnet (`8453`) |
| Credential storage | `~/.taskmarket/keystore.json`; CLI-created `0644` was corrected and read back as `0600`; no key is stored in this repository |

## Deliverable verification

The submitted artifact is
`docs/evidence/agent-economy/taskmarket-spider-bounty/index.html`.

| Check | Result |
|---|---|
| Exact artifact count | one file |
| Size | `21,967` bytes; limit is 10 MB |
| SHA-256 | `ddd4a6c15247df9620a8f6c0f7c7dd5482b8f8d74f29e37ec5f82f70d3cf1fe5` |
| Runtime | `file://`; HTML/CSS/vanilla JS only |
| Network | no external requests |
| Real-browser acceptance | `node docs/evidence/agent-economy/taskmarket-spider-bounty/game.e2e.mjs` → `PASS: spider memory game acceptance E2E` |
| Covered behavior | 16 cards/8 pairs, editable names, keyboard activation, scoring, same-player extra turn, mismatch lock/flip/player switch, winner/draw, replay, new players, 320px no-overflow, console/network error checks |
| Visual QA | real Chromium screenshots inspected at `1200×1000` and `320×700` |

## Live submission and independent readback

| Field | Readback |
|---|---|
| Submission ID | `aadbef70-3e8f-4fff-a918-1ff2d907a7db` |
| Submitted at | `2026-07-28T05:29:15.820Z` |
| Worker | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Artifact role/name | `final` / `index.html` |
| Remote size/hash | `21,967` / `ddd4a6c15247df9620a8f6c0f7c7dd5482b8f8d74f29e37ec5f82f70d3cf1fe5` |
| Deliverable hash | `0x10cad19aa92377964c1368072db66e3f066a80e06cfad34998d0349f57954dc6` |
| Base transaction | `0x87b511ab9f6e2a1da867e657836715fe977b050b176c8c8606312fb1c8762e93` |
| Receipt | block `49213605`; `status 1 (success)` |

The marketplace submissions readback matched the dedicated worker address,
file name, size, SHA-256, deliverable hash, and transaction. `cast receipt`
independently read the same transaction from Base mainnet and returned
`status 1 (success)`.

## Remaining gate

The task is competitive and had 17 submissions immediately before this
submission. Only requester award plus verified USDC receipt can advance 13c.
Polling may detect the event, but elapsed time or an unawarded submission must
never be relabelled as revenue.
