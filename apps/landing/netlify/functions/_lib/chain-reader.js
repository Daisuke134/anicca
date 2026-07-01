// Live Base-mainnet reader for enrichOnChain. Pre-fetches balances + USDC inflow logs + ETH price so
// that enrichOnChain stays a synchronous pure function; ALL async chain I/O is isolated here.
// If unconfigured (no BASE_RPC_URL) or a read fails, the corresponding accessor THROWS → enrich flags
// that figure `unverified` (never a trusted/fake number). PUBLIC data only.
const { JsonRpcProvider, Contract, formatUnits } = require("ethers");

const USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"; // Base USDC (6 decimals)
const ERC20 = [
  "function balanceOf(address) view returns (uint256)",
  "event Transfer(address indexed from, address indexed to, uint256 value)",
];
// ~30 days of Base blocks (~2s/block). USDC inflow window (approximate; precise ts-cut is a follow-up).
const LOOKBACK_BLOCKS = 1_200_000;

async function makeBaseReader(ids = [], opts = {}) {
  const rpc = opts.rpcUrl || process.env.BASE_RPC_URL;
  const cache = { usdc: {}, native: {}, inflows: {} };
  let price = null;
  if (rpc && ids.length) {
    const provider = new JsonRpcProvider(rpc);
    const usdc = new Contract(USDC, ERC20, provider);
    try {
      const res = await fetch("https://api.coinbase.com/v2/prices/ETH-USD/spot");
      const j = await res.json();
      price = Number(j?.data?.amount) || null;
    } catch { /* price stays null → ethUsdPrice throws → net worth unverified */ }
    let latest = 0;
    try { latest = await provider.getBlockNumber(); } catch {}
    for (const id of ids) {
      const k = String(id).toLowerCase();
      try { cache.usdc[k] = await usdc.balanceOf(id); } catch {}
      try { cache.native[k] = await provider.getBalance(id); } catch {}
      if (latest) {
        try {
          const logs = await usdc.queryFilter(usdc.filters.Transfer(null, id), latest - LOOKBACK_BLOCKS, latest);
          cache.inflows[k] = logs.map((l) => ({ from: String(l.args.from || "").toLowerCase(), usd: Number(formatUnits(l.args.value, 6)) }));
        } catch { /* leave undefined → externalInflowsUsd throws → earn unverified */ }
      }
    }
  }
  const norm = (a) => String(a).toLowerCase();
  return {
    ethUsdPrice: () => { if (price == null) throw new Error("no ETH price"); return price; },
    usdcBalanceAtomic: (a) => { const v = cache.usdc[norm(a)]; if (v == null) throw new Error("no usdc balance"); return v; },
    nativeBalanceWei: (a) => { const v = cache.native[norm(a)]; if (v == null) throw new Error("no native balance"); return v; },
    externalInflowsUsd: (a, _sinceTs, exSet) => {
      const list = cache.inflows[norm(a)];
      if (list == null) throw new Error("no inflow data");
      return list.filter((x) => !exSet.has(x.from)).reduce((s, x) => s + x.usd, 0);
    },
  };
}

module.exports = { makeBaseReader, USDC };
