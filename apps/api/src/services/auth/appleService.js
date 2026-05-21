import { createRemoteJWKSet, jwtVerify } from 'jose';
import baseLogger from '../../utils/logger.js';
import { getOrCreateInternalUser } from '../users/profileStore.js';

const logger = baseLogger.withContext('AppleAuthService');
const APPLE_JWKS_URL = new URL('https://appleid.apple.com/auth/keys');

let appleJWKS;

function getAppleJWKS() {
  if (!appleJWKS) {
    appleJWKS = createRemoteJWKSet(APPLE_JWKS_URL, {
      cacheLifetime: 60_000,
      cooldownDuration: 5_000
    });
  }
  return appleJWKS;
}

export async function warmAppleKeys() {
  try {
    const jwks = getAppleJWKS();
    await jwks({ alg: 'RS256', kid: 'warmup-placeholder' }).catch(() => null);
    logger.info('Apple JWKS warmed');
  } catch (error) {
    logger.warn('Warm-up failed (non-critical)', error);
    throw error;
  }
}

export async function verifyIdentityToken(identityToken, nonce, rawUserId) {
  const jwks = getAppleJWKS();
  const { payload } = await jwtVerify(identityToken, jwks, {
    issuer: 'https://appleid.apple.com',
    audience: process.env.APPLE_SIGN_IN_CLIENT_ID,
    nonce
  });

  const appleUserId = payload.sub ?? rawUserId;
  const displayName = payload.name ?? 'User';
  const internalUserId = await getOrCreateInternalUser({
    appleUserId,
    email: payload.email,
    displayName
  });

  return {
    userId: internalUserId,
    appleUserId,
    displayName,
    email: payload.email
  };
}
