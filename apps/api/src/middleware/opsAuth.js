import { logger } from '../lib/logger.js';

/**
 * Ops API auth middleware
 * Validates ANICCA_AGENT_TOKEN via Bearer auth
 * Supports token rotation with ANICCA_AGENT_TOKEN_OLD during grace period
 * (aligned with requireAgentAuth.js)
 */
export function opsAuth(req, res, next) {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    logger.warn('[opsAuth] Missing or invalid Authorization header');
    return res.status(401).json({ error: 'Unauthorized' });
  }

  const token = authHeader.slice(7);
  const currentToken = process.env.ANICCA_AGENT_TOKEN;
  const oldToken = process.env.ANICCA_AGENT_TOKEN_OLD;

  const isValid = token === currentToken || (oldToken && token === oldToken);

  if (!isValid) {
    // Log first 8 chars of each for debugging (redacted)
    logger.warn(`[opsAuth] Token mismatch: got=${token?.slice(0,8)}... expected=${currentToken?.slice(0,8)}...`);
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}
