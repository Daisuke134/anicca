# 13d-b Base USDC Payout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send only verified, reserve-surplus Base USDC from one Life Manager agent wallet to that tenant's registered wallet, then record and report the exact confirmed transfer.

**Architecture:** A pure policy computes the maximum safe payout from verified ledger rows and the measured on-chain balance. A separate EIP-3009 boundary signs, verifies, settles, and independently checks the Base receipt. The runtime remains tenant-scoped, records `financial_user_transfer` only after exact receipt verification, and sends Telegram only after the append-only ledger accepts the receipt.

**Tech Stack:** Node.js CommonJS, `node:test`, viem, Base mainnet (`eip155:8453`), Circle USDC, x402 facilitator v2, Supabase REST, Telegram Bot API.

## Global Constraints

- Default survival reserve is exactly `35_000_000` USDC atomic units ($35.000000); callers may raise it, never silently lower it.
- `financial_external_income - financial_realized_loss - financial_fee - financial_user_transfer` is the only ledger surplus; deposit, self-funding, internal move, and unverified rows contribute zero.
- Payout atomic amount is `min(verified ledger surplus, on-chain balance - reserve, explicit transaction cap)`, clamped at zero.
- A tenant `uid` is mandatory; the runtime reads only that row and requires its own `telegram_chat_id` plus `payout_destination.status=usable`.
- The agent private key is read only after policy returns a positive amount and is never logged, persisted, returned, or included in an error.
- Settlement is not success until Base chain id is 8453, receipt status is success, and exactly one Circle USDC `Transfer(agent,destination,amount)` log exists.
- `financial_user_transfer` is written after chain verification with deterministic key `payout:<tx>:transfer`; a retry is a duplicate, never a second transfer claim.
- A zero balance or zero verified surplus is an honest no-op and performs no key read, signing, facilitator call, ledger write, or Telegram send.
- Official contracts: Circle `EIP3009.sol` defines authorization-based transfers; Coinbase x402 v2 exact uses EIP-3009 and `/verify` then `/settle`; viem `signTypedData` signs EIP-712 typed data.

---

### Task 1: Reserve-aware payout policy

**Files:**
- Create: `apps/life-manager/lib/payout-policy.test.js`
- Create: `apps/life-manager/lib/payout-policy.js`

**Interfaces:**
- Consumes: `{ rows, walletAddress, onchainUsdcAtomic, reserveAtomic?, maxPayoutAtomic? }`
- Produces: `computePayout(input) -> { amountAtomic, verifiedSurplusMinor, reason, reserveAtomic }`

- [ ] **Step 1: Write the failing policy tests**

```js
test("verified profit pays only the amount above the $35 reserve", () => {
  assert.deepEqual(computePayout({
    rows: [
      earning("financial_external_income", 10_000),
      earning("financial_fee", 500),
      earning("financial_user_transfer", 1_000),
    ],
    walletAddress: WALLET,
    onchainUsdcAtomic: "42000000",
  }), {
    amountAtomic: "7000000",
    verifiedSurplusMinor: 8500,
    reason: "ready",
    reserveAtomic: "35000000",
  });
});

test("bootstrap deposits never create payout capacity", () => {
  const result = computePayout({
    rows: [earning("financial_deposit", 100_000)],
    walletAddress: WALLET,
    onchainUsdcAtomic: "1000000000",
  });
  assert.equal(result.amountAtomic, "0");
  assert.equal(result.reason, "no_verified_surplus");
});
```

- [ ] **Step 2: Run `node --test apps/life-manager/lib/payout-policy.test.js` and verify failure is `MODULE_NOT_FOUND`**

- [ ] **Step 3: Implement integer-only normalization, wallet scoping, closed kind handling, reserve floor, and min-cap arithmetic**

```js
function computePayout(input) {
  // Normalize all money to BigInt, derive verified minor-unit surplus,
  // convert cents to six-decimal USDC, and return the smallest safe bound.
}
```

- [ ] **Step 4: Run the focused test and verify every policy case passes**

- [ ] **Step 5: Commit the policy and its tests**

### Task 2: EIP-3009 settlement and exact receipt verification

**Files:**
- Create: `apps/life-manager/lib/base-usdc-payout.test.js`
- Create: `apps/life-manager/lib/base-usdc-payout.js`

**Interfaces:**
- Consumes: `settleBaseUsdc({ privateKey, walletAddress, destination, amountAtomic, facilitatorUrl, rpcUrl, nowMs?, fetchImpl? })`
- Produces: `{ txHash, amountAtomic, from, to, blockNumber }` only after independent receipt verification

- [ ] **Step 1: Write failing tests for signer/address mismatch, malformed destination, verify refusal, settle refusal, wrong chain, failed receipt, wrong transfer log, duplicate transfer logs, and the exact success path**

```js
test("a settled response is accepted only when Base contains one exact USDC transfer", async () => {
  const receipt = await settleBaseUsdc(validRequest, controlledBoundaries);
  assert.deepEqual(receipt, {
    txHash: TX,
    amountAtomic: "7000000",
    from: WALLET,
    to: DESTINATION,
    blockNumber: "123",
  });
});
```

- [ ] **Step 2: Run the focused test and verify it fails because the module does not exist**

- [ ] **Step 3: Implement the Base USDC EIP-712 domain and `TransferWithAuthorization` message using viem**

```js
const domain = {
  name: "USD Coin",
  version: "2",
  chainId: 8453,
  verifyingContract: BASE_USDC,
};
```

- [ ] **Step 4: Implement x402 `/verify` and `/settle`, then independently fetch chain id and receipt and require one exact Transfer log**

- [ ] **Step 5: Run focused tests and verify all settlement branches pass**

- [ ] **Step 6: Commit settlement code and tests**

### Task 3: Tenant-scoped payout runtime and append-only receipt

**Files:**
- Create: `apps/life-manager/lib/payout-runtime.test.js`
- Create: `apps/life-manager/lib/payout-runtime.js`
- Modify: `apps/life-manager/lib/earnings-runtime.js`

**Interfaces:**
- Consumes: `runPayout({ uid, wallet, reserveAtomic?, maxPayoutAtomic? }, deps)`
- Produces: `{ status: "noop"|"transferred"|"duplicate", reason?, amountAtomic, txHash? }`
- Reuses: `recordEarnLoopRevenue(entry, opts)`

- [ ] **Step 1: Write failing tests showing missing UID and cross-tenant rows fail before money I/O**

- [ ] **Step 2: Write failing tests showing zero policy amount never reads the private key, signs, settles, writes, or sends Telegram**

- [ ] **Step 3: Write the failing success test: exact tenant row → policy → settlement → `financial_user_transfer` → Telegram receipt, in that order**

```js
assert.deepEqual(events, [
  "read-tenant:u1",
  "read-ledger",
  "read-balance",
  "read-key",
  "settle",
  "record-transfer",
  "send-telegram",
]);
```

- [ ] **Step 4: Run the focused test and verify expected missing-runtime failures**

- [ ] **Step 5: Add a bounded wallet-scoped ledger reader and implement the fail-closed runtime**

- [ ] **Step 6: Render the §9.11 receipt with exact amount and Basescan transaction link**

- [ ] **Step 7: Run focused tests and verify all tenant, no-op, ordering, duplicate, and error branches pass**

- [ ] **Step 8: Commit runtime code and tests**

### Task 4: Production CLI, verification, and evidence

**Files:**
- Create: `apps/life-manager/scripts/run-agent-payout.js`
- Create: `apps/life-manager/scripts/run-agent-payout.test.js`
- Create: `docs/evidence/agent-economy/2026-07-27-13d-base-usdc-payout.json`
- Modify: `docs/superpowers/specs/2026-05-20-life-manager-one-repo.md`
- Modify: `docs/handoff.md`

**Interfaces:**
- CLI: `node apps/life-manager/scripts/run-agent-payout.js --uid <tenant-uid>`
- Output: one secret-free JSON object with measured counts/status; never a private key, full destination, Supabase credential, or Telegram token

- [ ] **Step 1: Write failing CLI tests for mandatory UID, zero-balance no-op, and secret-free output**

- [ ] **Step 2: Run the CLI test and verify expected missing-script failure**

- [ ] **Step 3: Implement dependency loading, protected wallet read, Base balance read, and exit-code contract**

- [ ] **Step 4: Run focused FIN/payout tests**

Run:

```bash
node --test \
  apps/life-manager/lib/agent-wallet.test.js \
  apps/life-manager/lib/earnings-ledger.test.js \
  apps/life-manager/lib/earnings-runtime.test.js \
  apps/life-manager/lib/payout-question.test.js \
  apps/life-manager/lib/payout-address-intake.test.js \
  apps/life-manager/lib/payout-policy.test.js \
  apps/life-manager/lib/base-usdc-payout.test.js \
  apps/life-manager/lib/payout-runtime.test.js \
  apps/life-manager/scripts/run-agent-payout.test.js
```

- [ ] **Step 5: Run the full `node --test apps/life-manager/lib/*.test.js` suite and distinguish pre-existing baseline failures from new failures**

- [ ] **Step 6: Inspect the diff for secrets and run the production CLI for the exact tenant without printing UID or destination**

- [ ] **Step 7: Record the observed zero-or-transfer outcome, update the SSOT cursor, commit, push, merge, reinstall from canonical main, and rerun production verification**

