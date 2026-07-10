// VCSDD spawn-funding-swap Phase 2a (RED) shared test fakes. Test-Money Safety Rule (binding,
// PROP-021): this file contains ZERO imports of the concrete SkipApiClient/ChainReader/BaseSigner/
// AkashSigner-subprocess/PriceOracle implementation modules and ZERO real endpoint literal strings —
// every client below is an in-memory fake/spy, never a real network/RPC/signing client. Shared by every
// driver-level test file so the fake shapes stay consistent with the contract lib/driver.mjs (Phase 2b)
// will actually implement against.

// spyFn(impl) — a minimal call-recording wrapper so tests can assert exact call arguments/order without
// pulling in a mocking library the rest of this codebase doesn't already depend on (mirrors the
// spy-by-hand style already used in colony-spawn-lock.test.mjs's walletGenCalls counter, generalized).
export function spyFn(impl = () => {}) {
  const calls = [];
  const fn = (...args) => {
    calls.push(args);
    return impl(...args);
  };
  fn.calls = calls;
  return fn;
}

export function createFakeChainReader({
  akashBalanceUakt = 0n,
  baseUsdcBalance = 0n,
  baseGasBalance = 0n,
  baseTxStatusByNonce = {}, // Map-like plain object: `${address}:${nonce}` -> 'confirmed' | 'not-found'
} = {}) {
  return {
    getAkashBalance: spyFn(async () => akashBalanceUakt),
    getBaseUsdc: spyFn(async () => baseUsdcBalance),
    getBaseGas: spyFn(async () => baseGasBalance),
    getBaseTxStatusByNonce: spyFn(async (address, nonce) => baseTxStatusByNonce[`${address}:${nonce}`] ?? "not-found"),
  };
}

export function createFakePriceOracle({ aktUsdPrice = 1.0, shouldReject = false } = {}) {
  return {
    getAktUsdPrice: spyFn(async () => {
      if (shouldReject) throw new Error("fake price oracle: injected failure");
      return aktUsdPrice;
    }),
  };
}

export function createFakeSkipApiClient({ routeResponse = null, shouldReject = false } = {}) {
  return {
    getRoute: spyFn(async () => {
      if (shouldReject) throw new Error("fake skip api client: injected failure");
      return routeResponse;
    }),
  };
}

export function createFakeBaseSigner({
  address = "0xFAKE_BASE_SIGNER_ADDRESS",
  txHash = "0xFAKE_TX_HASH",
  nextNonce = 0n,
  shouldReject = false,
} = {}) {
  return {
    getAddress: spyFn(async () => address),
    getNextNonce: spyFn(async () => nextNonce),
    signAndBroadcast: spyFn(async () => {
      if (shouldReject) throw new Error("fake base signer: injected failure");
      return { txHash };
    }),
  };
}

export function createFakeRelayPoller({ statusesByChain = {} } = {}) {
  // statusesByChain: chainId -> either a fixed status string, or an array of statuses consumed
  // one-per-call (so a test can simulate "pending, pending, ..." across repeated poll attempts).
  const callCounts = {};
  return {
    waitForConfirmation: spyFn(async (chainId) => {
      callCounts[chainId] = (callCounts[chainId] ?? 0) + 1;
      const entry = statusesByChain[chainId];
      if (Array.isArray(entry)) {
        const idx = Math.min(callCounts[chainId] - 1, entry.length - 1);
        return entry[idx];
      }
      return entry ?? "confirmed";
    }),
  };
}

// createFakeLedgerStore — a fully in-memory fake of the LedgerStore contract (lock + read/write),
// used by driver tests that do NOT need to prove real cross-process file-lock contention (that is
// PROP-010's job, exercised in driver-lock-and-concurrency.test.mjs against the REAL ledger-store.mjs).
export function createFakeLedgerStore({ initialState = {}, backingStore = null } = {}) {
  // backingStore lets a test share persisted ledger CONTENTS across multiple createFakeLedgerStore
  // instances (each representing a separate simulated process attempt) while each instance keeps its
  // OWN independent `locked` flag — modeling "a crashed process no longer holds the lock, but the
  // durable ledger file it wrote to survives" (REQ-005's crash-recovery premise). structuredClone
  // (not JSON round-trip) is used so bigint fields (nonces, amounts) survive the store/retrieve cycle
  // with their exact type intact.
  const store = backingStore ?? new Map(Object.entries(initialState));
  let locked = false;
  return {
    withLock: spyFn(async (destinationAddress, fn) => {
      if (locked) return { ok: false, reason: "locked" };
      locked = true;
      try {
        const result = await fn();
        return { ok: true, result };
      } finally {
        locked = false;
      }
    }),
    readState: spyFn(async (destinationAddress) => (store.has(destinationAddress) ? structuredClone(store.get(destinationAddress)) : null)),
    writeState: spyFn(async (destinationAddress, state) => {
      store.set(destinationAddress, structuredClone(state));
    }),
  };
}

// A minimal, VALID Skip route fixture shaped like the live-confirmed response cited in
// specs/behavioral-spec.md (Base USDC -> AKT, txs_required=2). amountOutUakt is expressed as the raw
// uakt bigint the pure validateRoute/verifySettlement functions consume.
export function validRouteFixture({ amountOutUakt = 24_650_000n } = {}) {
  return {
    dest_asset_denom: "uakt",
    dest_asset_chain_id: "akashnet-2",
    amount_out: amountOutUakt.toString(),
    txs_required: 2,
  };
}
