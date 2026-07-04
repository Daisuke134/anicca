// Sprint-6 T6 — makeSolanaReader unit tests. @solana/web3.js's Connection is a concrete class, so
// makeSolanaReader accepts an injectable `opts.conn` (duck-typed subset of Connection) for tests;
// production omits it and a real Connection(rpcUrl) is constructed.
const { test } = require("node:test");
const assert = require("node:assert");
const { makeSolanaReader, USDC_MINT_SOLANA } = require("../chain-reader-solana");

const ADDR = "AJ99EemzNHpkdjpMJ9aXfLthvfQYkjSXUjYrQr3853MN";
const SENDER = "2yTcHLZWT5VmMBF2iTAPtyTM3CcT2YW88PQFCt8E2y27";
const SEED_SENDER = "BF9vzj7YdA6nowwZdW65fQSM1vhRN4sntkKTPnnsfRCX";

function fakeConn({ lamports = 0, usdcAtomic = 0, signatures = [], txByS = {}, throwOn = null } = {}) {
  return {
    getBalance: async () => { if (throwOn === "balance") throw new Error("rpc down"); return lamports; },
    getParsedTokenAccountsByOwner: async () => {
      if (throwOn === "usdc") throw new Error("rpc down");
      return { value: usdcAtomic > 0 ? [{ account: { data: { parsed: { info: { mint: USDC_MINT_SOLANA, tokenAmount: { amount: String(usdcAtomic) } } } } } }] : [] };
    },
    getSignaturesForAddress: async () => { if (throwOn === "sigs") throw new Error("rpc down"); return signatures; },
    getParsedTransaction: async (sig) => txByS[sig] ?? null,
  };
}

function fakeTx({ target, targetPre, targetPost, other, otherPre, otherPost, blockTime }) {
  return {
    blockTime,
    transaction: { message: { accountKeys: [{ pubkey: { toBase58: () => other } }, { pubkey: { toBase58: () => target } }] } },
    meta: { preBalances: [otherPre, targetPre], postBalances: [otherPost, targetPost] },
  };
}

test("nativeBalance: lamports / 1e9 = SOL", async () => {
  const reader = await makeSolanaReader([ADDR], { conn: fakeConn({ lamports: 2_500_000_000 }), fetchPrice: async () => 150 });
  assert.strictEqual(Number(reader.nativeBalanceWei(ADDR)) / 1e9, 2.5);
});

test("usdcBalance: parses the SPL token account amount", async () => {
  const reader = await makeSolanaReader([ADDR], { conn: fakeConn({ usdcAtomic: 7_500000 }), fetchPrice: async () => 150 });
  assert.strictEqual(Number(reader.usdcBalanceAtomic(ADDR)), 7_500000);
});

test("ethUsdPrice (SOL-USD here): returns the fetched price", async () => {
  const reader = await makeSolanaReader([ADDR], { conn: fakeConn({}), fetchPrice: async () => 142.5 });
  assert.strictEqual(reader.ethUsdPrice(), 142.5);
});

test("fail-closed: unreachable RPC -> accessor throws (never fabricates a balance)", async () => {
  const reader = await makeSolanaReader([ADDR], { conn: fakeConn({ throwOn: "balance" }), fetchPrice: async () => 150 });
  assert.throws(() => reader.nativeBalanceWei(ADDR));
});

test("fail-closed: price fetch failure -> ethUsdPrice throws (never a fabricated price)", async () => {
  const reader = await makeSolanaReader([ADDR], { conn: fakeConn({}), fetchPrice: async () => { throw new Error("price api down"); } });
  assert.throws(() => reader.ethUsdPrice());
});

test("externalInflowsUsd: sums real inflows (sender = biggest balance decrease), excludes exSet", async () => {
  const now = Math.floor(Date.now() / 1000);
  const sig1 = "sig1", sig2 = "sig2";
  const reader = await makeSolanaReader([ADDR], {
    fetchPrice: async () => 100,
    conn: fakeConn({
      signatures: [{ signature: sig1, blockTime: now }, { signature: sig2, blockTime: now }],
      txByS: {
        // real external inflow: 1 SOL from SENDER (not excluded) -> counts
        [sig1]: fakeTx({ target: ADDR, targetPre: 0, targetPost: 1_000000000, other: SENDER, otherPre: 5_000000000, otherPost: 4_000000000, blockTime: now }),
        // seed inflow: 2 SOL from SEED_SENDER (a configured seed address) -> excluded
        [sig2]: fakeTx({ target: ADDR, targetPre: 1_000000000, targetPost: 3_000000000, other: SEED_SENDER, otherPre: 5_000000000, otherPost: 3_000000000, blockTime: now }),
      },
    }),
  });
  const exSet = new Set([SEED_SENDER]);
  const usd = reader.externalInflowsUsd(ADDR, 0, exSet);
  assert.strictEqual(usd, 100); // only the 1 SOL real inflow * price(100), the seed 2 SOL excluded
});

test("externalInflowsUsd: a tx before sinceTs is not counted", async () => {
  const now = Math.floor(Date.now() / 1000);
  const sig1 = "sig1";
  const reader = await makeSolanaReader([ADDR], {
    fetchPrice: async () => 100,
    conn: fakeConn({
      signatures: [{ signature: sig1, blockTime: now - 1000 }],
      txByS: { [sig1]: fakeTx({ target: ADDR, targetPre: 0, targetPost: 1_000000000, other: SENDER, otherPre: 5_000000000, otherPost: 4_000000000, blockTime: now - 1000 }) },
    }),
  });
  const usd = reader.externalInflowsUsd(ADDR, now, new Set());
  assert.strictEqual(usd, 0);
});
