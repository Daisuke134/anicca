// _lib/worldid.js — shared World ID personhood verification + atomic nullifier claim for the
// /income gate. CJS (netlify functions are CJS). The authoritative sybil gate lives HERE and is
// consumed by income-signup (the recipient-record writer) so personhood is enforced at the server
// write boundary, NOT only in the browser (VCSDD FIND-001). verifyCloudProof is dynamically imported
// (it is ESM) and recomputes signal_hash, so a proof minted for email A cannot be relayed to email B.

// verify-only (no dedup) — used by the handleVerify UX step. Returns {ok} | {ok:false,status,reason}.
async function verifyProof({ proof, signal, appId, action, verify } = {}) {
  if (!proof || typeof proof !== 'object') return { ok: false, status: 400, reason: 'proof_required' };
  if (!signal) return { ok: false, status: 400, reason: 'signal_required' };
  if (!appId) return { ok: false, status: 500, reason: 'missing_worldcoin_app_id' };
  const doVerify = verify || (async (p, a, act, sig) => {
    const { verifyCloudProof } = await import('@worldcoin/idkit');
    return verifyCloudProof(p, a, act, sig);
  });
  let v;
  try { v = await doVerify(proof, appId, action, signal); }
  catch { return { ok: false, status: 500, reason: 'verify_error' }; }
  if (!v || v.success !== true) return { ok: false, status: 403, reason: (v && (v.code || v.detail)) || 'verification_failed' };
  const nullifier_hash = proof.nullifier_hash;
  if (!nullifier_hash) return { ok: false, status: 403, reason: 'no_nullifier' };
  return { ok: true, nullifier_hash };
}

// verify + ATOMIC claim — used by income-signup (authoritative). `insert(row)->status` must hit a
// table with UNIQUE(nullifier_hash, action); a 409 means already claimed. Allow is gated on a
// successful unique insert (no TOCTOU); any write failure denies (fail-closed).
async function verifyAndClaim({ proof, signal, appId, action, verify, insert } = {}) {
  const v = await verifyProof({ proof, signal, appId, action, verify });
  if (!v.ok) return v;
  if (typeof insert !== 'function') return { ok: false, status: 500, reason: 'no_store' };
  let status;
  try { status = await insert({ nullifier_hash: v.nullifier_hash, action, signal: String(signal) }); }
  catch { return { ok: false, status: 500, reason: 'dedup_store_error' }; }
  if (status === 409) return { ok: false, status: 409, reason: 'already_claimed' };
  if (status < 200 || status >= 300) return { ok: false, status: 500, reason: 'dedup_store_error' };
  return { ok: true, nullifier_hash: v.nullifier_hash };
}

// default Supabase inserter for personhood_nullifiers (returns the HTTP status).
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

module.exports = { verifyProof, verifyAndClaim, supabaseNullifierInsert };
