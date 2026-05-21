import express from 'express';
import prisma from '../../lib/prisma.js';
import requireInternalAuth from '../../middleware/requireInternalAuth.js';
import baseLogger from '../../utils/logger.js';
import { sendSlackMessage } from '../../services/slackNotifier.js';

const router = express.Router();
const logger = baseLogger.withContext('AdminOpsEvents');

router.use(requireInternalAuth);

// POST /api/admin/ops/events
// Used by: automation agents (GHA/VPS) to record ops events + emit Slack notifications.
router.post('/events', async (req, res) => {
  try {
    const { eventType, platform = null, payload = {} } = req.body || {};

    if (!eventType || typeof eventType !== 'string') {
      return res.status(400).json({ error: 'eventType is required' });
    }

    const normalizedPlatform = platform ? String(platform).toLowerCase() : null;

    // Record (SSOT inside this repo is agent_audit_logs)
    await prisma.agentAuditLog.create({
      data: {
        eventType,
        platform: normalizedPlatform,
        requestPayload: payload,
        executedBy: 'system',
      },
    });

    // Deduplicated Slack notifications for noisy events
    if (eventType === 'x_credits_depleted') {
      const existing = await prisma.agentAuditLog.findFirst({
        where: {
          eventType: 'x_credits_depleted',
          createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
        },
        orderBy: { createdAt: 'desc' },
      });

      // If we just created it above, this is always non-null. We dedupe by finding a *previous* one.
      // Simple approach: if there is more than one in 24h, suppress Slack.
      const count = await prisma.agentAuditLog.count({
        where: {
          eventType: 'x_credits_depleted',
          createdAt: { gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
        },
      });

      if (count <= 1) {
        const msg = {
          text: '⚠️ X posting paused: credits/rate limit detected. Routing to App Nudge.',
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: `*Event*: x_credits_depleted\n*Action*: pause X posting for today; route to App Nudge\n*Payload*: ${JSON.stringify(payload).slice(0, 800)}`,
              },
            },
          ],
        };

        await sendSlackMessage('#ops', msg);
        await sendSlackMessage('#agents', msg);
      } else {
        logger.warn('Slack suppressed (duplicate x_credits_depleted in 24h)', { count, existingAt: existing?.createdAt });
      }
    }

    return res.json({ success: true });
  } catch (error) {
    logger.error('Failed to record ops event', error);
    return res.status(500).json({ error: 'Failed to record ops event' });
  }
});

export default router;
