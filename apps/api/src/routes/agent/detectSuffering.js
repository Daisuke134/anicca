import { Router } from 'express';
import { prisma } from '../../lib/prisma.js';
import { detectSuffering } from '../../services/sufferingDetectionService.js';
import { sendSlackMessage } from '../../services/slackNotifier.js';

const router = Router();

router.post('/', async (req, res) => {
  try {
    const {
      platform,
      context,
      externalPostId = null,
      platformUserId = null,
      severity = null,
      severityScore = null,
      region = null,
    } = req.body || {};

    if (!platform || typeof platform !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'platform is required and must be a string',
      });
    }

    if (!context || typeof context !== 'string') {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'context is required and must be a string',
      });
    }

    const normalizedPlatform = platform.trim().toLowerCase();
    const result = detectSuffering({ context, severityScore, severity, source: 'detect_suffering' });

    for (const eventType of result.eventTypes) {
      await prisma.agentAuditLog.create({
        data: {
          eventType,
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId,
            platformUserId,
            region,
            severityScore: result.severityScore,
          },
          responsePayload: {
            detections: result.detections,
          },
          executedBy: 'system',
        },
      });
    }

    if (result.safeTTriggered) {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'safe_t_interrupted',
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId,
            platformUserId,
            region,
            severityScore: result.severityScore,
          },
          executedBy: 'system',
        },
      });

      try {
        await sendSlackMessage('#agents', {
          text: `🚨 Crisis detected (${normalizedPlatform})`,
          blocks: [
            {
              type: 'section',
              text: {
                type: 'mrkdwn',
                text: `*Platform*: ${normalizedPlatform}\n*Region*: ${region || 'unknown'}\n*Severity Score*: ${result.severityScore.toFixed(2)}\n*External Post ID*: ${externalPostId || 'n/a'}`,
              },
            },
          ],
        });

        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_sent',
            platform: normalizedPlatform,
            requestPayload: {
              externalPostId,
              platformUserId,
              region,
            },
            executedBy: 'system',
          },
        });
      } catch (error) {
        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_failed',
            platform: normalizedPlatform,
            requestPayload: {
              externalPostId,
              platformUserId,
              region,
              error: error.message,
            },
            executedBy: 'system',
          },
        });
      }
    }

    return res.json({
      detections: result.detections,
      stepComplete: {
        eventType: 'step/complete',
        safeTTriggered: result.safeTTriggered,
        emittedEvents: result.eventTypes,
      },
    });
  } catch (error) {
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error.message,
    });
  }
});

export default router;
