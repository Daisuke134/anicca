# spawn-funding-swap — behavioral-spec.md (sprint-2: real-clients)

Sprint-1 (REQ-001..REQ-012, driver.mjs + pure/**) already shipped GREEN against
`lib/__tests__/fakes/fake-clients.mjs` (commits `92101880`..`b253315d`). This document is scoped to
**sprint-2 only**: the 5 real, network/RPC/signing-touching client modules under
`lib/real-clients/**` that `bin/spawn-funding-swap.mjs`'s production `buildDeps()` dynamically imports
(REQ-013..REQ-018). Every REQ below is additive to, never a replacement of, sprint-1's REQ-001..REQ-012
(still governed by `lib/driver.mjs`'s own header comment).

Money-safety context: this feature moves real Base-chain USDC (via a signed Base transaction) toward a
cross-chain swap into AKT on Akash. Sprint-2's real-clients are the ONLY place in this feature that ever
touch real money/network — the pure core and driver were already hardened against fakes; sprint-2 must
not weaken any of REQ-001..REQ-012's guarantees, only implement the effectful edges those REQs assume.

## Purity boundary analysis (sprint-2 additions)

- **New pure core addition**: `lib/pure/cosmos-address.mjs` (`bech32Encode`, `convertBits8to5`,
  `deriveCosmosAddress`) — deterministic bech32 encoding of a 20-byte pubkey-hash, no I/O. Subject to the
  SAME PROP-017 import-boundary scan as sprint-1's pure core (no `node:fs`/`node:child_process`/
  `node:http(s)`/`fetch`).
- **New effectful shell**: `lib/real-clients/{chain-reader,price-oracle,skip-api-client,base-signer,
  relay-poller}.mjs`. Every one of these performs real I/O (Base JSON-RPC over `fetch`, the `akash` CLI
  via `execFile`, Skip API over `fetch`, Base tx signing/broadcast via `viem`) and is therefore NEVER
  imported by a file under `lib/__tests__/` (PROP-021's existing structural scan, unmodified this
  sprint) — each module's own unit tests live under `lib/real-clients/__tests__/`, a directory PROP-021's
  scan (scoped to `lib/__tests__/`'s own subtree) does not traverse.

## Requirements

### REQ-013: Cosmos-SDK address derivation from the Base signing key
**EARS**: WHEN base-signer needs a bech32 address for a Cosmos-SDK IBC-hop chain (noble-1, osmosis-1)
THE SYSTEM SHALL derive it deterministically from the SAME secp256k1 private key already resolved for
Base signing, via `compressedPubkey -> RIPEMD160(SHA256(compressedPubkey)) -> bech32(hrp)`.
**Edge Cases**:
- A 0-byte or >20-byte hash input to `deriveCosmosAddress`: THE SYSTEM SHALL throw (never silently
  truncate/pad to produce a malformed address).
- An empty `hrp`: THE SYSTEM SHALL throw.
**Acceptance Criteria**:
- `deriveCosmosAddress(pubkeyHash20, "noble")` on a known-answer 20-byte hash produces the EXACT bech32
  string independently verified against a reference bech32 implementation (cross-checked against a
  Python BIP-173 reference implementation during this sprint's design phase; both agree byte-for-byte).
- The derived noble-1/osmosis-1 addresses, when submitted to Skip API's live `/v2/fungible/msgs`
  `address_list`, are accepted as well-formed bech32 (verified live 2026-07-11 — not rejected with the
  "not bech32 valid" error a malformed string produces).

### REQ-014: Real chain-reader (Akash + Base balance/nonce reads)
**EARS**: WHEN driver.mjs calls `chainReader.getAkashBalance(address)` / `getBaseUsdc(address)` /
`getBaseGas(address)` / `getBaseTxStatusByNonce(address, nonce)` THE SYSTEM SHALL query the real Akash
chain (via the `akash` CLI, matching `skills/self/spawn/lib/spawn-orchestrator.mjs:228-241`'s own
`query bank balances -o json` shape) and the real Base chain (via `eth_call`/`eth_getBalance`/
`eth_getTransactionCount` JSON-RPC, matching `skills/_shared/lib/usdc.mjs`'s fetchImpl-injectable
transport shape) and return the EXACT on-chain raw bigint (uakt / wei / raw-6-decimal-USDC respectively;
`getBaseUsdc` NEVER returns `usdc.mjs`'s own `/1e6`-scaled Number).
**Edge Cases**:
- `AKASH_NODE`/`AKASH_CHAIN_ID` unset in env: THE SYSTEM SHALL throw rather than query the `akash` CLI's
  own ambient default node (which could silently be the wrong network).
- No `uakt` entry in the balances response: THE SYSTEM SHALL return `0n` (a genuinely-zero balance, not
  an error).
- A malformed/non-2xx RPC response for any Base read: THE SYSTEM SHALL throw (fail-closed; driver.mjs's
  REQ-001 call site is wrapped in try/catch expecting exactly this).
- `getBaseTxStatusByNonce(address, nonce)`: `eth_getTransactionCount(address, "latest")` (the count of
  MINED txs, == the next fresh nonce) strictly greater than `nonce` means that nonce has already landed
  on-chain → `"confirmed"`; otherwise `"not-found"`.
**Acceptance Criteria**:
- `getAkashBalance`/`getBaseUsdc`/`getBaseGas` return `bigint`, never `Number` or `string`.
- `getBaseTxStatusByNonce` returns only the two literal strings `"confirmed"` / `"not-found"` (matches
  `createFakeChainReader`'s own contract exactly).

### REQ-015: Real price oracle (AKT/USD spot price)
**EARS**: WHEN driver.mjs calls `priceOracle.getAktUsdPrice()` THE SYSTEM SHALL fetch a live AKT/USD spot
price from CoinGecko's free `simple/price` endpoint (verified live 2026-07-11:
`GET .../simple/price?ids=akash-network&vs_currencies=usd` → `{"akash-network":{"usd":0.606867}}`) and
return it as a finite, positive `number`.
**Edge Cases**:
- Non-2xx HTTP response: THE SYSTEM SHALL throw.
- Missing/non-numeric/non-finite/`<=0` `akash-network.usd` field: THE SYSTEM SHALL throw rather than
  return an invalid price for driver.mjs's REQ-011 validation to (redundantly) catch — this client never
  hands driver.mjs a value driver.mjs would itself have to reject.
**Acceptance Criteria**:
- Every RESOLVED value satisfies `typeof v === "number" && Number.isFinite(v) && v > 0`.
- Every failure mode above THROWS (never resolves to `NaN`/`0`/`-1` as a sentinel).

### REQ-016: Real Skip API route client
**EARS**: WHEN driver.mjs calls `skipApiClient.getRoute(params)` THE SYSTEM SHALL POST to Skip API's
live `/v2/fungible/route` endpoint with `amount_in`/`source_asset_chain_id`/`dest_asset_chain_id`
coerced to JSON strings (verified live: a numeric `chain_id` is REJECTED with
`invalid value for string field sourceAssetChainId`), `allow_unsafe: true` and `allow_multi_tx: true`
(verified live: this specific Base-USDC→AKT pair has NO single-tx route — omitting `allow_multi_tx`
returns Skip error code 5), and return the parsed JSON response body UNMODIFIED (its field names —
`dest_asset_denom`, `dest_asset_chain_id`, `amount_out`, `txs_required` — already match
`lib/pure/route-validation.mjs`'s `validateRoute` contract exactly, verified live 2026-07-11 against a
real 15-USDC-in quote).
**Edge Cases**:
- Non-2xx HTTP response, unparseable JSON, or a JSON body carrying Skip's own `code` error field: THE
  SYSTEM SHALL throw (driver.mjs's REQ-002 call site is wrapped in try/catch expecting exactly this).
- `params.source_asset_chain_id`/`dest_asset_chain_id` arriving as a JS `number` (driver.mjs's own
  `BASE_CHAIN_ID` literal): THE SYSTEM SHALL coerce via `String(...)` before it reaches the wire.
**Acceptance Criteria**:
- The request body's `amount_in` is always `String(params.amount_in)` (never a JS `number`, which would
  lose bigint precision for large amounts).
- A live-shaped success response passes unmodified through `validateRoute` (proven via
  `validRouteFixture()`'s own shape, which mirrors the real live response 1:1).

### REQ-017: Real relay poller (Base receipt wait + cross-chain relay settle-wait)
**EARS**: WHEN driver.mjs calls `relayPoller.waitForConfirmation(chainId, txHash, timeoutMs)` with a
NUMERIC `chainId` (the Base-signed leg 0, called with a real txHash) THE SYSTEM SHALL poll
`eth_getTransactionReceipt(txHash)` until it returns a receipt or `timeoutMs` elapses, returning
`"confirmed"` for `receipt.status === "0x1"`, `"reverted"` for any other landed status, and `"pending"`
on timeout. WHEN called with a STRING `chainId` (a relay-only leg ≥1, called with `txHash: null` — driver
never records a txHash for these legs) THE SYSTEM SHALL wait a bounded settle-window (`min(timeoutMs,
RELAY_SETTLE_WAIT_MS)`) and report `"confirmed"` only if that full window elapsed within `timeoutMs`,
else `"pending"`.
**Edge Cases**:
- **Documented limitation (flagged for adversary review)**: the string-`chainId` branch has NO
  txHash/address to independently verify against (the frozen `waitForConfirmation(chainId, txHash,
  timeoutMs)` interface provides neither for a relay-only leg) — its `"confirmed"` result is therefore
  OPTIMISTIC, not a genuine on-chain observation. This is safe ONLY because REQ-007
  (`lib/driver.mjs:209-224`) independently re-queries `chainReader.getAkashBalance()` after every leg
  reports confirmed and fails closed (`settlement_unverified`) if the real balance delta doesn't match
  the quote within `TOLERANCE_BPS` — a false "confirmed" here can only delay-and-retry via REQ-007, never
  produce a false overall success.
- `txHash` falsy for the numeric-`chainId` branch: THE SYSTEM SHALL return `"pending"` immediately
  (nothing to poll).
- `timeoutMs` non-numeric/`<=0`: THE SYSTEM SHALL treat it as `0` (immediate `"pending"`/settle-check
  with zero wait), never hang indefinitely.
**Acceptance Criteria**:
- Return value is always one of `"confirmed"` / `"pending"` / `"reverted"` (a string; driver.mjs only
  ever branches on `=== "confirmed"`, so any other literal is treated as not-yet-done).
- The EVM-vs-Cosmos branch is selected purely by `typeof chainId` (matches driver.mjs's own literal
  types: `BASE_CHAIN_ID` is a `number`, `AKASH_CHAIN_ID` is a `string`), never a chain-id string match.

### REQ-018: Real base-signer (the sole value-moving Base transaction) — HIGHEST RISK
**EARS**: WHEN driver.mjs calls `baseSigner.getAddress()` / `getNextNonce()` /
`signAndBroadcast({amount, nonce, sourceAddress, destinationAkashAddress})` THE SYSTEM SHALL sign and
broadcast EXACTLY ONE real Base-chain transaction — the `evm_tx` returned by Skip API's
`/v2/fungible/msgs` endpoint for this feature's live-confirmed route shape (Base USDC
-[CCTP,smart_relay]-> noble-1 -[PFM]-> osmosis-1 -[PFM swap]-> akashnet-2) — using the driver-supplied
`nonce` verbatim, and return `{txHash}`.
**Edge Cases (money-safety-critical)**:
- `sourceAddress` (if provided) not matching this signer's own derived address: THE SYSTEM SHALL throw
  BEFORE any network call (mirrors driver.mjs's own REQ-009 `expectedBaseSignerAddress` check).
- `destinationAkashAddress` not equal to this feature's single fixed colony destination constant
  (`akash1ms7gr5sxkv33ra353hg5lu8dm7akljdaamj523`, matching `bin/spawn-funding-swap.mjs`'s own
  never-overridable literal): THE SYSTEM SHALL throw BEFORE signing.
- A re-fetched Skip route (needed because the frozen `signAndBroadcast` interface receives no
  `quoteSnapshot`) whose `dest_asset_denom`/`dest_asset_chain_id` differ from the expected
  `uakt`/`akashnet-2`: THE SYSTEM SHALL throw BEFORE signing (never sign against a route Skip changed
  underneath this feature).
- Skip's `/v2/fungible/msgs` response containing zero or more-than-one `evm_tx` entries: THE SYSTEM SHALL
  throw (this feature only supports its single-signed-leg route shape).
- `evm_tx.signer_address` not matching this signer's own derived address: THE SYSTEM SHALL throw.
- An unresolved `evm_tx.required_erc20_approvals` allowance at sign time (i.e. `getNextNonce()`'s own
  prior approval-settlement did not actually land): THE SYSTEM SHALL throw rather than attempt a SECOND
  approve transaction inline (which would consume an extra nonce and break the driver's single-nonce
  crash-recovery tracking — see the module's own header comment for the full nonce-tracking rationale).
- `ANICCA_HOME` unset when this module's own key-resolution is invoked: THE SYSTEM SHALL throw (mirrors
  `resolve-swap-identity.mjs`'s own fail-closed gate; belt-and-suspenders since the CLI's REQ-009 check
  already guarantees this in production).
**Acceptance Criteria**:
- `getNextNonce()` NEVER returns a nonce that a subsequent, in-flight ERC-20 approval transaction (sent
  BY THIS SAME MODULE, as part of settling `required_erc20_approvals`) also used — the approval
  check-and-send happens entirely INSIDE `getNextNonce()`, before the returned nonce is captured, so the
  value driver.mjs durably persists as "the leg-0 nonce" is ALWAYS the swap tx's own, exclusive nonce
  (proven via the injected `walletClientFactory` spy in this module's own tests: the approve tx's nonce,
  if any, is always the return value MINUS the number of approvals actually sent).
- `signAndBroadcast`'s on-chain `nonce` field is always EXACTLY the `nonce` parameter passed in — never a
  freshly re-queried value.
- The Cosmos-SDK addresses passed into Skip's `address_list` for noble-1/osmosis-1 are ALWAYS derived
  from this SAME module's own resolved private key (REQ-013) — never a hardcoded/random placeholder
  string, so any relay-failure `recover_address` refund remains recoverable by this instance.

## Non-functional requirements (sprint-2)

- **NFR-5 (money-safety)**: no real-client module ever signs/broadcasts a value-moving Base transaction
  without first verifying BOTH the signer identity (REQ-009, unchanged) AND the destination address
  (REQ-018) match their expected, fixed values.
- **NFR-6 (test isolation)**: no test file anywhere in this feature (including `lib/real-clients/
  __tests__/**`) ever performs a real network call, real signing, or real subprocess invocation of the
  `akash`/production `provider-services` CLI — every transport boundary (`fetch`, `execFile`,
  viem wallet/public clients) is injectable and mocked in tests (Test-Money Safety Rule, extended to
  sprint-2's own new unit-test directory, which PROP-021's existing scan does not cover — enforced here
  by convention + this spec, since it is a NEW test directory PROP-021 was written before this sprint
  existed).
- **NFR-7 (bounded approval blast radius)**: the ERC-20 allowance this feature ever grants to a Skip
  spender contract is capped at a small, fixed literal (`APPROVAL_CAP_BASE_UNITS = 100_000_000n`, $100),
  never `MAX_UINT256` — mirrors `lib/pure/constants.mjs`'s own `SWAP_MAX_USD=20` bounded-literal
  philosophy.
