# Behavioral Spec — founder-x402-self-facilitate (Phase 1a, lean, iteration 3, ADVERSARY-PASS LOCKED)

Feature: `founder-x402-self-facilitate`
Date: 2026-06-28 · Iteration: 3 (adversary iter-3 verdict PASS, 5/5 dims, 0 regressions; closes iter-2 NEW-1/NEW-2/NEW-3)
Builder = main agent (me). Adversary = fresh `vcsdd:vcsdd-adversary` (Phase 1c).
Parent: `~/anicca/docs/superpowers/specs/2026-06-27-G1-founder-money-loop.md` §G1.2 SELF-FACILITATION.

## Goal (one sentence + deviation note)
Swap `apps/x402-agents/src/server.js` from `HTTPFacilitatorClient` (CDP/x402.org-testnet) to an **in-process `x402Facilitator`** signed by `EVM_PRIVATE_KEY`, exposing exactly **one** paid endpoint `POST /social/x` at `$0.003` USDC on Base mainnet (`eip155:8453`), `payTo = X402_WALLET_ADDRESS` (= `0x810f6d61f7606deee2657d3083e150a222bc29c5`), Bazaar-discoverable, replicable by any self-funded child with its OWN key + OWN host — zero CDP / Coinbase / Railway / Dais creds.

★ **DEVIATION FROM CANONICAL REFERENCE** ★ — `~/anicca-work/x402/examples/typescript/servers/self-facilitation/index.ts` uses Base **Sepolia** (`eip155:84532`, `baseSepolia` from `viem/chains`). This feature uses Base **MAINNET** (`eip155:8453`, `base` from `viem/chains`). Replicators MUST flip every chain reference; importing `baseSepolia` is forbidden by REQ-003 and PROP-003 (Tier 0).

## §Done (Phase 1a) — F1 done ≠ GOAL done (explicit)

- **F1 done** = (a) the impl satisfies every REQ + every Tier-0 PROP in this spec, AND (b) the server boots locally with only `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` set, AND (c) a single self-buy on Base mainnet for `POST /social/x` reaches a successful settle on-chain (Bazaar discovery seed), AND (d) `record-earn.mjs` INV-7 REJECTS that settle as a self-payment (NOT counted as earn). ★ **§Done (c)+(d) PREREQUISITE**: a one-shot manual gas seed of ≥ $1 Base ETH onto `X402_WALLET_ADDRESS` MUST land before §Done (c) can be evaluated (a Base-mainnet settle costs gas; F1 itself does not productionize the seed). F3 productionizes this gas-seed step as an automated capability; F1 §Done (c) accepts either the F3 automation OR a manual one-shot seed. An autonomous builder loop reading the spec MUST treat §Done (c)+(d) as conjoined with that one-shot gas seed (or with F3) and SHALL NOT freeze waiting for "F3 first" — the seed is permitted under either authority. ★
- **GOAL done** (the G1 STOP rule, first real external USDC) = F1 done ∧ F2 done ∧ F3 done ∧ F4 done ∧ F5 done. F1 alone CANNOT satisfy STOP. Do not blame F1 when no money flows after F1 ships — the missing pieces are the host (F2), the gas seed (F3 productionized), the pre-settlement listing (F4), the 24/7 heartbeat (F5).

## EARS Requirements

- **REQ-001** (ubiquitous) — The server **shall** build an in-process facilitator with all of: (i) `privateKeyToAccount(EVM_PRIVATE_KEY)` from `viem/accounts`; (ii) `createWalletClient({ account, chain: base, transport: http() }).extend(publicActions)` from `viem` + `viem/chains` (where `base` is Base mainnet); (iii) `toFacilitatorEvmSigner({ address, getCode, readContract, verifyTypedData, writeContract, sendTransaction, waitForTransactionReceipt })` from `@x402/evm` to produce the `FacilitatorEvmSigner` instance; (iv) `new x402Facilitator()` from `@x402/core/facilitator`; (v) `registerExactEvmScheme(facilitator, { signer, networks: "eip155:8453" })` from `@x402/evm/exact/facilitator`; (vi) `new x402ResourceServer({ verify: facilitator.verify.bind(facilitator), settle: facilitator.settle.bind(facilitator), getSupported: async () => facilitator.getSupported() })` from `@x402/core/server`; (vii) `.register("eip155:8453", new ExactEvmServerScheme())` from `@x402/evm/exact/server` on the resource server BEFORE passing it to `paymentMiddleware`. All seven steps are MANDATORY — omitting any one of (iii), (v), or (vii) results in a server that boots but cannot settle.

- **REQ-002** (ubiquitous, anchored to singleton) — The `paymentMiddleware` from `@x402/express` **shall** be configured with **EXACTLY ONE** paid route key. That key **shall** be `"POST /social/x"` and its `payTo` **shall** be `process.env.X402_WALLET_ADDRESS`. (`Object.keys(routeTable).length === 1` is a structural invariant — see PROP-002.)

- **REQ-003** (ubiquitous) — The settle signer **shall** sign on the **Base mainnet** chain only (`base` from `viem/chains`, `chainId === 8453`, `networks: "eip155:8453"`). The codebase **shall NOT** import `baseSepolia` and **shall NOT** reference `eip155:84532` anywhere under `apps/x402-agents/src/**`.

- **REQ-004** (ubiquitous) — `POST /social/x` `accepts` **shall** be exactly: `{ scheme: "exact", price: "$0.003", network: "eip155:8453", payTo: <X402_WALLET_ADDRESS>, mimeType: "application/json", description: "Real-time X/Twitter data for AI agents — user/thread/search, pay per request in USDC on Base mainnet.", maxTimeoutSeconds: 60, extra: { asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" } }`. The `extra.asset` pin is REQ-013's USDC contract; the `maxTimeoutSeconds` is the buyer-facing settle window.

- **REQ-004b** (ubiquitous, units pin) — The price string `"$0.003"` **shall** resolve to exactly the integer string `"3000"` USDC base units (USDC has 6 decimals: $0.003 × 10⁶ = 3000). The impl **shall** assert this resolution at startup (or in a startup test) so a units-misparse cannot silently cause a $0 self-buy that seeds discovery without value.

- **REQ-005** (ubiquitous, Bazaar POST shape) — `POST /social/x` **shall** declare Bazaar discoverability via `declareDiscoveryExtension({ method: "POST", bodyType: "json", input: <realistic example body>, inputSchema: { type: "object", properties: {...}, required: [...] }, output: { example: <realistic response>, schema: { type: "object", properties: {...} } } })` from `@x402/extensions/bazaar`. Omitting `method` or `bodyType` causes the helper to fall through to the GET/query path (see `@x402/extensions/src/bazaar/resourceService.ts:93-99` — `isBodyMethod = bodyType !== undefined`), which makes Bazaar misclassify the route and prevents discovery by buyers.

- **REQ-006** (unwanted, env hardening — runs inside `createApp()`, not only at script entrypoint) — IF `process.env.EVM_PRIVATE_KEY` is missing OR empty OR does not match `/^0x[0-9a-fA-F]{64}$/`, OR IF `process.env.X402_WALLET_ADDRESS` is missing OR empty OR does not match `/^0x[0-9a-fA-F]{40}$/`, THEN: (a) the impl **shall** log a structured error to stderr naming the offending var (without echoing its value beyond a length+prefix snippet), AND (b) when invoked as a script the process **shall** exit non-zero BEFORE binding the listen port; when invoked as a library (e.g. supertest), `createApp()` **shall** throw a typed `MissingEnvError`. The check **shall** be a single exported function called from BOTH the script entrypoint AND `createApp()` — it **shall not** be gated on any `import.meta.url` branch.

- **REQ-007** (unwanted, scoped to all of `src/**`) — IF any source under `apps/x402-agents/src/**` (RECURSIVELY, ALL paths) imports `@coinbase/x402`, or references `CDP_API_KEY*`, or references the string `x402.org/facilitator`, or references any `RAILWAY_*`, `DATABASE_URL`, `OPENAI_API_KEY` env, or imports `@prisma/client`, `openai`, or `./lib/prisma`, THEN the static check **shall** fail. Paired with REQ-017 (deferred-route relocation).

- **REQ-008** (ubiquitous) — `GET /health` **shall** return HTTP 200 with body `{ "status": "ok", "service": "x402-agents", "gas_ready": <bool> }` whenever required env are present, where `gas_ready` is the boot-time NFR-004 flag (true when the agent's Base ETH balance ≥ 0.0005 ETH at boot, false otherwise). The `/health` handler **shall NOT** import or call Prisma, Postgres, OpenAI, or any other external system at request time; it **shall** be a pure constant response derived from the boot-time `gas_ready` snapshot.

- **REQ-009** (event-driven, single-source-of-truth) — WHEN a client makes `GET /metadata`, the server **shall** respond 200 with `{ routes: [ <one entry derived from the SAME constant route table that is passed to paymentMiddleware> ] }`. Each entry: `{ method, path, scheme, price, network, payTo, asset, discoverable }`. The metadata handler and the paymentMiddleware config **shall** read from the same exported constant; no literal duplication is allowed (REQ-016 below pins this).

- **REQ-010** (ubiquitous) — The unit / integration tests under `apps/x402-agents/src/__tests__/` **shall** be deterministic and **shall NOT** require live network access. RPC calls **shall** be intercepted at the transport boundary (e.g. msw/node, undici interceptor, or a fake `fetch` injected into the viem transport). Tests that mock `facilitator.settle` to return success **shall** log `[MOCKED]` so the spec's anti-fake gate (HARD 0.31) cannot be fooled.

- **REQ-011** (ubiquitous, replicability contract, no-Dais-creds floor) — `apps/x402-agents/src/server.js` **shall** boot with **only** `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` + optional `PORT` set in env — no `DATABASE_URL`, no `OPENAI_API_KEY`, no `CDP_API_KEY_*`, no `RAILWAY_*`. "Boot" is defined operationally in PROP-011 (stdout `listening on port`, GET /health → 200 within 500ms, clean stderr).

- **REQ-012** (ubiquitous, settle correctness, exact-scheme conformance) — When `facilitator.settle` runs to completion successfully, it **shall** result in a USDC `Transfer` event on Base mainnet with `to == X402_WALLET_ADDRESS` and `from == <buyer-relayed source per x402 exact-scheme spec>`, on the USDC contract pinned by REQ-013. Verifying this is the FIRST EXTERNAL earn (out of scope for unit tests — Phase 2 no-mock E2E covers it; F1 covers only the SELF-buy seed in §Done point (c)).

- **REQ-013** (ubiquitous, asset pin) — The USDC asset address on Base mainnet **shall** be exactly `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (Circle's native USDC on Base, 6 decimals). This pin appears in `accepts.extra.asset` (REQ-004) AND is enforced by static grep (PROP-013).

- **REQ-014** (unwanted, settle failure handling) — IF `facilitator.settle` throws OR returns a rejection (including `insufficient-funds`, RPC timeout, signature mismatch), THEN: (a) the HTTP response **shall** be `502` with body `{ "error": "settle_failed", "reason": <truncated message>, "code": <facilitator error code or "unknown"> }`; (b) the failure **shall** be logged to stderr with a structured tag `[x402.settle.error]` including the route, the error code, and a sanitized error message (no private-key bytes). This prevents the gas-empty case from returning a generic 500 and triggering buyer retry storms that kill demand discovery. WHEN `facilitator.verify` fails (bad signature, wrong network, etc.), the server **shall** return `402` with a freshly-issued `PaymentRequirements` object per the x402 exact-scheme spec.

- **REQ-015** (unwanted, port conflict) — IF the listen port is in use (EADDRINUSE), the server **shall** exit non-zero within 2 s and log to stderr `[x402.boot.port_conflict] port=<n>`.

- **REQ-016** (ubiquitous, single source of truth) — The route table object **shall** be defined once as a module-level constant (exported as `ROUTES`); `paymentMiddleware` and the `GET /metadata` handler **shall** both consume it. Static-PROP-016 asserts no literal-shape duplication (no second `"$0.003"` or `"eip155:8453"` literal elsewhere in the file outside the `ROUTES` constant).

- **REQ-017** (ubiquitous, deferred-route relocation) — The 8 deferred endpoint route files (`buddhistCounsel.js`, `contextCompressor.js`, `decisionClarifier.js`, `emotionDetector.js`, `focusCoach.js`, `habitDesigner.js`, `intentRouter.js`, `promptSanitizer.js`) under `apps/x402-agents/src/routes/` AND the helper `apps/x402-agents/src/lib/prisma.js` **shall** be MOVED out of `apps/x402-agents/src/` before F1 lands. Acceptable targets: (a) `apps/x402-agents-deferred/src/...` (separate package, deps remain), or (b) git-deletion (history-recoverable). This makes REQ-007's recursive scan honest.

## Non-functional

- **NFR-001 dep floor** — only the following deps may be imported by `src/server.js`: `viem`, `@x402/core`, `@x402/evm`, `@x402/express`, `@x402/extensions`, `express`, `cors`, `express-rate-limit`. The following **shall not** appear under `src/**`: `@coinbase/x402`, `@prisma/client`, `prisma`, `openai`. (Removal from `package.json` may be a separate cleanup; REQ-007 enforces the import constraint regardless.)
- **NFR-002 footprint** — `src/server.js` after the swap stays under 300 lines.
- **NFR-003 replicable boot timing** — `node src/server.js` with just `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS` set should bind a port in ≤ 2 s on a 1-cpu/512Mi container.
- **NFR-004 gas-readiness** (replicability honest about gas) — On boot, after env validation but BEFORE accepting buyer traffic, the impl **shall** read the agent's Base ETH balance via the configured viem walletClient. IF balance < `0.0005 ETH`, the impl **shall** log a structured warning `[x402.boot.gas_low] balance=<wei> address=<addr> floor=500000000000000` to stderr. The impl **shall NOT** refuse to boot (gas can arrive after boot via F3 seed), but it **shall** mark a `gas_ready=false` flag exposed at `/health` so a heartbeat / monitor can detect "booted but cannot settle". Tier-2 children inherit this exact behavior — replicability contract = boot + signal-gas-status, not boot + lie.

## Out of scope (deferred to later features)

- Hosting (cloudflared / Fly / Akash) — **F2**.
- Gas seeding $1 Base ETH onto 0x810f — **F3** (NFR-004's gas-balance check ENABLES the heartbeat to know when F3 is satisfied).
- Pre-settlement listing on x402scan + agentcash.dev — **F4**.
- 24/7 launchd heartbeat wrapping founder-loop.sh — **F5**.
- The 8 other endpoints (re-introduced under a separate package in F1, re-enabled as paid routes only after `/social/x` earns first external USDC) — **F-LATER**.

## Anti-fake gate (cross-link, HARD 0.31 + INV-7 + adversary iter-1 finding)

- The §Done point (c) self-buy on Base mainnet is real on-chain. INV-7 in `record-earn.mjs` (parent G1 spec) MUST reject it as self-payment. No `console.log("settled!")` or analogous fakes — the only acceptable evidence of a settle in F1 is the on-chain tx hash on BaseScan + `record-earn` REJECTING the row.
- Tests that mock `facilitator.settle` MUST log `[MOCKED]`. A test that asserts a settle "succeeded" without either (i) a real tx hash, or (ii) `[MOCKED]` in stderr, is fail-closed by the adversary on Phase 3.

## Replicability assertion (bridge to Tier-2 children, honest version)

REQ-007 + REQ-011 + REQ-017 + NFR-004 together: a Tier-2 child clones the same `src/server.js`, sets ONLY its OWN `EVM_PRIVATE_KEY` + `X402_WALLET_ADDRESS`, boots on any of H1–H5, AND signals `gas_ready=false` until F3 (or its child equivalent) funds it. No silent "booted but earning nothing" claim. This is what makes F1 a teachable skill (HARD 0.40 GLVS step 4).

## Done (Phase 1a, iteration 3 — adversary PASS)

iter-3 surgical close-out: REQ-008 body literal now includes `gas_ready` cross-ref to NFR-004; §Done (c)+(d) carries an explicit "F3-or-manual one-shot seed" prerequisite clause so an autonomous builder loop will not freeze; REQ-002 cross-ref corrected to PROP-002. All three iter-2 findings CLOSED, zero iter-1 regressions, 5/5 dimensions PASS. Verification architecture (iteration 2) is unchanged and re-validated against this spec. The spec is now locked for Phase 2a (RED).
