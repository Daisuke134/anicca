import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { detectSuffering } from '../services/sufferingDetectionService.js';
import { sendSlackMessage } from '../services/slackNotifier.js';

const logger = baseLogger.withContext('SufferingDetectorJob');

// Synthetic feed for Day-0 operational verification.
// This avoids any external integration while still exercising:
// - detect_suffering thresholds
// - audit log events
// - SAFE-T interruption + Slack notification
const SYNTHETIC_FEED = [
  { platform: 'moltbook', region: 'JP', externalPostId: 'synthetic-1', platformUserId: 'moltbook:synthetic', context: '最近ずっと眠れない。しんどい。', severityScore: 0.65 },
  { platform: 'moltbook', region: 'JP', externalPostId: 'synthetic-2', platformUserId: 'moltbook:synthetic', context: '死にたい。もう無理。', severityScore: 0.95 },
];

export async function runSufferingDetectorJob(options = {}) {
  const now = new Date();
  const feed = options.feed || SYNTHETIC_FEED;

  const emitted = [];
  let slackSent = 0;
  let slackFailed = 0;

  for (const item of feed) {
    const normalizedPlatform = String(item.platform || 'unknown').toLowerCase();
    const result = detectSuffering({
      context: item.context,
      severityScore: item.severityScore ?? null,
      severity: item.severity ?? null,
      source: 'suffering-detector-job',
    });

    for (const eventType of result.eventTypes) {
      await prisma.agentAuditLog.create({
        data: {
          eventType,
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId: item.externalPostId || null,
            platformUserId: item.platformUserId || null,
            region: item.region || null,
            severityScore: result.severityScore,
            source: 'synthetic_feed',
          },
          responsePayload: { detections: result.detections },
          executedBy: 'system',
        },
      });
      emitted.push(eventType);
    }

    if (result.safeTTriggered) {
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'safe_t_interrupted',
          platform: normalizedPlatform,
          requestPayload: {
            externalPostId: item.externalPostId || null,
            platformUserId: item.platformUserId || null,
            region: item.region || null,
            severityScore: result.severityScore,
            source: 'suffering-detector-job',
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
                text: `*Platform*: ${normalizedPlatform}\n*Region*: ${item.region || 'unknown'}\n*Severity Score*: ${result.severityScore.toFixed(2)}\n*External Post ID*: ${item.externalPostId || 'n/a'}`,
              },
            },
          ],
        });
        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_sent',
            platform: normalizedPlatform,
            requestPayload: { externalPostId: item.externalPostId || null, platformUserId: item.platformUserId || null, region: item.region || null },
            executedBy: 'system',
          },
        });
        slackSent += 1;
      } catch (error) {
        await prisma.agentAuditLog.create({
          data: {
            eventType: 'crisis_notification_failed',
            platform: normalizedPlatform,
            requestPayload: { externalPostId: item.externalPostId || null, platformUserId: item.platformUserId || null, region: item.region || null, error: error?.message || String(error) },
            executedBy: 'system',
          },
        });
        slackFailed += 1;
      }
    }
  }

  const result = {
    ok: true,
    now: now.toISOString(),
    feedCount: feed.length,
    emittedCounts: emitted.reduce((acc, e) => ((acc[e] = (acc[e] || 0) + 1), acc), {}),
    slack: { sent: slackSent, failed: slackFailed },
  };
  logger.info('Suffering detector job completed', result);
  return result;
}

export default runSufferingDetectorJob;
