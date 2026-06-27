# Verification Architecture — founder-x402-self-facilitate (Phase 1b, lean)

Feature: `founder-x402-self-facilitate` · Mode: lean · Date: 2026-06-28
Pairs with `behavioral-spec.md`.

## Purity boundary map

| Component | Side | Reason |
|---|---|---|
| Route table literal (`{"POST /social/x": {...}}`) | **PURE data** | Plain JS object; deterministic; testable without env. |
| `declareDiscoveryExtension({output:{example,schema}})` result | **PURE data** | Returns a plain config object. |
| `privateKeyToAccount(EVM_PRIVATE_KEY)` | **IMPURE** | Reads env; deterministic given env, but env IS an environmental side-effect. |
| `createWalletClient({chain: base, transport: http()})` | **IMPURE** | Holds a network transport; will make RPC calls when settling. |
| `new x402Facilitator()` + `registerExactEvmScheme` | **IMPURE** | Holds a stateful facilitator + signer references. |
| `app.listen(port, cb)` | **IMPURE** | Binds a port. |
| Pre-bind env check (REQ-006) | **PURE** | Pure function over `process.env`; returns boolean / throws. |
| `GET /health` handler | **PURE-ish** | Constant response; pure given no Prisma. |
| `GET /metadata` handler | **PURE** | Returns the literal route table description. |

**Purity test rule**: all PURE pieces are unit-tested without binding a port, mocking facilitator init via `vitest` spies on `@x402/core/facilitator`. IMPURE pieces are integration-tested with supertest + mocked viem.

## Proof obligations (PROP-XXX ↔ REQ-XXX)

Tier 0 = required to land. Tier 1 = strong-pass. Tier 2 = nice-to-have. Lean mode marks only Tier 0 as `required:true`.

| ID | Covers | Tier | Required? | Verification |
|---|---|---|---|---|
| **PROP-001** | REQ-001 | 0 | yes | **static**: `grep -rE "HTTPFacilitatorClient" apps/x402-agents/src/` returns 0 matches; `grep -rE "x402Facilitator|registerExactEvmScheme" apps/x402-agents/src/` returns ≥ 2 matches. |
| **PROP-002** | REQ-002 | 0 | yes | **unit**: spy on `paymentMiddleware`; the config passed has every paid route with `payTo === process.env.X402_WALLET_ADDRESS`. |
| **PROP-003** | REQ-003 | 1 | no | **static + unit**: `grep -rE "baseSepolia|eip155:84532" apps/x402-agents/src/` returns 0; `grep -rE "from 'viem/chains'" apps/x402-agents/src/` shows `base` imported; unit test asserts `evmSigner` resolved from `EVM_PRIVATE_KEY`. |
| **PROP-004** | REQ-004 | 0 | yes | **unit**: the `paymentMiddleware` config object has EXACTLY one key `"POST /social/x"`; that route's `accepts` has `scheme:"exact"`, `price:"$0.003"`, `network:"eip155:8453"`, `payTo` equals env. |
| **PROP-005** | REQ-005 | 0 | yes | **unit**: the `/social/x` config's `extensions` field includes the result of `declareDiscoveryExtension({output:{example,schema}})`; spy on `declareDiscoveryExtension` to assert call args; `GET /metadata` reports `discoverable:true`. |
| **PROP-006** | REQ-006 | 1 | no | **integration**: spawn `node src/server.js` with empty `EVM_PRIVATE_KEY` → exits non-zero within 2s; stderr contains `Missing required env vars`. Spawn again missing `X402_WALLET_ADDRESS` → same. |
| **PROP-007** | REQ-007 | 0 | yes | **static**: `grep -rE "@coinbase/x402\|CDP_API_KEY\|x402\\.org/facilitator\|RAILWAY_\|DATABASE_URL\|OPENAI_API_KEY" apps/x402-agents/src/` returns 0 matches under `src/server.js` and `src/lib/x402/` paths. |
| **PROP-008** | REQ-008 | 0 | yes | **integration**: supertest `GET /health` → 200, body `{status:"ok",service:"x402-agents"}`; runs without any DATABASE_URL set. |
| **PROP-009** | REQ-009 | 1 | no | **integration**: supertest `GET /metadata` → 200, body matches the spec's literal shape. |
| **PROP-010** | REQ-010 | 1 | no | **meta**: `npm test` runs under `--reporter=verbose` with the network disabled (`UV_THREADPOOL_SIZE=1` + assertion that no real RPC URLs were hit by inspecting a vitest spy on `http.request`). |
| **PROP-011** | REQ-011 | 0 | yes | **integration**: spawn `node src/server.js` with ONLY `EVM_PRIVATE_KEY=<test key>` + `X402_WALLET_ADDRESS=<test addr>` set (no DB, no OpenAI key, no CDP, no Railway env) → boots successfully, `/health` returns 200 within 2s. |
| **PROP-012** | REQ-012 | 2 | no | **no-mock E2E (deferred to F2 host + F3 gas + F4 list + F5 heartbeat)**: a self-buy succeeds on Base mainnet; INV-7 in `record-earn.mjs` rejects it as a self-payment (NOT earn). First external buyer → INV-7 accepts → ledger row written. Verified on BaseScan. |

## Tiering rationale

- Tier 0 (PROP-001/002/004/005/007/008/011) = the things that, if violated, mean the swap didn't actually happen or the replicable contract is broken. These MUST pass for the adversary gate (Phase 1c).
- Tier 1 (PROP-003/006/009/010) = quality reinforcements; their failure means a smell, not a wrong implementation.
- Tier 2 (PROP-012) = real on-chain proof; only verifiable AFTER F2-F5 complete because it needs a public host + gas + listing.

## Anti-fake gate (HARD 0.31 + INV-7)

- Any unit/integration test that mocks `facilitator.settle` to return success MUST log `[MOCKED]` in test output; coverage of `facilitator.settle` for the goal-bearing on-chain settle is OUT OF SCOPE here — that flows through the parent `record-earn.mjs`'s INV-7 cursor in Phase 2 (F1 E2E task).
- No `console.log("settled!")` or similar that could imitate success without a real tx hash; the only place a settle success is recorded is `record-earn.mjs` (out of this feature).

## Replicability assertion (the bridge to Tier-2 children)

PROP-007 + PROP-011 + REQ-007 + REQ-011 together encode the replicability contract: a self-funded child can clone the same `src/server.js`, set only `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` from its OWN wallet, and boot on any of the H1-H5 host rails — no Dais creds, no shared infra. This is what makes F1 a teachable skill (HARD 0.40 GLVS step 4: teach the swarm).

## Done (Phase 1b)

This file commits to: 12 proof obligations, 7 Tier-0 required, the rest Tier 1/2. Phase 1c adversary review will check the spec/architecture for: missing edge cases, ambiguous EARS, weak verification, purity boundary leaks, unfalsifiable claims.
