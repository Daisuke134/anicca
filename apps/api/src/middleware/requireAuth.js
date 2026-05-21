import crypto from 'crypto';

// HS256 JWT 検証（外部依存なし）
function verifyJwtHs256(token, secret) {
  const parts = String(token || '').split('.');
  if (parts.length !== 3) throw new Error('invalid jwt');
  const [h, p, s] = parts;
  const data = `${h}.${p}`;
  const expected = crypto.createHmac('sha256', secret).update(data).digest('base64url');
  const ok = crypto.timingSafeEqual(Buffer.from(s), Buffer.from(expected));
  if (!ok) throw new Error('signature mismatch');
  const payloadJson = Buffer.from(p, 'base64url').toString('utf8');
  return JSON.parse(payloadJson);
}

function tryVerify(token, secret) {
  if (!secret) return null;
  try {
    return verifyJwtHs256(token, secret);
  } catch (e) {
    return null;
  }
}

export default async function requireAuth(req, res) {
  try {
    const auth = req.headers['authorization'] || '';
    if (!auth.startsWith('Bearer ')) {
      res.status(401).json({ error: 'Missing Authorization bearer' });
      return null;
    }
    const token = auth.slice('Bearer '.length).trim();

    const memberSecret = process.env.PROXY_AUTH_JWT_SECRET;
    const guestSecret = process.env.PROXY_GUEST_JWT_SECRET;

    let decoded = tryVerify(token, memberSecret);
    let tokenType = 'member';

    if (!decoded) {
      decoded = tryVerify(token, guestSecret);
      tokenType = decoded ? 'guest' : null;
    }

    if (!decoded || !tokenType) {
      console.warn('JWT verification failed: no matching secret');
      res.status(401).json({ error: 'Invalid token' });
      return null;
    }

    const sub = decoded?.sub || decoded?.uid || decoded?.user_id || decoded?.email || null;
    if (!sub) {
      res.status(401).json({ error: 'Token missing subject' });
      return null;
    }

    const email = decoded?.email || null;
    const plan = decoded?.plan || (tokenType === 'guest' ? 'guest' : 'free');
    const status = decoded?.status || plan;
    const usageLimit = Number.isFinite(decoded?.usage_limit) ? decoded.usage_limit : null;
    const usageRemaining = Number.isFinite(decoded?.usage_remaining) ? decoded.usage_remaining : null;
    const guestSessionId = tokenType === 'guest'
      ? (decoded?.guest_session_id || sub)
      : null;

    return { sub, email, plan, status, usageLimit, usageRemaining, raw: decoded, tokenType, guestSessionId };
  } catch (e) {
    console.warn('JWT verification failed:', e?.message || String(e));
    res.status(401).json({ error: 'Invalid token' });
    return null;
  }
}
