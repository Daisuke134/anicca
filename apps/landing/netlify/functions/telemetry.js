const { verifyTelemetry } = require("./_lib/telemetry-verify");
const { getLastTs, upsertInstance } = require("./_lib/telemetry-store");
const { BASE_ID_RE, SOLANA_ID_RE } = require("./_lib/telemetry-schema");
const { expectedHost } = require("./_lib/fixed-identities");

// 400-class (caller error) vs 401-class (auth/replay). The handler NEVER re-serializes the payload —
// verifyTelemetry reads the verbatim signed `message` (round-3 signing-bytes contract).
const BAD_REQUEST = new Set(["bad_json", "schema", "host_wallet_mismatch"]);

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };

  let body;
  try { body = JSON.parse(event.body || ""); } catch { return { statusCode: 400, body: "bad_json" }; }
  const message = body.message, signature = body.signature;
  if (typeof message !== "string" || typeof signature !== "string") {
    return { statusCode: 400, body: "bad_request" };
  }
  // extract id (for the per-id monotonic lookup) without trusting it — verify binds it to the bytes.
  // Validate the wallet-address shape BEFORE the id reaches the Supabase REST query: id is
  // attacker-controlled and used in getLastTs's URL before signature verification, so a non-address
  // string could inject PostgREST query syntax. Reject anything that isn't a 0x+40-hex address OR a
  // base58 Solana address (same shape rules as telemetry-schema.js — imported, not re-derived, so the
  // two checks can never drift apart).
  let id;
  try { id = JSON.parse(message).id; } catch { return { statusCode: 400, body: "bad_json" }; }
  if (typeof id !== "string" || !(BASE_ID_RE.test(id) || SOLANA_ID_RE.test(id))) return { statusCode: 400, body: "schema" };

  const cfg = { url, key };
  const lastTs = await getLastTs(id, cfg);
  const now = Math.floor(Date.now() / 1000);
  const v = verifyTelemetry(message, signature, { now, lastTs });
  if (!v.ok) return { statusCode: BAD_REQUEST.has(v.reason) ? 400 : 401, body: v.reason };
  // WALLET = 1 IDENTITY (Dais 2026-06-22: "every agent has its own wallet — Akash was STEALING
  // anicca-a3cdd4's wallet; I never want to see 'akash' on the dashboard"). The canonical host for a
  // wallet is either a pre-registered fixed name (FIXED_IDENTITIES) or, for auto-derived instances,
  // deterministically "anicca-<first 6 hex of address>" (matches runtime assignIdentity — EVM only, an
  // auto-derived Solana instance doesn't exist yet). A validly-signed post whose host ≠ its own wallet's
  // canonical name is a squatter sharing a key that isn't its own → reject, so the dashboard row can
  // NEVER be overwritten by a foreign-named instance.
  const wantHost = expectedHost(id);
  if (String(v.payload.host).toLowerCase() !== wantHost.toLowerCase()) {
    return { statusCode: 400, body: "host_wallet_mismatch" };
  }
  await upsertInstance(v.payload, cfg);
  return { statusCode: 202, body: JSON.stringify({ ok: true }) };
};
