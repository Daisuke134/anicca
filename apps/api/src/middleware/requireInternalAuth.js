import crypto from 'crypto';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('RequireInternalAuth');

/**
 * 内部API用認証ミドルウェア（Admin API + cron job）
 * INTERNAL_API_TOKEN と INTERNAL_AUTH_SECRET のいずれかに一致するBearerトークンを要求
 * timing-safe comparison でタイミング攻撃を防止
 */
export default function requireInternalAuth(req, res, next) {
  const auth = req.headers['authorization'] || '';
  if (!auth.startsWith('Bearer ')) {
    logger.warn('Missing Authorization bearer for internal API');
    return res.status(401).json({ error: 'Missing Authorization bearer' });
  }

  const token = auth.slice('Bearer '.length).trim();
  const expectedToken = process.env.INTERNAL_API_TOKEN || process.env.INTERNAL_AUTH_SECRET;

  if (!expectedToken) {
    logger.error('INTERNAL_API_TOKEN / INTERNAL_AUTH_SECRET not configured');
    return res.status(500).json({ error: 'Internal API token not configured' });
  }

  const tokenBuf = Buffer.from(token, 'utf8');
  const expectedBuf = Buffer.from(expectedToken, 'utf8');

  if (tokenBuf.length !== expectedBuf.length || !crypto.timingSafeEqual(tokenBuf, expectedBuf)) {
    logger.warn('Invalid internal API token');
    return res.status(401).json({ error: 'Invalid token' });
  }

  next();
}
