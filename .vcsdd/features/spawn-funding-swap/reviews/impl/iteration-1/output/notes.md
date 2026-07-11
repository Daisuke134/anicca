# spawn-funding-swap sprint-2 real-clients — adversary notes (iteration 1)

Fresh-context review. No manifest.json was found at
`.vcsdd/features/spawn-funding-swap/reviews/impl/iteration-1/input/manifest.json` in this worktree (the
`.vcsdd/features/spawn-funding-swap/` tree does not exist yet) — reviewed directly against the task's
file list, `skills/self/spawn-funding-swap/specs/{behavioral-spec,verification-architecture}.md`,
`lib/driver.mjs`, `lib/pure/{constants,settlement,route-validation}.mjs`, `bin/spawn-funding-swap.mjs`,
and every file under `lib/real-clients/**` + `lib/real-clients/__tests__/**` +
`lib/__tests__/cosmos-address.test.mjs`. Suite-run claim (159/159) was not independently re-run (no Bash
tool available to this adversary) — treated as thinker-reported, not adversary-verified.

## Files read in full
- `lib/real-clients/base-signer.mjs` (300 lines)
- `lib/real-clients/chain-reader.mjs`
- `lib/real-clients/price-oracle.mjs`
- `lib/real-clients/skip-api-client.mjs`
- `lib/real-clients/relay-poller.mjs`
- `lib/pure/cosmos-address.mjs`
- `lib/real-clients/__tests__/{base-signer,chain-reader,price-oracle,relay-poller,test-money-safety-scan}.test.mjs`
- `lib/__tests__/cosmos-address.test.mjs`
- `lib/__tests__/fakes/fake-clients.mjs` (frozen contract shapes)
- `lib/driver.mjs`, `lib/pure/constants.mjs`, `lib/pure/settlement.mjs`, `lib/pure/route-validation.mjs`
- `bin/spawn-funding-swap.mjs`
- `skills/self/spawn-funding-swap/specs/{behavioral-spec,verification-architecture}.md`

## Per-question findings

1. **BASE-SIGNER trace (Q1)**: signAndBroadcast correctly gates on sourceAddress/destinationAkashAddress
   (REQ-009-style, fail-closed BEFORE any network call — verified, PROP-045 tests pass this closed-path).
   The nonce fix (approval moved inside getNextNonce()) is internally consistent: `ensureApprovalsSettled`
   AWAITS `waitForTransactionReceipt` for every approve tx before `getNextNonce()`'s own
   `eth_getTransactionCount(pending)` call, so the returned nonce provably reflects the just-mined approve
   tx and is the swap tx's own exclusive nonce (PROP-043 test proves `approveNonce < returnedNonce`
   correctly). HOWEVER: the module does NOT independently bound/verify the actual amount or destination
   contract being signed (FIND-001, CRITICAL) — it trusts Skip's `evm_tx.to`/`data`/`value` completely.
   The only amount-adjacent cap in the whole path is APPROVAL_CAP_BASE_UNITS ($100), which bounds a
   `transferFrom`-style spend but does NOT bound a direct `transfer()`-style call the signer's own key
   could authorize with zero prior approval. This is the single blocking finding.

2. **COSMOS-ADDRESS (Q2)**: the bech32 implementation is standard BIP-173 (correct generator polynomial
   `0x3b6a57b2...`, correct checksum XOR-1 constant for classic bech32 — NOT bech32m, matching Cosmos SDK's
   own convention), correct HRP-expand/checksum/charset. `deriveCosmosAddress` correctly composes
   `RIPEMD160(SHA256(compressedPubkey)) -> bech32(hrp)`, the standard Cosmos-SDK secp256k1 address scheme.
   Verified against `lib/__tests__/cosmos-address.test.mjs`'s known-answer vector (independently
   cross-checked per the test's own comment) and an hrp-participates-in-checksum proof test. No
   discrepancy found. PASS on this specific question.

3. **SKIP-API-CLIENT (Q3)**: request shape matches the spec's live-verified fields, `chain_id` fields are
   always `String(...)`-coerced regardless of input type (PROP-037), fail-closed on non-2xx/`code`-bearing
   responses (PROP-038). It does NOT itself validate the returned route's destination — that check lives
   in `lib/pure/route-validation.mjs`'s `validateRoute` (called by driver.mjs), which correctly rejects any
   `dest_asset_denom !== "uakt"` / `dest_asset_chain_id !== "akashnet-2"` / non-positive `amount_out`. A
   manipulated Skip *route* response therefore cannot silently redirect the swap's declared destination —
   but see FIND-004: base-signer.mjs's OWN internal route re-fetch (inside signAndBroadcast) is a second,
   unreconciled call to the same endpoint, and FIND-001 for why the msgs-response's actual evm_tx contents
   are never validated at all.

4. **RELAY-POLLER (Q4)**: the optimistic bounded-wait design for the relay-only leg is SOUND, verified by
   cross-reading `lib/driver.mjs:209-224`'s REQ-007: `postBalanceUakt = await ctx.chainReader.getAkashBalance(...)`
   is a genuine fresh re-query (not inferred from leg/relay status), and `verifySettlement`
   (`lib/pure/settlement.mjs`) does real bigint delta math against `quotedAmountOutUakt * (10000-toleranceBps)/10000`
   — confirmed this is not vacuous (it does not merely check `delta > 0` or trust the route's promise). A
   false "confirmed" from relay-poller's optimistic branch can only cause a premature ledger leg-write, and
   the ACTUAL swap-success verdict is gated by this independent balance re-query, exactly as the spec
   claims. PASS on this specific question.

5. **CHAIN-READER (Q5)**: `getBaseTxStatusByNonce`'s nonce-count technique
   (`eth_getTransactionCount(address, "latest")` count > nonce → "confirmed") is the standard, correct
   technique. Units verified: `getAkashBalance` returns the raw `uakt` string as bigint (6-decimal, per
   AKT_DECIMALS in constants.mjs), `getBaseUsdc` returns raw eth_call result (6-decimal USDC, never
   `/1e6`-scaled — confirmed by PROP-034's own test asserting `936500n` for hex `0xe4e1c`, and by contrast
   with `skills/_shared/lib/usdc.mjs`'s different, Number-scaled contract, which this module explicitly
   does NOT reuse), `getBaseGas` returns raw wei (18-decimal, PROP-034 test asserts
   `10_000_000_000_000_000n` for 0.01 ETH). No unit confusion found. PASS on this specific question.

6. **PRICE-ORACLE (Q6)**: fails closed (throws) on non-2xx, missing field, non-numeric, `<=0`, and
   non-finite (Infinity) — all six PROP-036 cases tested and structurally correct in the implementation.
   PASS on this specific question.

7. **TESTS (Q7)**: 55 new tests were not independently counted by this adversary (no Bash access), but
   every real-clients test file inspected genuinely mocks its transport boundary (fetchImpl/execFileImpl/
   walletClientFactory/publicClientFactory) — no real network call was found in any test file read. A
   money-safety-scan test (PROP-049) IS present, but its actual implementation is narrower than its own
   documented claim (FIND-007, LOW). RED-phase genuineness ("every test... MUST fail until Phase 2b") is
   asserted in every test file's own header comment but was not independently re-run by this adversary.

## Go/No-Go for a real Base -> Akash swap

**NO-GO.** FIND-001 (critical) means the highest-risk transaction-signing code in the colony currently
trusts a third-party HTTP API's response body completely for the actual value-moving transaction contents
(destination contract + encoded amount), with no independent verification. This must be fixed — at
minimum, decode `evm_tx.data`'s encoded transfer/call amount and assert it equals the `amount` parameter
(or the already-validated `quoteSnapshot`'s expectation), and/or allowlist the expected Skip/CCTP contract
address(es) for `evm_tx.to` — before any real funds are put behind this code path. FIND-002 (no proof
obligation exists for this property) and FIND-003 (probe-route-vs-real-route spender mismatch, likely
denial-of-service rather than loss) should be fixed in the same pass since they share the same code region.
