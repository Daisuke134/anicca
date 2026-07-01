const { aggregate } = require("./_lib/telemetry-aggregate");
const { enrichOnChain } = require("./_lib/enrich");
const { makeBaseReader } = require("./_lib/chain-reader");

// R12: this endpoint MUST NOT serve raw self-reported rankings. It enriches every row on-chain
// (net worth + external earnings, keyed on the wallet `id`) BEFORE aggregating, so the leaderboard
// reflects verified figures and self/seed money cannot buy rank. `deps.reader` is injectable for tests.
exports.handler = async (event, context, deps = {}) => {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };
  const r = await fetch(`${url}/rest/v1/instances?select=*`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!r.ok) return { statusCode: 502, body: `supabase ${r.status}` };
  const rowsRaw = await r.json();
  const rows = Array.isArray(rowsRaw) ? rowsRaw : [];
  const reader = deps.reader || (await makeBaseReader(rows.map((row) => row.id)));
  const enriched = enrichOnChain(rows, reader);
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=15" },
    body: JSON.stringify(aggregate(enriched)),
  };
};
