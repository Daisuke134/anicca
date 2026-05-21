import requireAuth from './requireAuth.js';
import baseLogger from '../utils/logger.js';

const logger = baseLogger.withContext('ExtractUserId');

/**
 * Prefer Bearer token (AT). Fallback to device-id/user-id headers (legacy).
 * @returns {Promise<string|null>}
 */
export default async function extractUserId(req, res) {
  const authHeader = String(req.headers['authorization'] || '');
  if (authHeader.startsWith('Bearer ')) {
    const auth = await requireAuth(req, res);
    if (!auth) return null;
    return auth.sub;
  }
  const deviceId = (req.get('device-id') || '').toString().trim();
  const userId = (req.get('user-id') || '').toString().trim();
  if (!deviceId) {
    logger.warn('Missing device-id header');
    res.status(400).json({ error: { code: 'INVALID_REQUEST', message: 'device-id is required' } });
    return null;
  }
  if (!userId) {
    logger.warn('Missing user-id header');
    res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'user-id is required' } });
    return null;
  }
  return userId;
}



