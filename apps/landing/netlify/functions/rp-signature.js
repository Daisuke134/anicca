// POST /.netlify/functions/rp-signature
// Body: { action }  -> { sig, nonce, created_at, expires_at }
// World ID 4.0 step 3: sign the proof request with the RP signing key so World App/Portal trust it
// came from us. The signing key (RP_SIGNING_KEY) is a SECRET — server-only, NEVER sent to the client,
// NEVER NEXT_PUBLIC. Source: https://docs.world.org/world-id/idkit/integrate (step 3).

const RP_SIGNING_KEY = process.env.RP_SIGNING_KEY;
const DEFAULT_ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';

function json(statusCode, obj) {
  return { statusCode, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(obj) };
}

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  if (!RP_SIGNING_KEY) return json(500, { error: 'missing RP_SIGNING_KEY' });
  let body;
  try { body = JSON.parse(event.body || '{}'); } catch { return json(400, { error: 'invalid json' }); }
  const action = body.action || DEFAULT_ACTION;
  try {
    const { signRequest } = await import('@worldcoin/idkit-core/signing');
    const { sig, nonce, createdAt, expiresAt } = signRequest({ signingKeyHex: RP_SIGNING_KEY, action });
    return json(200, { sig, nonce, created_at: createdAt, expires_at: expiresAt });
  } catch (e) {
    return json(500, { error: 'signing_failed' });
  }
};
