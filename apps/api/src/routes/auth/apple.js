import express from 'express';
import { z } from 'zod';
import { verifyIdentityToken, warmAppleKeys } from '../../services/auth/appleService.js';
import baseLogger from '../../utils/logger.js';
import { signJwtHs256 } from '../../utils/jwt.js';
import crypto from 'crypto';
import { upsertRefreshToken } from '../../services/auth/refreshStore.js';

const router = express.Router();
const logger = baseLogger.withContext('AppleAuth');

const appleAuthSchema = z.object({
  identity_token: z.string(),
  nonce: z.string(),
  user_id: z.string() // Apple's user identifier
});

/**
 * POST /auth/apple
 * Verify Apple identity token and create/update user
 */
router.post('/', async (req, res) => {
  try {
    const normalizedBody = {
      identity_token: req.body.identity_token ?? req.body.identityToken,
      nonce: req.body.nonce ?? req.body.nonceToken ?? req.body.hashedNonce,
      user_id: req.body.user_id ?? req.body.userId ?? req.body.user
    };
    const validationResult = appleAuthSchema.safeParse(normalizedBody);
    
    if (!validationResult.success) {
      logger.warn('Invalid Apple auth payload', validationResult.error);
      return res.status(400).json({ 
        error: 'invalid_request',
        details: validationResult.error.errors 
      });
    }
    
    const { identity_token, nonce, user_id } = validationResult.data;
    
    // Verify identity token
    const verifiedUser = await verifyIdentityToken(identity_token, nonce, user_id);
    
    if (!verifiedUser) {
      logger.warn('Apple token verification failed');
      return res.status(401).json({ error: 'token_verification_failed' });
    }
    
    // Issue Access Token (15 min)
    const jwtSecret = process.env.PROXY_AUTH_JWT_SECRET;
    if (!jwtSecret) {
      logger.error('PROXY_AUTH_JWT_SECRET not configured');
      return res.status(500).json({ error: 'server_not_configured' });
    }
    const now = Math.floor(Date.now() / 1000);
    const exp = now + (15 * 60);
    const jti = crypto.randomUUID();
    const accessPayload = {
      sub: verifiedUser.userId,
      iat: now,
      exp,
      jti,
      iss: 'anicca-proxy',
      aud: 'anicca-mobile'
    };
    const token = signJwtHs256(accessPayload, jwtSecret);

    // Issue Refresh Token (30 days) and store hashed
    const rt = crypto.randomBytes(32).toString('base64url');
    try {
      await upsertRefreshToken({
        userId: verifiedUser.userId,
        token: rt,
        deviceId: (req.get('device-id') || 'unknown').toString(),
        ttlDays: 30,
        userAgent: req.get('user-agent') || null
      });
    } catch (e) {
      logger.error('Failed to persist refresh token', e);
      return res.status(500).json({ error: 'failed_to_issue_token' });
    }

    // Return tokens + user info
    return res.json({
      userId: verifiedUser.userId,
      appleUserId: verifiedUser.appleUserId,
      displayName: verifiedUser.displayName,
      email: verifiedUser.email,
      token,
      expiresAt: exp * 1000,
      refreshToken: rt
    });
  } catch (error) {
    logger.error('Apple auth error', error);
    return res.status(500).json({ error: 'internal_error' });
  }
});

/**
 * GET /auth/apple/health
 * Health check endpoint for warming up Apple auth infrastructure
 */
router.get('/health', async (req, res) => {
  // iOS側のウォームアップ用途。ここは「速く200を返す」が最優先（タイムアウト/UX悪化を防ぐ）
  res.status(200).json({ status: 'ok' });

  // fire-and-forget: 失敗してもhealth自体は落とさない
  warmAppleKeys().catch((e) => {
    logger.warn('Apple keys warmup failed', e);
  });
});

export default router;

