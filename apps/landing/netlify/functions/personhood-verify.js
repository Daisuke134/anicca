// POST /.netlify/functions/personhood-verify
// Body: { proof, signal }  — the IDKit handleVerify UX step. VERIFY-ONLY: confirms the World ID proof
// is valid (so the form can show "verified" and enable submit) but does NOT claim the nullifier here.
// The AUTHORITATIVE sybil gate (verify + atomic nullifier dedup + recipient record) lives in
// income-signup.js, enforced at the server write boundary so it cannot be bypassed by calling the
// signup endpoint directly (VCSDD FIND-001). Fail-closed.

const { verifyProof } = require('./_lib/worldid.js');

const APP_ID = process.env.WORLDCOIN_APP_ID;
const ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';

function json(statusCode, obj) {
  return { statusCode, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(obj) };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  if (!APP_ID) return json(500, { ok: false, reason: 'missing_worldcoin_app_id' });
  let body;
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { ok: false, reason: 'invalid_json' }); }
  const res = await verifyProof({ proof: body.proof, signal: body.signal, appId: APP_ID, action: ACTION });
  return json(res.ok ? 200 : res.status, res.ok ? { ok: true } : { ok: false, reason: res.reason });
};
