// net-worth-lib.js unit tests — ported from ~/anicca/skills/earn/lib/__tests__/net-worth.test.mjs
// (20 tests green there against real wallets). No network: every RPC + spot-price call goes through
// an injected fake fetch.
const { test } = require("node:test");
const assert = require("node:assert");
const { fetchNetWorth, hexToUnits, balanceOfCalldata, EVM_TOKENS, SOLANA_USDC_MINT } = require("../net-worth-lib");

const ok = (obj) => ({ ok: true, json: async () => obj });

function fakeFetch(handler) {
  const calls = [];
  const f = async (url, init) => {
    const body = init?.body ? JSON.parse(init.body) : null;
    calls.push({ url, method: body?.method, params: body?.params, type: body?.type });
    return handler(url, body, calls);
  };
  f.calls = calls;
  return f;
}

test("hexToUnits: 6-decimal token", () => {
  assert.strictEqual(hexToUnits("0x" + (14148061).toString(16), 6), 14.148061);
});

test("hexToUnits: empty / 0x / null -> 0 (unfunded ERC-20 read, not a crash)", () => {
  assert.strictEqual(hexToUnits("0x", 6), 0);
  assert.strictEqual(hexToUnits(null, 6), 0);
  assert.strictEqual(hexToUnits(undefined, 6), 0);
});

test("balanceOfCalldata: selector + 32-byte left-padded address, lowercased", () => {
  const d = balanceOfCalldata("0x810F6D61F7606dEEE2657d3083E150a222Bc29C5");
  assert.strictEqual(d, "0x70a08231" + "0".repeat(24) + "810f6d61f7606deee2657d3083e150a222bc29c5");
});

test("balanceOfCalldata: rejects a non-EVM address instead of silently querying garbage", () => {
  assert.throws(() => balanceOfCalldata("8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9"), /not an EVM address/);
});

test("T1: counts the Polymarket deposit wallet pUSD a Base-only reader could not see", async () => {
  const f = fakeFetch(async (url, body) => {
    if (url.includes("polygon")) {
      const to = body.params[0].to.toLowerCase();
      if (to === EVM_TOKENS.polygon.find((x) => x.symbol === "pUSD").address.toLowerCase()) {
        return ok({ result: "0x" + (14148061).toString(16) });
      }
      return ok({ result: "0x0" });
    }
    return ok({ result: "0x0" });
  });
  const r = await fetchNetWorth(
    [{ chain: "polygon", address: "0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74", label: "pm-deposit" }],
    { fetchImpl: f, includeNative: false },
  );
  assert.strictEqual(r.total_usd, 14.148061);
  assert.strictEqual(r.holdings[0].symbol, "pUSD");
  assert.deepStrictEqual(r.errors, []);
});

test("T1: counts Solana SOL as well as USDC", async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === "getTokenAccountsByOwner") {
      assert.strictEqual(body.params[1].mint, SOLANA_USDC_MINT);
      return ok({ result: { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: 26.34 } } } } } }] } });
    }
    if (body?.method === "getBalance") return ok({ result: { value: 205_000_000 } });
    if (String(url).includes("SOL-USD")) return ok({ data: { amount: "76.9" } });
    return ok({ result: null });
  });
  const r = await fetchNetWorth([{ chain: "solana", address: "8Fpqd", label: "franklin" }], { fetchImpl: f });
  const sol = r.holdings.find((h) => h.symbol === "SOL");
  const usdc = r.holdings.find((h) => h.symbol === "USDC");
  assert.strictEqual(usdc.usd, 26.34);
  assert.strictEqual(sol.priced, true);
  assert.strictEqual(Math.round(r.total_usd * 100) / 100, 42.1);
});

test("T1: aggregates across chains AND wallets into one number", async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === "getTokenAccountsByOwner") {
      return ok({ result: { value: [{ account: { data: { parsed: { info: { tokenAmount: { uiAmount: 10 } } } } } }] } });
    }
    if (body?.method === "eth_call") return ok({ result: "0x" + (5_000_000).toString(16) });
    return ok({ result: null });
  });
  const r = await fetchNetWorth([
    { chain: "base", address: "0x810f6d61f7606deee2657d3083e150a222bc29c5", label: "evm" },
    { chain: "polygon", address: "0x810f6d61f7606deee2657d3083e150a222bc29c5", label: "evm" },
    { chain: "solana", address: "8Fpqd", label: "sol" },
  ], { fetchImpl: f, includeNative: false });
  assert.strictEqual(r.total_usd, 30);
  assert.strictEqual(r.holdings.length, 5);
});

test("fail-soft: a failing RPC degrades ONE leg to an error, others survive", async () => {
  const f = fakeFetch(async (url, body) => {
    if (url.includes("polygon")) return ok({ error: { message: "rpc exploded" } });
    if (body?.method === "eth_call") return ok({ result: "0x" + (7_000_000).toString(16) });
    return ok({ result: null });
  });
  const r = await fetchNetWorth([
    { chain: "base", address: "0x810f6d61f7606deee2657d3083e150a222bc29c5" },
    { chain: "polygon", address: "0x810f6d61f7606deee2657d3083e150a222bc29c5" },
  ], { fetchImpl: f, includeNative: false });
  assert.strictEqual(r.total_usd, 7); // the Base leg survived
  assert.strictEqual(r.errors.length, 3); // all 3 Polygon tokens errored
});

test("T1: an unpriceable native asset counts as $0 and is flagged — never guessed", async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.method === "getBalance") return ok({ result: { value: 1_000_000_000 } });
    if (body?.method === "getTokenAccountsByOwner") return ok({ result: { value: [] } });
    if (String(url).includes("SOL-USD")) throw new Error("price feed down");
    return ok({ result: null });
  });
  const r = await fetchNetWorth([{ chain: "solana", address: "8Fpqd" }], { fetchImpl: f });
  const sol = r.holdings.find((h) => h.symbol === "SOL");
  assert.strictEqual(sol.amount, 1);
  assert.strictEqual(sol.usd, 0, "unpriceable asset must contribute 0, not a guess");
  assert.strictEqual(sol.priced, false);
  assert.strictEqual(r.total_usd, 0);
});

test("counts a Hyperliquid margin account — money no chain reader can see", async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.type === "clearinghouseState") {
      return ok({ marginSummary: { accountValue: "7.720186" } });
    }
    return ok({ result: "0x0" });
  });
  const r = await fetchNetWorth(
    [{ chain: "hyperliquid", address: "0x810f6d61f7606deee2657d3083e150a222bc29c5", label: "HL" }],
    { fetchImpl: f },
  );
  assert.strictEqual(r.total_usd, 7.720186);
  assert.strictEqual(r.holdings[0].chain, "hyperliquid");
});

test("a Hyperliquid account that never deposited contributes 0, not NaN", async () => {
  const f = fakeFetch(async (url, body) => {
    if (body?.type === "clearinghouseState") return ok({ marginSummary: { accountValue: "0.0" } });
    return ok({ result: "0x0" });
  });
  const r = await fetchNetWorth([{ chain: "hyperliquid", address: "0xdead" }], { fetchImpl: f });
  assert.strictEqual(r.total_usd, 0);
  assert.deepStrictEqual(r.holdings, []);
});
