#!/usr/bin/env node
// portfolio-realtime.mjs — the REAL-TIME, NO-FAKE truth of whether anicca is earning. Unlike the
// ledger-based net-positive monitor (which only sees recorded earn_usdc), this queries the LIVE chain
// every run: wallet USDC, Aave aUSDC (yield principal+interest), and the Hyperliquid account value.
// It compares total portfolio value to the capital invested and prints a real-time verdict. A loop
// (launchd / cron) runs this on a cadence → a genuine real-time earnings feed, not a 16-day-stale page.
//
// Usage: node portfolio-realtime.mjs  → one JSON line to stdout (append to EARN_STATE feed by the loop).
const WALLET = process.env.ANICCA_WALLET_ADDRESS || '0xB9dd3B67921B354c656523d6851537988F31DD56';
const INVESTED_USD = Number(process.env.ANICCA_INVESTED_USD || 18.7); // Dais's capital in (SOL→Base relay)
const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const AUSDC = '0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB'; // Aave v3 Base aUSDC
const RPCS = ['https://base-rpc.publicnode.com', 'https://base.drpc.org', 'https://1rpc.io/base', 'https://base.llamarpc.com'];

async function call(to, data) {
  for (const url of RPCS) {
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_call', params: [{ to, data }, 'latest'] }) });
      const j = await r.json();
      if (j.result && j.result !== '0x') return BigInt(j.result);
    } catch { /* next rpc */ }
  }
  return null;
}

async function hlValue() {
  try {
    const r = await fetch('https://api.hyperliquid.xyz/info', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'clearinghouseState', user: WALLET }) });
    const j = await r.json();
    return Number(j?.marginSummary?.accountValue || 0);
  } catch { return 0; }
}

const bal = (sel) => `0x70a08231000000000000000000000000${WALLET.slice(2).toLowerCase()}`;
const [liqRaw, aaveRaw, hl] = await Promise.all([call(USDC, bal()), call(AUSDC, bal()), hlValue()]);
const liquid = Number(liqRaw || 0n) / 1e6;
const aave = Number(aaveRaw || 0n) / 1e6;
const total = liquid + aave + hl;
const net = total - INVESTED_USD;

const out = {
  ts: Math.floor(Date.now() / 1000),
  wallet: WALLET,
  live: { liquid_usdc: +liquid.toFixed(4), aave_ausdc: +aave.toFixed(4), hl_account: +hl.toFixed(4) },
  total_value_usd: +total.toFixed(4),
  invested_usd: INVESTED_USD,
  net_vs_invested_usd: +net.toFixed(4),
  net_positive: net > 0,
  verdict: net > 0
    ? `NET POSITIVE: $${total.toFixed(2)} vs $${INVESTED_USD} invested (+$${net.toFixed(2)})`
    : `not yet: $${total.toFixed(2)} vs $${INVESTED_USD} invested ($${net.toFixed(2)})`,
};
console.log(JSON.stringify(out));
process.exit(net > 0 ? 0 : 1);
