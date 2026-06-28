# Verification Architecture — founder-x402-self-facilitate (Phase 1b, lean, iteration 2)

Feature: `founder-x402-self-facilitate` · Mode: lean · Date: 2026-06-28 · Iteration: 2
Pairs with `behavioral-spec.md` (iteration 2). Revises iteration-1 per adversary FAIL verdict (25 findings).

## Purity boundary map (honest, no PURE-ish leaks)

| Component | Side | Reason |
|---|---|---|
| `ROUTES` constant (the single route table) | **PURE data** | Plain exported JS object; deterministic; testable without env. |
| `declareDiscoveryExtension({ method, bodyType, input, inputSchema, output })` result | **PURE data** | Returns a plain config object. |
| Env-validate function (REQ-006) | **PURE** | Pure over `process.env` snapshot; returns `MissingEnvError` or void. |
| `getMetadata()` (REQ-009) | **PURE** | Derives the metadata payload from `ROUTES` constant only. |
| `GET /health` handler (post-swap) | **PURE** | Returns constant `{status:"ok",service:"x402-agents", gas_ready: <bool>}`. No Prisma, no Postgres, no network — except the boot-once NFR-004 gas-balance read which is cached at module-load. |
| `privateKeyToAccount(EVM_PRIVATE_KEY)` | **IMPURE** | Reads env. |
| `createWalletClient(...).extend(publicActions)` | **IMPURE** | Holds network transport. |
| `toFacilitatorEvmSigner(...)` over the walletClient | **IMPURE** (proxies into the impure walletClient) | Each method calls live RPC. |
| `new x402Facilitator()` + `registerExactEvmScheme` + `x402ResourceServer.register(...)` | **IMPURE** | Stateful facilitator + signer references. |
| NFR-004 gas balance read (once at boot) | **IMPURE** | One RPC call. Result cached. |
| `app.listen(port, cb)` | **IMPURE** | Binds a port. |

**Purity test rule** — PURE pieces are unit-tested as plain functions with no env, no spies, no port. IMPURE pieces are integration-tested with supertest + a viem transport stubbed to a fixed-fake URL `http://127.0.0.1:1` so any unmocked network attempt throws a deterministic error.

**Implementation requirement (drops PROP-002/004/005 spy fragility)**: the route table MUST be an exported module-level constant `export const ROUTES = { ... };`. `paymentMiddleware`, `getMetadata`, and tests all consume this same constant. Tests assert against the imported constant directly — no `vi.mock` of `@x402/express` is needed.

## Proof obligations (PROP-XXX ↔ REQ-XXX)

Tier 0 = required to land (adversary blocks PASS otherwise). Tier 1 = strong-pass. Tier 2 = nice-to-have.

| ID | Covers | Tier | Required? | Verification (concrete, falsifiable) |
|---|---|---|---|---|
| **PROP-001a** | REQ-001 (i)+(ii) | 0 | yes | `grep -nE "privateKeyToAccount\(process\.env\.EVM_PRIVATE_KEY" apps/x402-agents/src/server.js` = EXACTLY 1 match AND `grep -nE "createWalletClient\(.*chain:\s*base" apps/x402-agents/src/server.js` = EXACTLY 1 match. |
| **PROP-001b** | REQ-001 (iii) | 0 | yes | `grep -nE "toFacilitatorEvmSigner\(" apps/x402-agents/src/server.js` = EXACTLY 1 match (not in a comment: line must not start with `//` or `*`). |
| **PROP-001c** | REQ-001 (iv)+(v) | 0 | yes | `grep -nE "new\s+x402Facilitator\(\)" apps/x402-agents/src/server.js` = EXACTLY 1 match AND `grep -nE "registerExactEvmScheme\(facilitator," apps/x402-agents/src/server.js` = EXACTLY 1 match. |
| **PROP-001d** | REQ-001 (vi)+(vii) | 0 | yes | `grep -nE "new\s+x402ResourceServer\(" apps/x402-agents/src/server.js` = EXACTLY 1 AND `grep -nE "\.register\(\"eip155:8453\",\s*new\s+ExactEvmServerScheme\(\)\)" apps/x402-agents/src/server.js` = EXACTLY 1. |
| **PROP-002** | REQ-002 (singleton) | 0 | yes | `import { ROUTES } from './server.js'; assert Object.keys(ROUTES).length === 1; assert Object.keys(ROUTES)[0] === "POST /social/x"; assert ROUTES["POST /social/x"].accepts.payTo === process.env.X402_WALLET_ADDRESS;` — pure unit test on the exported constant. |
| **PROP-003** | REQ-003 (mainnet only) | 0 | yes | `grep -rnE "baseSepolia\|eip155:84532" apps/x402-agents/src/` = 0 matches AND `grep -nE "import\s+\{[^}]*\bbase\b[^}]*\}\s+from\s+['\"]viem/chains['\"]" apps/x402-agents/src/server.js` = EXACTLY 1 match. |
| **PROP-004** | REQ-004 (accepts shape) | 0 | yes | Unit on `ROUTES["POST /social/x"].accepts`: `scheme==="exact"` ∧ `price==="$0.003"` ∧ `network==="eip155:8453"` ∧ `payTo===process.env.X402_WALLET_ADDRESS` ∧ `mimeType==="application/json"` ∧ `maxTimeoutSeconds===60` ∧ `extra.asset==="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"`. |
| **PROP-004b** | REQ-004b (units pin) | 0 | yes | Unit (or boot assertion): the resolved settle amount for `$0.003` on a USDC-6-decimals asset === the string `"3000"`. Implementation: parse the price via the x402 SDK's price resolver and assert the resulting `maxAmountRequired` (or equivalent) === `"3000"`. |
| **PROP-005** | REQ-005 (Bazaar POST shape — SDK-aligned, iter-2) | 0 | yes | Unit on `ROUTES["POST /social/x"].extensions.bazaar.info`: `info.input.type === "http"`, `info.input.method === "POST"`, `info.input.bodyType === "json"`, `info.input.body` is a non-empty object (the raw example), `info.output.type === "json"` AND `info.output.example` is non-empty. Plus assert `extensions.bazaar.schema.properties.input.properties.body` exists (the SDK injects the inputSchema there). No decorative top-level keys outside the `{bazaar:...}` returned by the SDK. |
| **PROP-006** | REQ-006 (env validator) | 0 | yes | Unit on the exported `validateEnv(env)` function: returns `MissingEnvError` for each of: missing key, empty string, malformed (key not matching `/^0x[0-9a-fA-F]{64}$/`, addr not matching `/^0x[0-9a-fA-F]{40}$/`). Integration: spawn `node src/server.js` with each broken case → exits non-zero within 2s; stderr contains the structured tag `[x402.boot.missing_env]`. |
| **PROP-006a** | REQ-006 (createApp throws) | 0 | yes | Integration: call `createApp()` from a test with broken env → throws `MissingEnvError` (a typed error class). |
| **PROP-007** | REQ-007 + REQ-017 (no leaky imports anywhere under src/) | 0 | yes | `grep -rnE "@coinbase/x402\|CDP_API_KEY\|x402\.org/facilitator\|RAILWAY_\|DATABASE_URL\|OPENAI_API_KEY\|@prisma/client\|from\s+['\"]openai['\"]\|require\(['\"]openai['\"]\)\|from\s+['\"]\./lib/prisma['\"]" apps/x402-agents/src/` returns 0 matches. (Recursive over ALL of src/, not just server.js.) Pair with PROP-017. |
| **PROP-008** | REQ-008 (/health pure) | 0 | yes | Integration: supertest `GET /health` → 200 with body `{status:"ok",service:"x402-agents",gas_ready:<bool>}` runs with `DATABASE_URL` unset and Prisma fully removed. |
| **PROP-008b** | REQ-008 (prisma not imported) | 0 | yes | `grep -nE "prisma\|@prisma/client\|from\s+['\"]\./lib/prisma['\"]" apps/x402-agents/src/server.js` = 0 matches. |
| **PROP-009** | REQ-009 (metadata shape) | 1 | no | Integration: supertest `GET /metadata` → 200, body has `routes[0].method==="POST"` ∧ `routes[0].path==="/social/x"` ∧ all 8 fields present (method, path, scheme, price, network, payTo, asset, discoverable). |
| **PROP-010** | REQ-010 (test determinism) | 1 | no | Test setup hooks a Node `fetch` interceptor (e.g. `undici.setGlobalDispatcher(new MockAgent())` OR `msw/node`) — any unmocked outbound HTTPS aborts with `NoMockHandlerError`. `npm test` runs with `--reporter=verbose`; assertion: zero `NoMockHandlerError` thrown means tests were properly mocked; zero real RPC calls. (Replaces the broken http.request spy.) |
| **PROP-011** | REQ-011 (replicable boot — iter-2: explicit RPC override for determinism) | 0 | yes | Integration: spawn `node src/server.js` with ONLY env: `EVM_PRIVATE_KEY=<32-byte hex test key>` + `X402_WALLET_ADDRESS=<40-hex test addr>` + `PORT=<random unused>` + `X402_RPC_URL=http://127.0.0.1:1` (RPC override to keep the gas-probe deterministic; no live Base mainnet RPC call during tests, per REQ-010). Within 2 s: child stdout contains `listening on port <PORT>`. The gas probe is allowed to fail against the fake RPC → expected stderr tag `[x402.boot.gas_probe_error]` (the fail path now logs instead of swallowing silently — iter-2 hardening). No stack traces beyond that. |
| **PROP-012** | REQ-012 (real settle, OOS unit) | 2 | no | OUT-OF-SCOPE for unit tests. F1 §Done point (c) self-buy E2E covers it on Base mainnet; first-external is F2+F3+F4+F5. |
| **PROP-013** | REQ-013 (USDC asset pin) | 0 | yes | `grep -nE "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" apps/x402-agents/src/server.js` = EXACTLY 1 match AND it appears inside the `extra.asset` field of `ROUTES["POST /social/x"].accepts`. |
| **PROP-014** | REQ-014 (settle fail handler — SDK-aligned, iter-2) | 0 | yes | Unit: import the exported `wrapSettle(fn)` from `server.js`; call `wrapSettle(() => { throw {code:'insufficient_funds', message:'low gas'} })()` and assert (a) the call rejects with the original error; (b) `console.error` was called with a string matching `/^\[x402\.settle\.error\] insufficient_funds/`. Verify response is the SDK's own 402+`{error:"Settlement failed",details}` is OUT OF SCOPE for unit (the SDK behavior is settled in @x402/express 2.4.0 source verification, not retested here). The log + rethrow contract IS the impl invariant. |
| **PROP-015** | REQ-015 (port conflict) | 1 | no | Integration: bind a dummy listener on `PORT`, spawn `node src/server.js` with same `PORT` → exits non-zero within 2s; stderr contains `[x402.boot.port_conflict] port=<PORT>`. |
| **PROP-016** | REQ-016 (single source of truth) | 0 | yes | Static: `grep -cE "\"\\\$0\\.003\"" apps/x402-agents/src/server.js` = EXACTLY 1 AND `grep -cE "\"eip155:8453\"" apps/x402-agents/src/server.js` = EXACTLY 1. Both literals live inside the `ROUTES` constant only. Plus unit: `getMetadata().routes[0].price === ROUTES["POST /social/x"].accepts.price` and same for network/payTo/asset/discoverable. |
| **PROP-017** | REQ-017 (deferred routes moved) | 0 | yes | After the swap: `ls apps/x402-agents/src/routes/ 2>/dev/null \| grep -E "^(buddhistCounsel\|contextCompressor\|decisionClarifier\|emotionDetector\|focusCoach\|habitDesigner\|intentRouter\|promptSanitizer)\.js$"` = 0 matches AND `ls apps/x402-agents/src/lib/prisma.js 2>/dev/null` = no file. (i.e. the files are not present under src/; they live under `apps/x402-agents-deferred/` if retained.) |
| **PROP-NFR-004** | NFR-004 (gas-readiness signal) | 1 | no | Integration: stub the walletClient's `getBalance` to return `BigInt(0)` → boot still succeeds AND stderr contains `[x402.boot.gas_low]` AND `GET /health` returns `gas_ready: false`. Stub to return `BigInt(1e18)` → stderr does NOT contain `[x402.boot.gas_low]` AND `gas_ready: true`. |

## Tiering rationale (post-iter-1 promotion)

- Tier 0 (PROP-001a/b/c/d, 002, 003 (promoted), 004, 004b, 005, 006 (promoted), 006a, 007, 008, 008b, 011, 013, 014, 016, 017) = the things that, if violated, mean either (a) the swap didn't happen, (b) money lands on the wrong chain / wrong token, (c) buyers can't discover, (d) tests pass spuriously, or (e) gas-empty kills demand. ALL must pass for the adversary gate (Phase 1c) — even in lean mode.
- Tier 1 (PROP-009, 010, 015, NFR-004) = quality reinforcements; failure means a smell, not a wrong impl.
- Tier 2 (PROP-012) = real on-chain proof; covered by F1 §Done (c) E2E + F2+F3+F4+F5 conjunctively.

## Anti-fake gate (HARD 0.31 + INV-7, strengthened)

- §Done (c) self-buy is the only F1-scope on-chain settle. INV-7 in parent `record-earn.mjs` rejects it as self-payment — the F1 done condition explicitly REQUIRES that rejection to fire.
- `[MOCKED]` tag required on any test that stubs `facilitator.settle` or `facilitator.verify`.
- "settle succeeded" claim with no tx hash + no `[MOCKED]` tag = automatic Phase 3 adversary FAIL.

## Replicability assertion (Tier-2 bridge, gas-honest)

PROP-007 + PROP-011 + PROP-017 + NFR-004 / PROP-NFR-004: a Tier-2 child clones server.js, sets ONLY its OWN env, boots on any of H1–H5, and SIGNALS `gas_ready=false` via `/health` until F3 (or its child-equivalent) funds it. Replicable boot ≠ replicable earn — that gap is closed by F3 + the heartbeat's gas-readiness watch. Adversary iter-1's impl-correctness #2 finding is closed by making this gap explicit + observable.

## Done (Phase 1b, iteration 2)

This iteration: 21 proof obligations (was 12); 17 Tier-0 required (was 7); each iter-1 grep regex hardened; spy fragility eliminated by exporting `ROUTES`; gas-readiness signal added; deferred-route relocation made a first-class invariant. Ready for iteration-2 adversary spec-review.
