# Behavioral Spec — founder-x402-self-facilitate (Phase 1a, lean)

Feature: `founder-x402-self-facilitate`
Date: 2026-06-28
Builder = main agent (me). Adversary = fresh `vcsdd:vcsdd-adversary` (Phase 1c).
Parent: `~/anicca/docs/superpowers/specs/2026-06-27-G1-founder-money-loop.md` §G1.2 SELF-FACILITATION.

## Goal (one sentence)
Swap `apps/x402-agents/src/server.js` from `HTTPFacilitatorClient` (CDP/x402.org-testnet) to an **in-process `x402Facilitator`** signed by `EVM_PRIVATE_KEY`, exposing exactly **one** paid endpoint `POST /social/x` at `$0.003` USDC on Base mainnet (`eip155:8453`), `payTo = X402_WALLET_ADDRESS` (= `0x810f6d61f7606deee2657d3083e150a222bc29c5`), Bazaar-discoverable, replicable by any self-funded child with its OWN key + OWN host — zero CDP / Coinbase / Railway / Dais creds.

## EARS Requirements

- **REQ-001** (ubiquitous) — The server **shall** instantiate an in-process facilitator via `new x402Facilitator()` from `@x402/core/facilitator`, register `exact` scheme via `registerExactEvmScheme(facilitator, { signer, networks: "eip155:8453" })` from `@x402/evm/exact/facilitator`, and pass `facilitator.verify` / `facilitator.settle` / `facilitator.getSupported` to the `x402ResourceServer` from `@x402/core/server`.

- **REQ-002** (ubiquitous) — The `paymentMiddleware` from `@x402/express` **shall** be configured with `payTo === process.env.X402_WALLET_ADDRESS` for every paid route.

- **REQ-003** (ubiquitous) — The settle signer **shall** be derived from `process.env.EVM_PRIVATE_KEY` via `privateKeyToAccount` (`viem/accounts`) on the **Base mainnet** chain (`base` from `viem/chains`, `chainId === 8453`). The codebase **shall not** import `baseSepolia` or any other chain.

- **REQ-004** (ubiquitous) — The server **shall** expose exactly one paid endpoint **`POST /social/x`** with `scheme:"exact"`, `price:"$0.003"`, `network:"eip155:8453"`, `payTo: X402_WALLET_ADDRESS`, `mimeType:"application/json"`. Description: `"Real-time X/Twitter data for AI agents — user/thread/search, pay per request in USDC on Base."`.

- **REQ-005** (ubiquitous) — `POST /social/x` **shall** be Bazaar-discoverable: its `extensions` field **shall** include the result of `declareDiscoveryExtension({ output: { example, schema } })` from `@x402/extensions/bazaar`, where `example` is a realistic response object and `schema` is a JSON-schema-like `{ type:"object", properties:{...} }`.

- **REQ-006** (unwanted) — IF `process.env.EVM_PRIVATE_KEY` is missing OR `process.env.X402_WALLET_ADDRESS` is missing, THEN the server **shall** log `Missing required env vars: ...` to stderr and exit with non-zero status **before** binding the listen port.

- **REQ-007** (unwanted) — IF the source under `apps/x402-agents/src/**` imports `@coinbase/x402` OR references `CDP_API_KEY` OR references the string `x402.org/facilitator` OR references any Railway-specific env (`RAILWAY_*`, `DATABASE_URL`, `OPENAI_API_KEY`) for the seller path, THEN the build / static check **shall** fail.

- **REQ-008** (ubiquitous) — `GET /health` **shall** return HTTP 200 with body `{ "status":"ok", "service":"x402-agents" }` so long as required env are present. Health **shall not** require Prisma or Postgres.

- **REQ-009** (event-driven) — WHEN a client makes `GET /metadata`, the server **shall** respond 200 with `{ routes: [{ method:"POST", path:"/social/x", scheme:"exact", price:"$0.003", network:"eip155:8453", payTo: X402_WALLET_ADDRESS, discoverable:true }] }`.

- **REQ-010** (ubiquitous) — The unit / integration tests **shall** be deterministic and **shall not** require live network access (no real RPC, no real Postgres, no real x402.org / CDP). Network-touching paths are mocked via `vitest` spies.

- **REQ-011** (ubiquitous) — `apps/x402-agents/src/server.js` **shall** boot with **only** `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` set (no `DATABASE_URL`, no `OPENAI_API_KEY`, no `CDP_API_KEY_*`, no `RAILWAY_*`). This is the replicability contract — any self-funded child must be able to boot the same server with only its OWN wallet env.

- **REQ-012** (ubiquitous) — When a buyer pays correctly, settle **shall** broadcast a USDC `Transfer` tx on Base mainnet whose `from` is the agent's EOA (derived from `EVM_PRIVATE_KEY`) and whose `to` is the buyer's relayed recipient per the x402 `exact` scheme spec; `payTo` (`X402_WALLET_ADDRESS`) receives USDC from the buyer via the standard `exact` flow. (E2E only — out of scope for unit tests; in scope for Phase 2 no-mock E2E.)

## Non-functional

- **NFR-001 dependency floor** — only the following deps may be NEW: `viem` (already), `@x402/core` (already), `@x402/evm` (already), `@x402/express` (already), `@x402/extensions` (already). The following deps **shall be removed** from the seller path: `@coinbase/x402`, `@prisma/client`, `prisma`, `openai`. (They may remain in `package.json` until a separate cleanup PR; the seller path **must not import them**.)
- **NFR-002 footprint** — `src/server.js` after the swap stays under 300 lines (was 193). All bloat (8 routers, prisma, openai client) moves out of the seller boot path.
- **NFR-003 replicable boot** — `node src/server.js` with just `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` set should bind a port in ≤ 2s on a 1-cpu/512Mi Akash container (Tier-2 child host floor).

## Out of scope (deferred to later features)

- Hosting (cloudflared / Fly / Akash) — **F2**.
- Gas seeding $1 Base ETH onto 0x810f — **F3**.
- Pre-settlement listing on x402scan + agentcash.dev — **F4**.
- 24/7 launchd heartbeat wrapping founder-loop.sh — **F5**.
- The other 7 endpoints (context-compressor, intent-router, prompt-sanitizer, emotion-detector, buddhist-counsel, focus-coach, habit-designer, decision-clarifier) — re-enabled only after `/social/x` earns first external USDC.

## Done (Phase 1a)

This file commits to: ONE in-process facilitator, ONE paid endpoint, ZERO CDP/Railway, REPLICABLE by any child with its own wallet env. Verification architecture follows in `verification-architecture.md`.
