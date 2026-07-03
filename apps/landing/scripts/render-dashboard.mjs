// Sprint-2 S11: Dais-owned render script.
// Runs enrichOnChain + aggregate over raw Supabase rows and merges the enriched leaderboard[]
// into the served apps/landing/public/dashboard.json without dropping existing top-level keys
// (mrr, goals, followers, lineage, ...).
//
// Anicca instances NEVER write this file directly (aniccaai.com write-guardrail); this script
// is intended to run under Dais-owned ops (GitHub Actions / cron / manual) and commit the diff.
import { createRequire } from "node:module";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { enrichOnChain } = require("../netlify/functions/_lib/enrich");
const { aggregate } = require("../netlify/functions/_lib/telemetry-aggregate");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_DASHBOARD_PATH = path.resolve(__dirname, "../public/dashboard.json");
const USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const LOOKBACK_BLOCKS = 1_200_000; // ~30 days on Base @ 2s/block

// Merge additively: preserve every existing key, overwrite `leaderboard` + tracking metrics
// with the enriched output. Empty rows => leaderboard = [] (no fake placeholders).
export function mergeIntoExisting(existing, agg) {
  return {
    ...existing,
    updated_at: agg.updated_at,
    leaderboard: agg.leaderboard,
    total_net_worth_usd: agg.total_net_worth_usd,
    earned_mo_usd: agg.earned_mo_usd,
    alive: agg.alive,
    self_funded_pct: agg.self_funded_pct,
    frontier_pct: agg.frontier_pct,
  };
}

export async function renderDashboard({ rows = [], reader, existing = {} }) {
  const enriched = enrichOnChain(rows, reader);
  const agg = aggregate(enriched);
  return mergeIntoExisting(existing, agg);
}

// Live production reader — same shape enrichOnChain expects. Pre-fetches balances + inflow logs
// so enrich stays synchronous. Any missing datum ⇒ the corresponding accessor throws ⇒ enrich
// marks that figure `unverified` (never fabricated).
export async function makeLiveReader(rows, { rpcUrl } = {}) {
  if (!rpcUrl) return unverifiedReader();
  let ethers;
  try { ethers = await import("ethers"); } catch { return unverifiedReader(); }
  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const usdc = new ethers.Contract(
    USDC_BASE_MAINNET,
    [
      "function balanceOf(address) view returns (uint256)",
      "event Transfer(address indexed from, address indexed to, uint256 value)",
    ],
    provider,
  );
  let price = null;
  try {
    const r = await fetch("https://api.coinbase.com/v2/prices/ETH-USD/spot");
    const j = await r.json();
    price = Number(j?.data?.amount) || null;
  } catch { /* price stays null → ethUsdPrice() throws → net worth unverified */ }
  let latest = 0;
  try { latest = await provider.getBlockNumber(); } catch { /* leave 0 → inflows unavailable */ }
  const cache = { usdc: {}, native: {}, inflows: {} };
  for (const row of rows) {
    const k = String(row.id).toLowerCase();
    try { cache.usdc[k] = await usdc.balanceOf(row.id); } catch { /* unverified */ }
    try { cache.native[k] = await provider.getBalance(row.id); } catch { /* unverified */ }
    if (latest) {
      try {
        const logs = await usdc.queryFilter(usdc.filters.Transfer(null, row.id), latest - LOOKBACK_BLOCKS, latest);
        cache.inflows[k] = logs.map((l) => ({ from: String(l.args.from || "").toLowerCase(), usd: Number(ethers.formatUnits(l.args.value, 6)) }));
      } catch { /* unverified */ }
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

function unverifiedReader() {
  const boom = (msg) => () => { throw new Error(msg); };
  return {
    ethUsdPrice: boom("no ETH price (no rpc)"),
    usdcBalanceAtomic: boom("no usdc balance (no rpc)"),
    nativeBalanceWei: boom("no native balance (no rpc)"),
    externalInflowsUsd: boom("no inflow data (no rpc)"),
  };
}

// CLI entrypoint (invoked by Dais-owned ops). Skipped when imported.
if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}

async function main() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const dashboardPath = process.env.DASHBOARD_JSON_PATH || DEFAULT_DASHBOARD_PATH;
  const rpcUrl = process.env.BASE_RPC_URL;
  if (!url || !key) {
    console.error("[render-dashboard] SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required");
    process.exit(2);
  }
  const r = await fetch(`${url}/rest/v1/instances?select=*`, { headers: { apikey: key, Authorization: `Bearer ${key}` } });
  if (!r.ok) {
    console.error(`[render-dashboard] supabase ${r.status}: ${await r.text()}`);
    process.exit(2);
  }
  const rows = await r.json();
  const reader = await makeLiveReader(Array.isArray(rows) ? rows : [], { rpcUrl });
  let existing = {};
  try { existing = JSON.parse(await fs.readFile(dashboardPath, "utf8")); } catch { /* new file */ }
  const next = await renderDashboard({ rows: Array.isArray(rows) ? rows : [], reader, existing });
  await fs.writeFile(dashboardPath, JSON.stringify(next, null, 2) + "\n");
  console.log(`[render-dashboard] wrote ${dashboardPath} (leaderboard rows: ${(next.leaderboard || []).length})`);
}
