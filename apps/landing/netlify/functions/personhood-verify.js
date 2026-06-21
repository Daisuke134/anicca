// POST /.netlify/functions/personhood-verify
// Body: { proof, signal }  where proof = the World ID IDKit ISuccessResult, signal = the claim's
// recipient (email or wallet). Verifies the proof with Worldcoin (verifyCloudProof handles signal
// hashing + the /api/v2/verify call, guaranteeing the signal_hash matches the frontend IDKitWidget),
// then enforces ONE-human-ONE-recipient by deduping the nullifier_hash in Supabase.
//
// Sybil guard is ATOMIC: personhood_nullifiers has UNIQUE(nullifier_hash, action); a duplicate INSERT
// returns 409 -> already_claimed. The decision to allow is gated on a successful unique insert, never
// on a prior read (no TOCTOU). Fail-closed: any verify failure / config miss -> deny, never allow.
//
// Required SQL (run in Supabase once):
//   create table if not exists personhood_nullifiers (
//     id bigint generated always as identity primary key,
//     nullifier_hash text not null,
//     action text not null,
//     signal text,
//     created_at timestamptz not null default now(),
//     unique (nullifier_hash, action)
//   );

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE = process.env.SUPABASE_SERVICE_ROLE_KEY;
const APP_ID = process.env.WORLDCOIN_APP_ID;
const ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';

function json(statusCode, obj) {
  return { statusCode, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(obj) };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  if (!SUPABASE_URL || !SUPABASE_SERVICE) return json(500, { ok: false, reason: 'missing_supabase_config' });
  if (!APP_ID) return json(500, { ok: false, reason: 'missing_worldcoin_app_id' });

  let body;
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { ok: false, reason: 'invalid_json' }); }
  const { proof, signal } = body;
  if (!proof || typeof proof !== 'object') return json(400, { ok: false, reason: 'proof_required' });
  if (!signal) return json(400, { ok: false, reason: 'signal_required' }); // recipient binding (anti-relay)

  // 1) verify the proof with Worldcoin (verifyCloudProof hashes the signal + calls /api/v2/verify).
  let verifyRes;
  try {
    const { verifyCloudProof } = await import('@worldcoin/idkit');
    verifyRes = await verifyCloudProof(proof, APP_ID, ACTION, signal);
  } catch (e) {
    console.error('[personhood-verify] verify error', e?.message);
    return json(500, { ok: false, reason: 'verify_error' });
  }
  if (!verifyRes || verifyRes.success !== true) {
    return json(403, { ok: false, reason: (verifyRes && (verifyRes.code || verifyRes.detail)) || 'verification_failed' });
  }

  // 2) atomic sybil dedup: insert the nullifier; a UNIQUE violation (409) means already claimed.
  const nullifier_hash = proof.nullifier_hash;
  if (!nullifier_hash) return json(403, { ok: false, reason: 'no_nullifier' });
  const ins = await fetch(`${SUPABASE_URL}/rest/v1/personhood_nullifiers`, {
    method: 'POST',
    headers: {
      apikey: SUPABASE_SERVICE,
      Authorization: `Bearer ${SUPABASE_SERVICE}`,
      'Content-Type': 'application/json',
      Prefer: 'return=minimal',
    },
    body: JSON.stringify({ nullifier_hash, action: ACTION, signal: String(signal) }),
  });
  if (ins.status === 409) return json(409, { ok: false, reason: 'already_claimed' });
  if (!ins.ok) {
    // any non-insert (write failure) must NOT pass as allowed -> deny (fail-closed).
    console.error('[personhood-verify] nullifier insert failed', ins.status);
    return json(500, { ok: false, reason: 'dedup_store_error' });
  }
  return json(200, { ok: true, nullifier_hash });
};
