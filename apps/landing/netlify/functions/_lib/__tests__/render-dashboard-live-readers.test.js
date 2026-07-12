// makeLiveReaders() — proves render-dashboard.mjs actually wires a Solana reader (previously NEVER
// used in production, see git blame on chain-reader-solana.js) AND the multi-chain/Polymarket-revenue
// overrides into the {base, solana} map enrichOnChain dispatches on. Everything mocked; no network.
const { test } = require("node:test");
const assert = require("node:assert");
const path = require("node:path");

const SCRIPT = path.resolve(__dirname, "../../../../scripts/render-dashboard.mjs");
const CLAUDE_P_ID = "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502";
const FRANKLIN_ID = "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9";
const PUSD_CONTRACT = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb";
const CLAUDE_P_PM = "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74";

const okJson = (body) => ({ ok: true, json: async () => body });
function calldataAddress(data) { return "0x" + String(data).slice(-40); }

// Fake Solana `Connection` (duck-typed subset chain-reader-solana.js's makeSolanaReader accepts via
// opts.conn) — no real network, matching chain-reader-solana.test.js's own test pattern.
function fakeSolanaConn() {
  return {
    getBalance: async () => 0,
    getParsedTokenAccountsByOwner: async () => ({ value: [] }),
    getSignaturesForAddress: async () => [],
    getParsedTransaction: async () => null,
  };
}

function fakeFetch() {
  return async (url, init) => {
    const u = String(url);
    if (u.includes("data-api.polymarket.com/activity")) {
      return okJson([{ type: "REDEEM", usdcSize: 10 }, { type: "TRADE", side: "BUY", usdcSize: 4 }]);
    }
    if (u.includes("data-api.polymarket.com/value")) {
      const user = new URL(u).searchParams.get("user").toLowerCase();
      return okJson([{ user, value: user === CLAUDE_P_PM ? 5 : 0 }]);
    }
    if (u.includes("coinbase.com")) return okJson({ data: { amount: "150" } });
    const body = init?.body ? JSON.parse(init.body) : null;
    if (body?.type === "clearinghouseState") return okJson({ marginSummary: { accountValue: "0" } });
    if (body?.method === "eth_call") {
      const to = String(body.params[0].to).toLowerCase();
      const wallet = calldataAddress(body.params[0].data);
      if (to === PUSD_CONTRACT && wallet === CLAUDE_P_PM) return okJson({ result: "0x" + (5_000000).toString(16) });
      return okJson({ result: "0x0" });
    }
    if (body?.method === "eth_getBalance") return okJson({ result: "0x0" });
    if (body?.method === "getTokenAccountsByOwner") return okJson({ result: { value: [] } });
    if (body?.method === "getBalance") return okJson({ result: { value: 0 } });
    return okJson({ result: "0x0" });
  };
}

test("makeLiveReaders returns a {base, solana} map, both carrying the same overrides", async () => {
  const { makeLiveReaders } = await import(SCRIPT);
  const rows = [
    { id: CLAUDE_P_ID, chain: "base" },
    { id: FRANKLIN_ID, chain: "solana" },
  ];
  const readers = await makeLiveReaders(rows, {
    fetchImpl: fakeFetch(),
    solanaConn: fakeSolanaConn(),
    solanaFetchPrice: async () => 150,
  });
  assert.strictEqual(typeof readers.base.netWorthUsd, "function");
  assert.strictEqual(typeof readers.solana.netWorthUsd, "function");
  // claude-p's override ($5 pUSD) is visible through EITHER reader (id-keyed, not chain-keyed)
  assert.strictEqual(readers.base.netWorthUsd(CLAUDE_P_ID), 5);
  assert.strictEqual(readers.solana.netWorthUsd(CLAUDE_P_ID), 5);
  // claude-p's Polymarket revenue override: 10 - 4 = 6
  assert.strictEqual(readers.base.revenueMoUsd(CLAUDE_P_ID), 6);
});

test("a solana-chain row is enriched through the solana reader, not silently unverified", async () => {
  const { makeLiveReaders } = await import(SCRIPT);
  const { enrichOnChain } = require(path.resolve(__dirname, "../enrich"));
  const rows = [{ id: FRANKLIN_ID, chain: "solana" }];
  const readers = await makeLiveReaders(rows, {
    fetchImpl: fakeFetch(),
    solanaConn: fakeSolanaConn(),
    solanaFetchPrice: async () => 150,
  });
  const [e] = enrichOnChain(rows, readers);
  assert.strictEqual(e.net_worth_src, "chain", "solana row must be routed to the solana reader, not left unverified");
});
