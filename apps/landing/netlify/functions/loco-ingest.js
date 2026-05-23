// Anicca Alarm — public OwnTracks ingest for subscribers (multi-tenant).
// OwnTracks (HTTP mode) on a subscriber's phone POSTs here:
//   https://aniccaai.com/.netlify/functions/loco-ingest?token=<owntracks_token>
// We look up the subscriber by token and store their latest location into
// Supabase subscriber_profiles. The multi-tenant lateness engine reads it.
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  if (!SUPABASE_URL || !SUPABASE_KEY) return { statusCode: 500, body: "missing config" };

  const token = (event.queryStringParameters || {}).token;
  if (!token) return { statusCode: 401, body: "[]" };

  let m;
  try { m = JSON.parse(event.body || "{}"); } catch { return { statusCode: 200, body: "[]" }; }
  // OwnTracks sends many message types; only persist location fixes.
  if (m._type !== "location" || typeof m.lat !== "number" || typeof m.lon !== "number") {
    return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: "[]" };
  }

  const patch = {
    location_lat: m.lat, location_lon: m.lon,
    location_acc: m.acc ?? null, location_vel: m.vel ?? null,
    location_tst: m.tst || Math.floor(Date.now() / 1000),
    updated_at: new Date().toISOString(),
  };
  try {
    await fetch(`${SUPABASE_URL}/rest/v1/subscriber_profiles?owntracks_token=eq.${encodeURIComponent(token)}`, {
      method: "PATCH",
      headers: {
        apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`,
        "Content-Type": "application/json", Prefer: "return=minimal",
      },
      body: JSON.stringify(patch),
    });
  } catch (e) {
    return { statusCode: 500, body: "[]" };
  }
  // OwnTracks expects a JSON array response.
  return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: "[]" };
};
