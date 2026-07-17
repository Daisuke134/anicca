// Supabase via REST (PostgREST) for the spawn webhook: owners table + spawn_events idempotency ledger.
// Same injectable-fetch + headers pattern as telemetry-store.js. `f` defaults to the platform fetch.
function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
}

// --- idempotency ledger (spawn_events) ---
async function isEventSeen(event_id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/spawn_events?event_id=eq.${encodeURIComponent(event_id)}&select=event_id`, {
    headers: headers(key),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
  const rows = await r.json();
  return Array.isArray(rows) && rows.length > 0;
}

async function markEventSeen(event_id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/spawn_events?on_conflict=event_id`, {
    method: "POST",
    headers: { ...headers(key), Prefer: "resolution=ignore-duplicates,return=minimal" },
    body: JSON.stringify({ event_id, seen_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

// --- owners table ---
async function upsertOwner({ email, droplet_id, sub_id, status }, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/owners?on_conflict=sub_id`, {
    method: "POST",
    headers: { ...headers(key), Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify({ sub_id, email, droplet_id, status, updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

async function getOwnerBySub(sub_id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}&select=sub_id,email,droplet_id,status`, {
    headers: headers(key),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
  const rows = await r.json();
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

async function markDestroyed(sub_id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
    method: "PATCH",
    headers: { ...headers(key), Prefer: "return=minimal" },
    body: JSON.stringify({ status: "destroyed", updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

// Mark an owner self-funded: its instance earns enough, the subscription is cancelled, but the
// droplet KEEPS RUNNING (the destroy-on-deleted webhook checks this status and skips destroy).
async function markSelfFunded(sub_id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
    method: "PATCH",
    headers: { ...headers(key), Prefer: "return=minimal" },
    body: JSON.stringify({ status: "self_funded", updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

module.exports = { isEventSeen, markEventSeen, upsertOwner, getOwnerBySub, markDestroyed, markSelfFunded };
