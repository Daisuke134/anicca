import crypto from 'crypto';
import { signJwtHs256 } from '../../utils/jwt.js';
import {
  findValidTokenRow,
  rotateToken,
  revokeByToken,
  revokeAllRefreshTokensForUser,
  markReuseAndRevokeAll
} from './refreshStore.js';

export async function rotateAndIssue(refreshToken, deviceId, userAgent) {
  const row = await findValidTokenRow(refreshToken);
  if (!row) return { error: 'invalid_refresh_token', status: 401 };

  const jwtSecret = process.env.PROXY_AUTH_JWT_SECRET;
  if (!jwtSecret) return { error: 'server_not_configured', status: 500 };

  // Rotate RT
  const newRt = crypto.randomBytes(32).toString('base64url');
  await rotateToken(row, newRt, { deviceId, userAgent });

  // Issue new AT
  const now = Math.floor(Date.now() / 1000);
  const exp = now + 15 * 60;
  const jti = crypto.randomUUID();
  const at = signJwtHs256(
    { sub: row.user_id, iat: now, exp, jti, iss: 'anicca-proxy', aud: 'anicca-mobile' },
    jwtSecret
  );

  return { token: at, expiresAt: exp * 1000, refreshToken: newRt };
}

export async function revoke(refreshToken, options = {}) {
  if (options.all) {
    if (options.userFromToken) {
      const row = await findValidTokenRow(refreshToken);
      if (row) {
        await revokeAllRefreshTokensForUser(row.user_id);
        return { ok: true, scope: 'all' };
      }
      return { ok: true };
    }
    return { ok: true };
  }
  await revokeByToken(refreshToken);
  return { ok: true };
}

export async function handleReuseDetected(userId) {
  await markReuseAndRevokeAll(userId);
}

export { revokeAllRefreshTokensForUser } from './refreshStore.js';












