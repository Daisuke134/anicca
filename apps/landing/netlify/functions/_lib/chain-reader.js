// Live multi-chain readers for enrichOnChain. Pre-fetches balances + inflow logs + native-token price so
// that enrichOnChain stays a synchronous pure function; ALL async chain I/O is isolated here. If a chain
// is unconfigured (no RPC URL) or a read fails, the corresponding accessor THROWS → enrich flags that
// figure `unverified` (never a trusted/fake number). PUBLIC data only, no private keys.
const { JsonRpcProvider, Contract, formatUnits } = require("ethers");

const ERC20 = [
  "function balanceOf(address) view returns (uint256)",
  "event Transfer(address indexed from, address indexed to, uint256 value)",
];
// ~30 days of blocks at ~2s/block (Base and Polygon are both ~2s). USDC/pUSD inflow window
// (approximate; precise ts-cut is a follow-up, same limitation as the original Base-only reader).
const LOOKBACK_BLOCKS = 1_200_000;

const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC (6 decimals)
const POLYGON_PUSD = "0xC011a7E12a19f7B1f670d46F03B03f3342E82DFB"; // Polygon pUSD (6 decimals)

// Generic EVM reader factory — Base and Polygon are both plain EVM chains (secp256k1/EIP-191), only the
// RPC endpoint, stablecoin address, and native-token price feed differ. Shared here so a fix to one
// (e.g. the inflow-window heuristic) doesn't have to be duplicated per chain.
async function makeEvmReader(ids, { rpcUrl, tokenAddress, priceUrl, priceKey }) {
  const cache = { usdc: {}, native: {}, inflows: {} };
  let price = null;
  if (rpcUrl && ids.length) {
    const provider = new JsonRpcProvider(rpcUrl);
    const token = new Contract(tokenAddress, ERC20, provider);
    try {
      const res = await fetch(priceUrl);
      const j = await res.json();
      price = Number(j?.data?.amount) || null;
    } catch { /* price stays null → nativePrice throws → net worth unverified if native balance > 0 */ }
    let latest = 0;
    try { latest = await provider.getBlockNumber(); } catch {}
    for (const id of ids) {
      const k = String(id).toLowerCase();
      try { cache.usdc[k] = await token.balanceOf(id); } catch {}
      try { cache.native[k] = await provider.getBalance(id); } catch {}
      if (latest) {
        try {
          const logs = await token.queryFilter(token.filters.Transfer(null, id), latest - LOOKBACK_BLOCKS, latest);
          cache.inflows[k] = logs.map((l) => ({ from: String(l.args.from || "").toLowerCase(), usd: Number(formatUnits(l.args.value, 6)) }));
        } catch { /* leave undefined → externalInflowsUsd throws → earn unverified */ }
      }
    }
  }
  const norm = (a) => String(a).toLowerCase();
  return {
    ethUsdPrice: () => { if (price == null) throw new Error(`no ${priceKey} price`); return price; },
    usdcBalanceAtomic: (a) => { const v = cache.usdc[norm(a)]; if (v == null) throw new Error("no stablecoin balance"); return v; },
    nativeBalanceWei: (a) => { const v = cache.native[norm(a)]; if (v == null) throw new Error("no native balance"); return v; },
    externalInflowsUsd: (a, _sinceTs, exSet) => {
      const list = cache.inflows[norm(a)];
      if (list == null) throw new Error("no inflow data");
      return list.filter((x) => !exSet.has(x.from)).reduce((s, x) => s + x.usd, 0);
    },
  };
}

async function makeBaseReader(ids = [], opts = {}) {
  return makeEvmReader(ids, {
    // Falls back to a public RPC (same pattern as Polygon/Solana below) — BASE_RPC_URL was never
    // configured on the Netlify site (2026-07-05 finding: this is why every row, including
    // anicca-a3cdd4, showed net_worth_src=null even before this multi-chain PR existed — there was
    // simply no RPC target, not a code bug). Still overridable via env for a dedicated/paid RPC.
    rpcUrl: opts.rpcUrl || process.env.BASE_RPC_URL || "https://base-rpc.publicnode.com",
    tokenAddress: BASE_USDC,
    priceUrl: "https://api.coinbase.com/v2/prices/ETH-USD/spot",
    priceKey: "ETH",
  });
}

// Polygon reader for claude-p's dedicated telemetry-signing identity (holds pUSD only — the funded
// Polymarket proxy's balance is read separately via the same public RPC in the poster; this reader
// verifies whatever the SIGNING identity itself holds, which mirrors anicca-a3cdd4's own pattern of
// "wallet.json signs, net worth computed independently"). Native MATIC is not counted (gas dust only,
// never material) — nativeBalanceWei always reports 0 so it can never corrupt the USD total.
async function makePolygonReader(ids = [], opts = {}) {
  const r = await makeEvmReader(ids, {
    rpcUrl: opts.rpcUrl || process.env.POLYGON_RPC_URL || "https://polygon-bor-rpc.publicnode.com",
    tokenAddress: POLYGON_PUSD,
    priceUrl: "https://api.coinbase.com/v2/prices/MATIC-USD/spot",
    priceKey: "MATIC",
  });
  return { ...r, nativeBalanceWei: () => 0n, ethUsdPrice: () => 0 };
}

// Solana reader — genuinely different chain (no ethers/EVM), raw JSON-RPC. Native decimals = 9 (SOL),
// NOT 18 — enrichOnChain reads `nativeDecimals()` when present instead of hardcoding 18, so this reader
// declares its own. externalInflowsUsd is NOT implemented (Solana inflow-history tracking via bare
// getSignaturesForAddress/parsed-instruction inspection is a much larger, separate undertaking than a
// Transfer event-log query) — it always throws, so earn_src stays "unverified" for Solana rows even
// though net_worth_src can be "chain". Honest partial verification, not silently faked.
const SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";

async function makeSolanaReader(ids = [], opts = {}) {
  const rpcUrl = opts.rpcUrl || process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com";
  const cache = { sol: {}, usdc: {} };
  let price = null;
  if (ids.length) {
    async function rpc(method, params) {
      const r = await fetch(rpcUrl, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }) });
      return (await r.json()).result;
    }
    try {
      const res = await fetch("https://api.coinbase.com/v2/prices/SOL-USD/spot");
      const j = await res.json();
      price = Number(j?.data?.amount) || null;
    } catch { /* price stays null → nativePrice throws → unverified */ }
    for (const id of ids) {
      try { const b = await rpc("getBalance", [id]); cache.sol[id] = BigInt(b?.value ?? 0); } catch {}
      try {
        const r = await rpc("getTokenAccountsByOwner", [id, { mint: SOL_USDC_MINT }, { encoding: "jsonParsed" }]);
        const list = r?.value || [];
        const total = list.reduce((s, a) => s + (Number(a.account?.data?.parsed?.info?.tokenAmount?.amount) || 0), 0);
        cache.usdc[id] = BigInt(Math.round(total));
      } catch {}
    }
  }
  return {
    ethUsdPrice: () => { if (price == null) throw new Error("no SOL price"); return price; },
    usdcBalanceAtomic: (a) => { const v = cache.usdc[a]; if (v == null) throw new Error("no usdc balance"); return v; },
    nativeBalanceWei: (a) => { const v = cache.sol[a]; if (v == null) throw new Error("no sol balance"); return v; },
    nativeDecimals: () => 9,
    externalInflowsUsd: () => { throw new Error("solana inflow tracking not implemented"); },
  };
}

module.exports = { makeBaseReader, makePolygonReader, makeSolanaReader, BASE_USDC, POLYGON_PUSD };
