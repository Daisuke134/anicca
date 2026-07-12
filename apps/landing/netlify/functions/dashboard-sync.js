const { aggregate } = require("./_lib/telemetry-aggregate");
const { enrichOnChain } = require("./_lib/enrich");
const { makeBaseReader } = require("./_lib/chain-reader");
const { computeDashboardOverrides, withDashboardOverrides } = require("./_lib/net-worth-augment");

// R12: this endpoint MUST NOT serve raw self-reported rankings. It enriches every row on-chain
// (net worth + external earnings, keyed on the wallet `id`) BEFORE aggregating, so the leaderboard
// reflects verified figures and self/seed money cannot buy rank. `deps.reader` is injectable for tests
// (when supplied it is used AS-IS, no augmentation — every existing test keeps its exact contract).
exports.handler = async (event, context, deps = {}) => {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };
  const r = await fetch(`${url}/rest/v1/instances?select=*`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!r.ok) return { statusCode: 502, body: `supabase ${r.status}` };
  const rowsRaw = await r.json();
  const rows = Array.isArray(rowsRaw) ? rowsRaw : [];
  let reader = deps.reader;
  if (!reader) {
    const baseReader = await makeBaseReader(rows.map((row) => row.id));
    // Same multi-chain/Polymarket-revenue overrides as render-dashboard.mjs (net-worth-augment.js) —
    // known ids (claude-p, Franklin) get their FULL net worth / realized revenue; every other row is
    // untouched. A failure here degrades to "no overrides", never to a broken leaderboard.
    let overrides;
    try {
      overrides = await computeDashboardOverrides(rows);
    } catch {
      overrides = { netWorthUsd: () => undefined, revenueMoUsd: () => undefined, revenueTodayUsd: () => undefined, errors: [] };
    }
    reader = withDashboardOverrides(baseReader, overrides);
  }
  const enriched = enrichOnChain(rows, reader);
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=15" },
    body: JSON.stringify(aggregate(enriched)),
  };
};
