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
**EARS**: WHEN driver.mjs calls `baseSigner.getAddress()` / `getNextNonce(amount)` /
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
- **(impl review iter1, FIND-001 CRITICAL fix / PROP-050)** Skip's `/v2/fungible/msgs` response is a
  third-party HTTP body, NEVER trusted on faith for the actual value-moving contents of `evm_tx`: THE
  SYSTEM SHALL decode and bound-check `evm_tx` against the driver-supplied intent BEFORE ever signing —
  (a) `evm_tx.data` MUST NOT decode as a bare ERC-20 `transfer`/`transferFrom` selector (this route's
  live-confirmed shape is always a router/entry-point contract call, per Skip's own EVM Transactions doc:
  a bare transfer selector needs no approval at all and could move up to the entire wallet balance); (b)
  `evm_tx.to` MUST exactly equal the sole `required_erc20_approvals[0].spender` and MUST NOT be the USDC
  contract itself (self-consistency allowlist, derived from the live route response, never a hardcoded
  Skip contract-address literal); (c) `required_erc20_approvals[0].amount` (Skip's self-reported metadata
  field) MUST exactly equal the driver-supplied `amount` parameter (bigint equality) and MUST NOT exceed
  `MAX_SWAP_BASE_UNITS` (`SWAP_MAX_USD`'s own base-unit equivalent, $20 — impl review iter2: previously a
  looser, independent `APPROVAL_CAP_BASE_UNITS`, $100, which was itself iter2's root cause); (d) **(impl
  review iter2 addition, the CRITICAL fix itself)** the ACTUAL, CURRENT on-chain allowance for
  `required_erc20_approvals[0].spender` — queried fresh via RPC at broadcast time, NEVER inferred from
  Skip's metadata field alone — MUST be EXACTLY `amount` (neither insufficient, which would revert
  on-chain, nor in EXCESS, which is itself the exploitable attack surface: a standing/stale higher
  allowance from a prior swap combined with attacker-controlled calldata could otherwise pull up to that
  standing amount even though the reported metadata amount looked honest); (e) `evm_tx.value` MUST be
  exactly `0n`. THE SYSTEM SHALL throw (never broadcast) on any violation. **The resulting invariant: even
  a fully-malicious/compromised Skip route can never cause this module to authorize moving more than
  `amount` (<= `SWAP_MAX_USD`, $20) of USDC in one signed transaction — full stop — because that is the
  most that is EVER approved on-chain for any spender this module calls (see `getNextNonce(amount)`'s own
  edge case below), and gate (d) independently re-verifies this against real chain state before every
  broadcast.**
- **(impl review iter1, FIND-001 CRITICAL fix; SUPERSEDED and corrected by impl review iter2, FIND-001
  CRITICAL fix — this replaces the iter1 text, which incorrectly implied the metadata-amount check above
  alone was sufficient)** `getNextNonce(amount)` (previously `getNextNonce()`, no argument — now REQUIRES
  the real, already-capped swap `amount`, available to driver.mjs's `ensureLeg0Submitted` BEFORE it is
  ever called, per REQ-006/REQ-012's choke point) grants an ERC-20 allowance to this route's spender that
  is EXACTLY `amount`, NEVER a standing higher cap that outlives the swap it was granted for: IF the
  current on-chain allowance already exactly equals `amount`, no transaction is sent (idempotent); IF it
  is non-zero and does not already equal `amount` (e.g. residual from a prior swap's different amount), it
  is FIRST reset to `0`, THEN set to `amount` (approve-race-safe sequence); IF it is `0`, it is set
  directly to `amount`. THE SYSTEM SHALL NOT send a separate post-swap reset-to-`0` transaction (this
  would require its own nonce, which the ledger's single-nonce-per-leg-0 crash-recovery model — see this
  module's own header comment — does not track, and a crash between the swap broadcast and a hypothetical
  reset tx would leave that reset's own state unaccounted for by resume logic); instead, any residual
  allowance (bounded, at most, to the LAST swap's own `amount` — never more than `SWAP_MAX_USD`, and never
  the old $100 standing cap) is self-healed by the NEXT swap's own exact-amount settlement.
- **(impl review iter1, FIND-003, documented assumption — UNCHANGED by the iter2 fix above)**
  `getNextNonce(amount)`'s approval-probe uses a small fixed `APPROVAL_PROBE_AMOUNT_BASE_UNITS` (1 USDC)
  to learn which spender contract to grant an allowance to, independent of the real swap amount (the
  actual amount granted to that spender is, however, always the real `amount` — never this probe value,
  per the iter2 fix above). Skip's spender-contract selection for a route COULD in principle vary by
  amount tier: IF that happens, THE SYSTEM SHALL fail CLOSED (refuse to sign, via the existing allowance
  check AND the new self-consistency gate above) — this is an accepted denial-of-service risk (this
  feature's funding mechanism stops working until the probe/real spenders agree again), NEVER a fund-loss
  risk (no tx is ever signed/broadcast against a spender that was not actually granted the exact-amount,
  on-chain-verified allowance).
- `ANICCA_HOME` unset when this module's own key-resolution is invoked: THE SYSTEM SHALL throw (mirrors
  `resolve-swap-identity.mjs`'s own fail-closed gate; belt-and-suspenders since the CLI's REQ-009 check
  already guarantees this in production).
**Acceptance Criteria**:
- `getNextNonce(amount)` NEVER returns a nonce that a subsequent, in-flight ERC-20 approval transaction
  (sent BY THIS SAME MODULE, as part of settling `required_erc20_approvals`) also used — the approval
  check-and-send happens entirely INSIDE `getNextNonce(amount)`, before the returned nonce is captured, so
  the value driver.mjs durably persists as "the leg-0 nonce" is ALWAYS the swap tx's own, exclusive nonce
  (proven via the injected `walletClientFactory` spy in this module's own tests: each approve tx's nonce
  is always strictly less than the return value, and strictly increasing across the reset-then-set pair
  when both are sent).
- `signAndBroadcast`'s on-chain `nonce` field is always EXACTLY the `nonce` parameter passed in — never a
  freshly re-queried value.
- The Cosmos-SDK addresses passed into Skip's `address_list` for noble-1/osmosis-1 are ALWAYS derived
  from this SAME module's own resolved private key (REQ-013) — never a hardcoded/random placeholder
  string, so any relay-failure `recover_address` refund remains recoverable by this instance.
- **(impl review iter1, PROP-050; tightened impl review iter2)** `signAndBroadcast` NEVER broadcasts an
  `evm_tx` whose decoded/verified amount, destination contract, native value, or ACTUAL on-chain allowance
  diverge from the driver-supplied intent (see the new edge cases above) — proven via the injected
  `walletClientFactory` spy in this module's own tests: `walletClientFactory.sent.length` stays `0` on
  every one of PROP-050's refusal-path tests (including the new iter2 "standing-excess-allowance +
  honest-looking metadata" attack test, which reproduces this iteration's exact critical finding), and is
  exactly `1` on every honest-tx path test.
- **(impl review iter2, FIND-001 CRITICAL fix)** `getNextNonce(amount)` grants an on-chain ERC-20
  allowance to any spender it approves that is EXACTLY `amount` — never a standing higher cap — proven via
  the injected `walletClientFactory` spy decoding each `approve()` call's own `(spender, amount)` args:
  the approved amount always equals the `amount` `getNextNonce` was called with, and a prior non-zero,
  non-matching allowance always produces exactly two approve txs (reset-to-`0`, then set-to-`amount`) at
  two strictly-sequential nonces.
- **(impl review iter1, FIND-004)** When the caller (driver.mjs) supplies `expectedAmountOutUakt`/
  `expectedTxsRequired` (its own REQ-002-validated quote), `signAndBroadcast`'s own necessary route
  re-fetch is reconciled against them and refuses to sign if they diverge — this parameter pair is
  OPTIONAL (omitting it preserves this module's prior, narrower guarantee for any caller that cannot
  supply it), but driver.mjs's own `ensureLeg0Submitted` ALWAYS supplies it.

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
- **NFR-7 (bounded approval blast radius, impl review iter2 CRITICAL fix — supersedes the iter1 text,
  which incorrectly stated the bound as a flat, standing `APPROVAL_CAP_BASE_UNITS = 100_000_000n`, $100)**:
  the ERC-20 allowance this feature ever grants to a Skip spender contract is bound EXACTLY to the CURRENT
  swap's own `amount` (`<= SWAP_MAX_USD`, $20) — NEVER a standing cap that persists across swaps, and
  never `MAX_UINT256`. `MAX_SWAP_BASE_UNITS` (the absolute defense-in-depth ceiling `signAndBroadcast`
  enforces) is derived directly from `lib/pure/constants.mjs`'s own `SWAP_MAX_USD`/`USDC_DECIMALS_BASE`
  (the SAME single choke point the driver's own per-invocation spend cap uses), not a second,
  independently-tunable literal. Worst-case loss under a fully-malicious/compromised Skip route is
  therefore bounded to `amount` (at most `SWAP_MAX_USD`, $20) — a 5x tightening from iter1's actual (if
  unacknowledged) $100 worst case, which was this iteration's CRITICAL finding (FIND-001, iter2).
- **NFR-8 (impl review iter1, FIND-006, documented assumption)**: the nonce-tracking crash-recovery
  guarantee (base-signer.mjs's own header comment, "Nonce-tracking / ERC-20 approval design") is provably
  correct ONLY under the assumption that this feature's Base wallet's on-chain nonce space is NEVER
  advanced by any OTHER concurrent process sharing the SAME `ANICCA_HOME`-resolved private key. REQ-010's
  canonical lock (`ledgerStore.withLock(destinationAkashAddress, ...)`) guards against a second
  CONCURRENT swap run of THIS feature, but does nothing to serialize this wallet's nonce space against
  any other Base-signing activity elsewhere in the colony for the same instance's key. This is currently
  safe because, per base-signer.mjs's own module header, every OTHER Base-chain signer in this repo
  (`skills/economy/gig/lib/escrow.mjs`) only ever signs a GASLESS EIP-3009 authorization — no other
  on-chain-nonce-consuming Base signer currently exists for this key. This assumption is NOT enforced by
  any runtime check (e.g. verifying the pending nonce hasn't moved between `getNextNonce()`'s approval-
  settlement and the driver's own durable write); a future colony change (a second skill reusing this
  same key for a real on-chain tx) would silently break this guarantee and MUST re-verify this NFR before
  shipping.

## Spec changelog

- **sprint-2 impl iter1 fixes FIND-001..007** (impl review iteration 1, findings closed): FIND-001
  (CRITICAL, PROP-050) — `signAndBroadcast` now decodes+verifies the actual signed tx amount/destination/
  value against intent before broadcasting, rather than trusting Skip's HTTP response; FIND-002 — PROP-050
  closes the proof-obligation gap this finding identified; FIND-003 — the probe-vs-real spender assumption
  is now documented (REQ-018 edge cases) and tested (PROP-051), fail-closed confirmed; FIND-004 —
  `signAndBroadcast` now accepts optional `expectedAmountOutUakt`/`expectedTxsRequired` and reconciles its
  own route re-fetch against driver.mjs's already-validated REQ-002 quote; FIND-005 — `DESTINATION_AKASH_
  ADDRESS`/`BASE_CHAIN_ID`/`BASE_USDC_DENOM`/`AKASH_CHAIN_ID`/`AKASH_UAKT_DENOM` are now defined once in
  `lib/pure/constants.mjs` and imported everywhere, closing the cross-file hand-copied-literal drift risk;
  FIND-006 — the wallet-global-nonce-ownership assumption is now documented as NFR-8; FIND-007 — PROP-049's
  scan now actually implements the "no bare `createRealXxx()`" check its own description claimed (plus a
  string-literal-aware comment-stripper fix discovered while implementing it), and the previously-bare
  call sites (2 in base-signer.test.mjs, 2 in relay-poller.test.mjs) now inject an explicit throw-guard
  `fetchImpl`.

- **sprint-2 impl iter2 fix FIND-001 (CRITICAL, per-swap exact-amount approval, loss bounded to amount)**
  (impl review iteration 2, finding closed): iter1's fix left a STANDING allowance (topped up to a flat
  `APPROVAL_CAP_BASE_UNITS`, $100, never lowered across swaps) and only checked Skip's SELF-REPORTED
  `required_erc20_approvals[0].amount` metadata field, never the ACTUAL on-chain allowance — a fully-
  malicious/compromised Skip route could therefore name the already-approved spender, report an honest-
  looking metadata amount (passing the old gate), and pull the full standing $100 via calldata the module
  never inspected, a 5x loss-amplification over `SWAP_MAX_USD` ($20). THE FIX: `getNextNonce()` is now
  `getNextNonce(amount)` and grants EXACTLY `amount` (never a standing higher cap) to this swap's spender,
  using a reset-to-`0`-then-set-to-`amount` sequence whenever a prior non-matching non-zero allowance is
  found (approve-race-safe); `signAndBroadcast` independently re-verifies, by fresh RPC query at broadcast
  time, that the ACTUAL on-chain allowance for `evm_tx.to` is EXACTLY `amount` (refusing on either
  insufficiency OR excess) — never trusting Skip's metadata field alone. `MAX_SWAP_BASE_UNITS` is now
  derived directly from `SWAP_MAX_USD`/`USDC_DECIMALS_BASE` ($20's base-unit equivalent) rather than
  reusing the old, looser `APPROVAL_CAP_BASE_UNITS` ($100), which no longer exists as a separate concept.
  **The new invariant: on-chain allowance == `amount` per swap; worst-case loss under a fully-malicious
  route is bounded to `amount` (<= `SWAP_MAX_USD`, $20), never the old $100 standing-cap bound.** REQ-018
  edge cases/acceptance criteria and NFR-7 updated accordingly; `driver.mjs`'s `ensureLeg0Submitted` now
  passes its already-computed `requiredBaseUnits` into `getNextNonce(amount)`.
