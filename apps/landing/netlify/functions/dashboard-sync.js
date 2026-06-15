const { aggregate } = require("./_lib/telemetry-aggregate");

exports.handler = async () => {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };
  const r = await fetch(`${url}/rest/v1/instances?select=*`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!r.ok) return { statusCode: 502, body: `supabase ${r.status}` };
  const rows = await r.json();
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=15" },
    body: JSON.stringify(aggregate(Array.isArray(rows) ? rows : [])),
  };
};
