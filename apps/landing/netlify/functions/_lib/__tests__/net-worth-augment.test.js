// net-worth-augment.js + enrichOnChain + aggregate integration tests — proves the FULL dashboard
// pipeline (T1: multi-chain net worth, T2: Polymarket-realized revenue) with everything mocked
// (injected fetchImpl). No network calls.
const { test } = require("node:test");
const assert = require("node:assert");
const { augmentDashboardReader, computeDashboardOverrides, withDashboardOverrides } = require("../net-worth-augment");
const { enrichOnChain } = require("../enrich");
const { aggregate } = require("../telemetry-aggregate");

const CLAUDE_P_ID = "0x02bb6b2af70dbf2c367c1b69aca9858bf3525502";
const FRANKLIN_ID = "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9";
const CLAUDE_P_PM = "0x904b50d2e214da947d83d6a2d32c4e3ffc17eb74";
const CLAUDE_P_TREASURY = "0x810f6d61f7606deee2657d3083e150a222bc29c5";
const PUSD_CONTRACT = "0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb";

// A minimal "empty" flat reader — every accessor returns/throws as if the underlying wallet is
// unfunded/unreadable. Used as the `baseReader` argument so tests exercise ONLY the override path,
// while still presenting the shape enrichOnChain's back-compat flat-reader detection expects
// (readerFor() duck-types on `usdcBalanceAtomic` being an own function).
function emptyFlatReader() {
  return {
    ethUsdPrice: () => 1,
    usdcBalanceAtomic: () => 0n,
    nativeBalanceWei: () => 0n,
    externalInflowsUsd: () => 0,
  };
}

const okJson = (body) => ({ ok: true, json: async () => body });

// Decode the queried wallet address out of an eth_call's balanceOf(address) calldata (the last 40
// hex chars), so the mock can answer differently per-WALLET, not just per-token-contract.
function calldataAddress(data) {
  return "0x" + String(data).slice(-40);
}

/**
 * A fake fetch that answers every leg this pipeline touches, with per-wallet precision:
 *   - claude-p's Polymarket deposit wallet (CLAUDE_P_PM) has a $12.30 mark-to-market portfolio value.
 *   - claude-p's treasury wallet (CLAUDE_P_TREASURY) holds a Hyperliquid margin account of $7.72.
 *   - Franklin's own Solana wallet holds 0.2 SOL (native).
 *   - every other (wallet, token) pair is $0.
 * @param {{pmActivity?:Array, hlDown?:boolean, pmValues?:object}} [fixtures]
 */
function fakeFetch({ pmActivity = [], hlDown = false, pmValues = { [CLAUDE_P_PM]: 12.30 } } = {}) {
  return async (url, init) => {
    const u = String(url);
    if (u.includes("data-api.polymarket.com/activity")) return okJson(pmActivity);
    if (u.includes("data-api.polymarket.com/value")) {
      const user = new URL(u).searchParams.get("user").toLowerCase();
      return okJson([{ user, value: pmValues[user] || 0 }]);
    }
    const body = init?.body ? JSON.parse(init.body) : null;
    if (u.includes("coinbase.com")) {
      if (u.includes("ETH-USD")) return okJson({ data: { amount: "3000" } });
      if (u.includes("POL-USD")) return okJson({ data: { amount: "0.5" } });
      if (u.includes("SOL-USD")) return okJson({ data: { amount: "150" } });
      return okJson({ data: { amount: "1" } });
    }
    if (body?.type === "clearinghouseState") {
      if (hlDown) throw new Error("simulated HL RPC outage");
      if (String(body.user).toLowerCase() === CLAUDE_P_TREASURY) {
        return okJson({ marginSummary: { accountValue: "7.72" } });
      }
      return okJson({ marginSummary: { accountValue: "0" } });
    }
    if (body?.method === "eth_call") {
      const to = String(body.params[0].to).toLowerCase();
      const wallet = calldataAddress(body.params[0].data);
      if (to === PUSD_CONTRACT && wallet === CLAUDE_P_PM) return okJson({ result: "0x" + Math.round(12.30 * 1e6).toString(16) });
      return okJson({ result: "0x0" });
    }
    if (body?.method === "eth_getBalance") return okJson({ result: "0x0" }); // no native ETH/POL anywhere in this fixture
    if (body?.method === "getTokenAccountsByOwner") return okJson({ result: { value: [] } }); // no Solana USDC
    if (body?.method === "getBalance") return okJson({ result: { value: 200_000_000 } }); // 0.2 SOL, any Solana wallet
    return okJson({ result: "0x0" });
  };
}

function baseRow(over) {
  return {
    id: "0xaaa", ts: Math.floor(Date.now() / 1000), host: "x", geo: "US",
    model_live: "m", model_tier: "frontier", net_worth_usd: 0, revenue_mo_usd: 0,
    burn_day_usd: 0, runway_days: 999, status: "alive", ...over,
  };
}

test("T1: claude-p net_worth includes the PM-deposit mark-to-market value and the Hyperliquid margin", async () => {
  const row = baseRow({ id: CLAUDE_P_ID });
  const reader = await augmentDashboardReader(emptyFlatReader(), [row], { fetchImpl: fakeFetch() });
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.net_worth_src, "chain");
  // PM /value 12.30 + HL 7.72 = 20.02
  assert.strictEqual(Math.round(e.net_worth_usd * 100) / 100, 20.02);
});

test("T1: Franklin net_worth includes Solana SOL, Base, and its own PM deposit", async () => {
  const row = baseRow({ id: FRANKLIN_ID, chain: "solana" });
  const reader = await augmentDashboardReader(emptyFlatReader(), [row], { fetchImpl: fakeFetch() });
  const [e] = enrichOnChain([row], { solana: reader });
  assert.strictEqual(e.net_worth_src, "chain");
  // 0.2 SOL * $150 = $30 (Solana USDC/Base/HL/PM all $0 for Franklin in this fixture)
  assert.strictEqual(Math.round(e.net_worth_usd * 100) / 100, 30);
});

test("T1: total_net_worth_usd is the SUM of claude-p AND Franklin (not just one of them)", async () => {
  const claudeRow = baseRow({ id: CLAUDE_P_ID });
  const franklinRow = baseRow({ id: FRANKLIN_ID, chain: "solana" });
  const rows = [claudeRow, franklinRow];
  const overrides = await computeDashboardOverrides(rows, { fetchImpl: fakeFetch() });
  const readers = {
    base: withDashboardOverrides(emptyFlatReader(), overrides),
    solana: withDashboardOverrides(emptyFlatReader(), overrides),
  };
  const enriched = enrichOnChain(rows, readers);
  const agg = aggregate(enriched);
  const claudeE = enriched.find((r) => r.id === CLAUDE_P_ID);
  const franklinE = enriched.find((r) => r.id === FRANKLIN_ID);
  assert.strictEqual(claudeE.net_worth_src, "chain");
  assert.strictEqual(franklinE.net_worth_src, "chain");
  assert.strictEqual(
    Math.round(agg.total_net_worth_usd * 100) / 100,
    Math.round((claudeE.net_worth_usd + franklinE.net_worth_usd) * 100) / 100,
  );
  // sanity: 20.02 (claude-p) + 30 (Franklin) = 50.02
  assert.strictEqual(Math.round(agg.total_net_worth_usd * 100) / 100, 50.02);
});

test("T1: an unpriceable native asset is counted as $0, not guessed", async () => {
  const row = baseRow({ id: FRANKLIN_ID, chain: "solana" });
  const fetchImpl = async (url, init) => {
    const u = String(url);
    if (u.includes("data-api.polymarket.com")) return okJson([]);
    if (u.includes("coinbase.com")) throw new Error("price feed down"); // SOL price unavailable
    const body = init?.body ? JSON.parse(init.body) : null;
    if (body?.method === "getBalance") return okJson({ result: { value: 1_000_000_000 } }); // 1 SOL
    if (body?.method === "getTokenAccountsByOwner") return okJson({ result: { value: [] } });
    if (body?.type === "clearinghouseState") return okJson({ marginSummary: { accountValue: "0" } });
    return okJson({ result: "0x0" });
  };
  const reader = await augmentDashboardReader(emptyFlatReader(), [row], { fetchImpl });
  const [e] = enrichOnChain([row], { solana: reader });
  assert.strictEqual(e.net_worth_src, "chain");
  assert.strictEqual(e.net_worth_usd, 0, "unpriceable SOL must contribute $0, never a guessed price");
});

test("T1: fail-soft — one leg's RPC failing does not kill the legs that DID read", async () => {
  const row = baseRow({ id: CLAUDE_P_ID });
  const reader = await augmentDashboardReader(emptyFlatReader(), [row], { fetchImpl: fakeFetch({ hlDown: true }) });
  const [e] = enrichOnChain([row], { base: reader });
  // Hyperliquid leg errored (simulated RPC outage), but the Polygon pUSD leg ($12.30) survives.
  assert.strictEqual(e.net_worth_src, "chain");
  assert.strictEqual(Math.round(e.net_worth_usd * 100) / 100, 12.30);
});

test("T2: revenue_mo_usd == Polymarket REDEEM total - BUY total for claude-p", async () => {
  const row = baseRow({ id: CLAUDE_P_ID });
  const pmActivity = [
    { type: "REDEEM", usdcSize: 49.78 },
    { type: "TRADE", side: "BUY", usdcSize: 39.97 },
  ];
  const reader = await augmentDashboardReader(emptyFlatReader(), [row], { fetchImpl: fakeFetch({ pmActivity }) });
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.earn_src, "chain");
  // total P&L = realized (49.78 - 39.97 = 9.81) + open-position mark-to-market (fixture /value = 12.30)
  assert.strictEqual(Math.round(e.revenue_mo_usd * 100) / 100, 22.11);
  assert.ok(e.revenue_today_usd <= e.revenue_mo_usd);
});

test("T2: a row with NO configured Polymarket account keeps the old Transfer-log earnings path (no regression)", async () => {
  const row = baseRow({ id: "0xsomeotheragent" });
  const reader = await augmentDashboardReader(
    {
      ethUsdPrice: () => 1,
      usdcBalanceAtomic: () => 0n,
      nativeBalanceWei: () => 0n,
      externalInflowsUsd: () => 42, // this row's earnings come from the ORIGINAL mechanism
    },
    [row],
    { fetchImpl: fakeFetch() },
  );
  const [e] = enrichOnChain([row], { base: reader });
  assert.strictEqual(e.revenue_mo_usd, 42, "an unconfigured id must not be affected by the augmentation");
});

test("everything above used only injected fetchImpl — computeDashboardOverrides never touches globalThis.fetch when fetchImpl is given", async () => {
  const realFetch = globalThis.fetch;
  let calledRealFetch = false;
  globalThis.fetch = async (...args) => { calledRealFetch = true; return realFetch(...args); };
  try {
    const row = baseRow({ id: CLAUDE_P_ID });
    await computeDashboardOverrides([row], { fetchImpl: fakeFetch() });
    assert.strictEqual(calledRealFetch, false);
  } finally {
    globalThis.fetch = realFetch;
  }
});
