// store-metrics.mjs — pure aggregation for store-review.mjs's `review` action (SELF-STORE-1).
// Factored out of the CLI script so it's unit-testable without touching disk/network: the model
// asks "what actually sold, and was any of it a REAL (external) buyer?" and this is the one place
// that answers it from raw sales/attempts rows.
//
// selfSet MUST be the same wallet set verify-inflow.mjs uses (lib/self-wallets.mjs) — a payer
// address in that set is us paying ourselves in a self-probe, never revenue (INV-7).

function priceUsd(price) {
  const n = Number(String(price || "").replace(/^\$/, ""));
  return Number.isFinite(n) ? n : 0;
}

function round6(n) {
  return Math.round(n * 1e6) / 1e6;
}

/**
 * @param {Array<{ts:string,route:string,price:string,payer:string|null,settled:boolean}>} rows
 *   sales-<payTo>.jsonl rows (settled attempts; may also include unsettled rows — filtered here).
 * @param {Array<{ts:string,route:string,price:string,payer:string|null,settled:boolean}>} attempts
 *   attempts-<payTo>.jsonl rows (every 402 challenge issued, settled or not).
 * @param {Set<string>} selfSet lowercased wallet addresses the colony itself controls.
 * @param {number} now ms epoch, injectable for tests.
 */
export function aggregateStore(rows, attempts, selfSet, now = Date.now()) {
  const sales = (rows || []).filter((r) => r && r.settled);
  const isExternal = (r) => !selfSet.has(String(r.payer || "").toLowerCase());
  const external = sales.filter(isExternal);

  const routeCounts = new Map();
  for (const r of sales) routeCounts.set(r.route, (routeCounts.get(r.route) || 0) + 1);
  const topRoutes = [...routeCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([route, count]) => ({ route, count }));

  const dayAgo = now - 24 * 60 * 60 * 1000;
  const attempts24h = (attempts || []).filter((a) => a && Date.parse(a.ts || "") >= dayAgo).length;

  const lastSaleTs = sales.length
    ? sales.map((r) => r.ts).sort().at(-1)
    : null;

  return {
    settledCount: sales.length,
    settledUsd: round6(sales.reduce((s, r) => s + priceUsd(r.price), 0)),
    externalCount: external.length,
    externalUsd: round6(external.reduce((s, r) => s + priceUsd(r.price), 0)),
    topRoutes,
    attempts24h,
    lastSaleTs,
    verdict: external.length > 0 ? "external sales present" : "no external sales yet — demand problem",
  };
}
