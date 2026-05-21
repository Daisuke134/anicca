import express from 'express';
import baseLogger from '../../utils/logger.js';
import { getEntitlementState, normalizePlanForResponse } from '../../services/subscriptionStore.js';
import extractUserId from '../../middleware/extractUserId.js';

const router = express.Router();
const logger = baseLogger.withContext('MobileEntitlement');

// GET /api/mobile/entitlement
router.get('/', async (req, res) => {
  const deviceId = (req.get('device-id') || '').toString().trim();
  const userId = await extractUserId(req, res);
  if (!userId) return;

  try {
    const state = await getEntitlementState(userId);
    return res.json({ entitlement: normalizePlanForResponse(state) });
  } catch (error) {
    logger.error('Failed to get entitlement', error);
    return res.status(500).json({ error: { code: 'INTERNAL_ERROR', message: 'Failed to get entitlement' } });
  }
});

export default router;

