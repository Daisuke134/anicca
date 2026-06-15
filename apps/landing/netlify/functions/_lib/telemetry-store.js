// Supabase via REST (PostgREST) — same pattern as netlify/functions/stripe-fashion-webhook.js.
// `f` is injectable for tests; defaults to the platform fetch (Node 20 global).
function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
}

async function getLastTs(id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/instances?id=eq.${id.toLowerCase()}&select=ts`, { headers: headers(key) });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
  const rows = await r.json();
  return Array.isArray(rows) && rows[0] ? rows[0].ts : 0;
}

async function upsertInstance(p, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/instances?on_conflict=id`, {
    method: "POST",
    headers: { ...headers(key), Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify({ ...p, id: p.id.toLowerCase(), updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

module.exports = { getLastTs, upsertInstance };
