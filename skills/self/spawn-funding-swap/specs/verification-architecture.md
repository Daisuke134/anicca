# spawn-funding-swap — verification-architecture.md (sprint-2: real-clients)

Scoped to sprint-2 (REQ-013..REQ-018, `lib/real-clients/**` + `lib/pure/cosmos-address.mjs`). Sprint-1's
own verification architecture (driver.mjs + pure core vs fakes) is unchanged and already GREEN.

## Purity Boundary Map

- **Pure Core** (new this sprint): `lib/pure/cosmos-address.mjs` — `bech32Encode`, `convertBits8to5`,
  `deriveCosmosAddress`. Deterministic, no I/O. Subject to PROP-017's existing structural scan (no
  `node:fs`/`node:child_process`/`node:http(s)`/`fetch` imports permitted).
- **Effectful Shell** (new this sprint): `lib/real-clients/chain-reader.mjs` (Base JSON-RPC over `fetch`
  + `akash` CLI over `execFile`), `lib/real-clients/price-oracle.mjs` (CoinGecko over `fetch`),
  `lib/real-clients/skip-api-client.mjs` (Skip API over `fetch`), `lib/real-clients/relay-poller.mjs`
  (Base JSON-RPC over `fetch` + bounded `setTimeout` sleeps), `lib/real-clients/base-signer.mjs` (Skip
  API over `fetch`, Base JSON-RPC over `fetch`, real tx signing/broadcast via `viem`'s wallet client, and
  ERC-20 `allowance`/`approve` calldata via `viem`'s `encodeFunctionData`). Every transport boundary in
  every one of these five modules is constructor-injectable (`fetchImpl`, `execFileImpl`,
  `walletClientFactory`, `publicClientFactory`) so unit tests never touch a real network/process/signer.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-030 | `bech32Encode`/`deriveCosmosAddress` match a known-answer vector cross-checked against an independent reference implementation | 1 | true | node:test (unit, known-answer) |
| PROP-031 | `deriveCosmosAddress` throws on a non-20-byte hash or empty hrp | 0 | true | node:test |
| PROP-032 | `createRealChainReader().getAkashBalance` parses a mocked `akash query bank balances -o json` stdout into the exact `uakt` bigint (or `0n` if absent), never a Number/string | 1 | true | node:test (mocked `execFileImpl`) |
| PROP-033 | `createRealChainReader().getAkashBalance` throws when `AKASH_NODE`/`AKASH_CHAIN_ID` are unset | 0 | true | node:test |
| PROP-034 | `createRealChainReader().getBaseUsdc`/`getBaseGas` return the RAW (never `/1e6`-scaled) bigint from a mocked `eth_call`/`eth_getBalance` response | 1 | true | node:test (mocked `fetchImpl`) |
| PROP-035 | `createRealChainReader().getBaseTxStatusByNonce` returns `"confirmed"` iff the mocked mined-tx-count is strictly greater than the queried nonce, else `"not-found"` | 1 | true | node:test (property: several count/nonce pairs) |
| PROP-036 | `createRealPriceOracle().getAktUsdPrice` resolves only for a finite positive `number`, throws for every other response shape (non-2xx, missing field, `<=0`, non-numeric) | 1 | true | node:test |
| PROP-037 | `createRealSkipApiClient().getRoute` always sends `amount_in`/`source_asset_chain_id`/`dest_asset_chain_id` as JSON strings (never JS numbers) regardless of the input type it received | 1 | true | node:test (mocked `fetchImpl`, request-body assertion) |
| PROP-038 | `createRealSkipApiClient().getRoute` throws on a non-2xx response or a body carrying Skip's own `code` field | 0 | true | node:test |
| PROP-039 | `createRealRelayPoller().waitForConfirmation` with a numeric `chainId` returns `"confirmed"`/`"reverted"`/`"pending"` correctly for a mocked receipt sequence (immediate success, immediate revert, never-lands-before-timeout) | 1 | true | node:test (mocked `fetchImpl`, small injected `pollIntervalMs`) |
| PROP-040 | `createRealRelayPoller().waitForConfirmation` with a string `chainId` returns `"confirmed"` only once the full (injected, test-scale) settle window elapses within `timeoutMs`, else `"pending"` | 1 | true | node:test (injected `relaySettleWaitMs`) |
| PROP-041 | `createRealBaseSigner().getAddress()`/`getNextNonce(amount)` throw when `ANICCA_HOME` is unset (fail-closed identity gate) | 0 | true | node:test |
| PROP-042 | `createRealBaseSigner().getAddress()` returns the address `viem`'s own `privateKeyToAccount` derives from the SAME resolved key (known-answer, injected fixture wallet.json) | 1 | true | node:test |
| PROP-043 | `getNextNonce(amount)`'s approval check-and-send (when the mocked allowance is `0`) sends the approve tx at a nonce STRICTLY LESS than the nonce `getNextNonce(amount)` itself returns, approving EXACTLY `amount` (decoded from the mocked `approve()` calldata, not merely "some tx was sent") — the single most important money-safety property this sprint's design depends on (see base-signer.mjs's own header comment) | 2 | true | node:test (mocked `walletClientFactory` spy capturing `sendTransaction`'s `nonce`/`data` args + mocked `eth_getTransactionCount` sequence, `viem` `decodeFunctionData` on the captured `data`) |
| PROP-044 | `getNextNonce(amount)` sends NO approve tx when the mocked on-chain allowance ALREADY EXACTLY equals `amount` (impl review iter2: tightened from the iter1 `>= APPROVAL_CAP_BASE_UNITS` check, which permitted a standing-excess allowance to silently pass) | 1 | true | node:test |
| PROP-044b | (impl review iter2, FIND-001 CRITICAL fix) `getNextNonce(amount)`'s approve-race guard: a prior non-zero on-chain allowance that does NOT already equal `amount` is reset to `0` FIRST, then set to `amount` — two sequential approve txs at two strictly-sequential nonces, never a single direct overwrite of a non-matching non-zero allowance | 2 | true | node:test (mocked `walletClientFactory` spy, two-entry `nonceSequence`, `decodeFunctionData` on both captured `data` args) |
| PROP-052 | (impl review iter2, FIND-001 CRITICAL fix — THE central property this iteration exists to prove) `signAndBroadcast` REFUSES to broadcast when the ACTUAL, CURRENT on-chain allowance for `evm_tx.to` (queried fresh via RPC, never inferred from Skip's HTTP response) diverges from `amount` in EITHER direction — insufficient (would revert on-chain) OR IN EXCESS (a standing/stale higher allowance, the exact iter2 attack: honest-looking `required_erc20_approvals[0].amount` metadata + a pre-existing higher real allowance + attacker-controlled calldata). Reproduces the iteration-2 adversary's exact CRITICAL finding (a pre-existing $100 `APPROVAL_CAP_BASE_UNITS`-style allowance + metadata reporting `amount` exactly) and proves it is now refused with zero broadcasts, alongside a regression test proving the honest exactly-`amount`-matching path still signs | 2 | true | node:test (spy assertion: `walletClientFactory.sent.length === 0` on the excess-allowance attack test, `=== 1` on the honest-match regression test) |
| PROP-045 | `signAndBroadcast` throws BEFORE any network call when `sourceAddress` or `destinationAkashAddress` don't match the expected fixed values | 0 | true | node:test |
| PROP-046 | `signAndBroadcast` throws when the re-fetched route's destination fields don't match `uakt`/`akashnet-2`, or when the msgs response contains zero/multiple `evm_tx` entries, or when `evm_tx.signer_address` mismatches | 0 | true | node:test |
| PROP-047 | `signAndBroadcast` throws (never signs) if the allowance check at sign time is still insufficient, rather than attempting a second, nonce-colliding approve | 2 | true | node:test |
| PROP-048 | `signAndBroadcast`'s broadcast call always uses `nonce` EXACTLY as passed in (spy assertion on the injected `walletClientFactory`) | 2 | true | node:test |
| PROP-049 | (structural, this sprint's own Test-Money-Safety extension) no file under `lib/real-clients/__tests__/**` references a live Skip/CoinGecko/`mainnet.base.org`/Akash RPC endpoint literal outside a documented comment, and no test constructs a bare `createRealXxx()` with no injected `fetchImpl`/`execFileImpl` transport seam in its argument object | 0 | true | node:test (static source scan, string-literal-aware comment stripper + balanced-paren call-argument extraction) |
| PROP-050 | (CRITICAL, FIND-001/FIND-002 fix, impl review iter1; tightened impl review iter2, FIND-001 CRITICAL fix) `signAndBroadcast` decodes and bound-checks the ACTUAL `evm_tx` Skip returned against the driver-supplied intent BEFORE ever signing: (a) `evm_tx.data` never decodes as a bare ERC-20 `transfer`/`transferFrom` selector; (b) `evm_tx.to` exactly equals the sole `required_erc20_approvals[0].spender` and is never the USDC contract itself; (c) `required_erc20_approvals[0].amount` (Skip's self-reported metadata) exactly equals the driver-supplied `amount` (bigint `===`) and is `<= MAX_SWAP_BASE_UNITS` (`SWAP_MAX_USD`'s base-unit equivalent, $20 — iter2: no longer the looser $100 `APPROVAL_CAP_BASE_UNITS`); (d) the REAL on-chain allowance for that spender, queried fresh via RPC, is EXACTLY `amount` (see PROP-052); (e) `evm_tx.value` is exactly `0n`. Refuses (throws, never broadcasts) on any violation | 2 | true | node:test (spy assertion: `walletClientFactory.sent.length === 0` on every refusal path, `=== 1` on the honest-tx path) |
| PROP-051 | (FIND-003 documented-assumption test, unchanged by the iter2 fix) `getNextNonce(amount)`'s approval-probe spender diverging from `signAndBroadcast`'s real-route spender fails CLOSED — the on-chain allowance check (never a second, nonce-colliding approve) refuses to sign, and PROP-050's own self-consistency gate additionally guarantees no broadcast happens against a mismatched spender. Also proves the probe-settled allowance is EXACTLY the real swap's `amount`, not a flat cap | 1 | true | node:test (route-fetch routed by `amount_in` to distinguish probe vs. real spender; `decodeFunctionData` on the captured approve calldata) |

## Verification Strategy

- **Tier 0** (no formal proof needed): fail-closed gates on missing env/malformed input (PROP-031,
  PROP-033, PROP-038, PROP-041, PROP-045, PROP-046, PROP-049) — simple, deterministic branch coverage.
- **Tier 1** (property/example-based tests, `node:test`): parsing/serialization correctness for each
  client's happy-path and malformed-response handling (PROP-030, PROP-032, PROP-034, PROP-035, PROP-036,
  PROP-037, PROP-039, PROP-040, PROP-042, PROP-044) — plus PROP-051 (impl review iter1: the documented
  probe-vs-real spender assumption fails closed, never fund-unsafe).
- **Tier 2** (the money-safety-critical properties this sprint exists to get right): the nonce-ordering
  guarantee between an internal ERC-20 approval and the tracked leg-0 nonce (PROP-043, PROP-044b,
  PROP-047, PROP-048) — verified via spy-based assertions on the exact sequence and arguments of every
  mocked `sendTransaction`/`eth_getTransactionCount` call, not merely "did it not throw" — AND (impl
  review iter1 addition, tightened impl review iter2) PROP-050/PROP-052: that the ACTUAL signed
  transaction content (destination contract, encoded USDC amount, native value) AND the ACTUAL, CURRENT
  on-chain ERC-20 allowance match the driver's intent exactly, bounded to `amount` (never a standing
  higher cap), and allowlisted, never taken on faith from Skip's HTTP response. These are the properties
  an adversary review (Phase 3, per this repo's `dev-workflow.md`) should scrutinize hardest — PROP-052 in
  particular is the direct closure of this iteration's CRITICAL finding (FIND-001, iter2).
- **Tier 3** (not attempted this sprint): no formal/symbolic proof of the Skip API's own route-selection
  or smart-relay execution guarantees — those are a third party's infrastructure, out of this feature's
  verification boundary; this feature's own safety net for that is REQ-007's independent on-chain
  settlement re-verification (already Tier-1-verified in sprint-1's `settlement.test.mjs`), which every
  real-client failure mode in this sprint ultimately routes through before any success is ever declared.

## Live-verification note (distinct from automated tests)

Several literal values in this sprint's implementation (Skip API request/response field names, the
`address_list` bech32-format requirement, the `allow_multi_tx`/chain-id-string requirements, CoinGecko's
response shape) were confirmed against the REAL, LIVE Skip API and CoinGecko endpoints during this
sprint's design phase (2026-07-11, via `curl`) — not assumed from training data. This is documented
provenance for the adversary review, not a substitute for the mocked-transport unit tests above (which
remain the actual CI-enforced regression gate, per NFR-6).
