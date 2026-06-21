// _lib/worldid4.js — World ID 4.0 personhood verify + atomic nullifier claim for the /income gate.
// CJS (netlify functions). Replaces the classic verifyCloudProof path: 4.0 forwards the IDKit result
// to the Developer Portal v4 verify endpoint, then we dedupe the nullifier atomically.
// Source: https://docs.world.org/world-id/idkit/integrate (steps 5-6), verified 2026-06-21.

const VERIFY_BASE = 'https://developer.world.org/api/v4/verify';

// Pure: pull the nullifier (normalized lowercase hex) from a 4.0 IDKit response. null if absent.
function extractNullifier(idkitResponse) {
  const r = idkitResponse && Array.isArray(idkitResponse.responses) ? idkitResponse.responses[0] : null;
  const n = r && r.nullifier;
  return typeof n === 'string' && /^0x[0-9a-fA-F]+$/.test(n) ? n.toLowerCase() : null;
}

// Pure: the signal_hash the response was bound to (lowercase). null if absent.
function responseSignalHash(idkitResponse) {
  const r = idkitResponse && Array.isArray(idkitResponse.responses) ? idkitResponse.responses[0] : null;
  const s = r && r.signal_hash;
  return typeof s === 'string' ? s.toLowerCase() : null;
}

// Live: forward the IDKit response AS-IS to the v4 verify endpoint. Returns {ok} | {ok:false,status}.
// Fail-closed: any non-2xx / network error -> not ok.
async function verifyV4(idkitResponse, rpId, { fetchImpl = fetch } = {}) {
  if (!rpId) return { ok: false, status: 500, reason: 'missing_rp_id' };
  if (!idkitResponse || typeof idkitResponse !== 'object' || !Array.isArray(idkitResponse.responses)) {
    return { ok: false, status: 400, reason: 'invalid_idkit_response' };
  }
  let res;
  try {
    res = await fetchImpl(`${VERIFY_BASE}/${rpId}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(idkitResponse),
    });
  } catch { return { ok: false, status: 500, reason: 'verify_network_error' }; }
  if (!res.ok) return { ok: false, status: res.status === 400 ? 403 : 502, reason: 'verification_failed' };
  // Don't trust HTTP 2xx alone — require the body to assert success:true (VCSDD FIND-003: a 200 with a
  // failure payload must NOT pass). The v4 endpoint returns { success: true, nullifier, ... } on success.
  const data = await res.json().catch(() => null);
  if (!data || data.success !== true) return { ok: false, status: 403, reason: 'verification_failed' };
  return { ok: true };
}

// verify + ATOMIC claim. expectedSignalHash (optional) binds the proof to OUR signal (e.g. hashSignal(email))
// so a proof minted for one signal cannot be relayed to another. insert(row)->status hits a table with
// UNIQUE(nullifier_hash, action); 409 = already_claimed. Fail-closed throughout.
async function verifyAndClaimV4({ idkitResponse, rpId, action, expectedSignalHash, insert, verify = verifyV4 } = {}) {
  const v = await verify(idkitResponse, rpId);
  if (!v.ok) return v;
  if (expectedSignalHash) {
    const got = responseSignalHash(idkitResponse);
    if (!got || got !== String(expectedSignalHash).toLowerCase()) {
      return { ok: false, status: 403, reason: 'signal_mismatch' }; // anti-relay
    }
  }
  const nullifier = extractNullifier(idkitResponse);
  if (!nullifier) return { ok: false, status: 403, reason: 'no_nullifier' };
  if (typeof insert !== 'function') return { ok: false, status: 500, reason: 'no_store' };
  let status;
  try { status = await insert({ nullifier_hash: nullifier, action, signal: idkitResponse?.responses?.[0]?.signal_hash || null }); }
  catch { return { ok: false, status: 500, reason: 'dedup_store_error' }; }
  if (status === 409) return { ok: false, status: 409, reason: 'already_claimed' };
  if (status < 200 || status >= 300) return { ok: false, status: 500, reason: 'dedup_store_error' };
  return { ok: true, nullifier_hash: nullifier };
}

// hashSignal helper (dynamic ESM import of idkit-core) — for binding the email as signal server-side.
async function hashSignalHex(signal) {
  const { hashSignal } = await import('@worldcoin/idkit-core');
  const h = hashSignal(signal);
  // hashSignal returns { digest, hash } or a value depending on version — normalize to 0x hex string.
  const v = (h && (h.digest ?? h.hash ?? h)) ;
  return typeof v === 'bigint' ? '0x' + v.toString(16) : String(v).toLowerCase();
}

// Supabase inserter for personhood_nullifiers (returns HTTP status).
function supabaseNullifierInsert(supabaseUrl, serviceKey) {
  return async (row) => {
    const res = await fetch(`${supabaseUrl}/rest/v1/personhood_nullifiers`, {
      method: 'POST',
      headers: { apikey: serviceKey, Authorization: `Bearer ${serviceKey}`, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
      body: JSON.stringify(row),
    });
    return res.status;
  };
}

module.exports = { verifyV4, verifyAndClaimV4, extractNullifier, responseSignalHash, hashSignalHex, supabaseNullifierInsert, VERIFY_BASE };
