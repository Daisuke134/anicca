// hl-state.mjs — the ONE place that turns a Hyperliquid clearinghouseState into the two numbers the
// dashboard needs: accountValue (net-worth contribution) and unrealizedPnl (revenue_by_source cell).
// Used by BOTH telemetry-poster (dashboard) and portfolio-realtime (monitor) so they can never drift.
// Pure aggregation is testable with a real fixture; only `hlState` does the fetch.

// @param json the clearinghouseState response object
// @returns { accountValue:number, unrealizedPnl:number } — always finite, never throws
export function aggregateHlState(json) {
  const acct = Number(json?.marginSummary?.accountValue);
  const positions = Array.isArray(json?.assetPositions) ? json.assetPositions : [];
  let upnl = 0;
  for (const p of positions) {
    const v = Number(p?.position?.unrealizedPnl);
    if (Number.isFinite(v)) upnl += v;
  }
  return {
    accountValue: Number.isFinite(acct) ? acct : 0,
    unrealizedPnl: Number.isFinite(upnl) ? upnl : 0,
  };
}

// Effectful: fetch clearinghouseState for a wallet and aggregate. Never throws (→ zeros on failure).
// @param wallet  the agent's address
// @param fetchFn injectable for tests; defaults to global fetch
export async function hlState(wallet, fetchFn = fetch) {
  try {
    const r = await fetchFn("https://api.hyperliquid.xyz/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "clearinghouseState", user: wallet }),
    });
    return aggregateHlState(await r.json());
  } catch {
    return { accountValue: 0, unrealizedPnl: 0 };
  }
}
