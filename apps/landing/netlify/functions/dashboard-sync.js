const { aggregate } = require("./_lib/telemetry-aggregate");
const { enrichOnChain } = require("./_lib/enrich");
const { makeBaseReader, makeSolanaReader, makePolygonReader } = require("./_lib/chain-reader");

// R12: this endpoint MUST NOT serve raw self-reported rankings. It enriches every row on-chain
// (net worth + external earnings, keyed on the wallet `id`, routed per-row by `chain`) BEFORE
// aggregating, so the leaderboard reflects verified figures and self/seed money cannot buy rank.
// `deps.readers` is injectable for tests: { base, solana, polygon }.
async function buildReaders(rows, deps = {}) {
  if (deps.readers) return deps.readers;
  const byChain = { base: [], solana: [], polygon: [] };
  for (const row of rows) {
    // "polygon-proxy" rows deliberately get NO reader (see telemetry-schema.js) — skip them here so
    // we don't waste an RPC read on an address that enrichOnChain will never look up under that key.
    if (row.chain === "polygon-proxy") continue;
    byChain[row.chain === "solana" || row.chain === "polygon" ? row.chain : "base"].push(row.id);
  }
  const [base, solana, polygon] = await Promise.all([
    makeBaseReader(byChain.base),
    makeSolanaReader(byChain.solana),
    makePolygonReader(byChain.polygon),
  ]);
  return { base, solana, polygon };
}

exports.handler = async (event, context, deps = {}) => {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };
  const r = await fetch(`${url}/rest/v1/instances?select=*`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!r.ok) return { statusCode: 502, body: `supabase ${r.status}` };
  const rowsRaw = await r.json();
  const rows = Array.isArray(rowsRaw) ? rowsRaw : [];
  const readers = await buildReaders(rows, deps);
  const enriched = enrichOnChain(rows, readers);
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=15" },
    body: JSON.stringify(aggregate(enriched)),
  };
};
