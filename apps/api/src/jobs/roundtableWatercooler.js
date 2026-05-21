import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { sendSlackMessage } from '../services/slackNotifier.js';

const logger = baseLogger.withContext('RoundtableWatercooler');

export async function runRoundtableWatercooler(options = {}) {
  const nowMs = options.nowMs ?? Date.now();
  const since = new Date(nowMs - 24 * 60 * 60 * 1000);

  const incidents = await prisma.agentAuditLog.count({
    where: {
      createdAt: { gte: since },
      eventType: { in: ['crisis:detected', 'safe_t_interrupted', 'crisis_notification_failed'] },
    },
  });

  if (incidents > 0) {
    logger.info('Watercooler skipped (incidents present)', { incidents });
    return { skipped: true, incidents };
  }

  await sendSlackMessage('#ops', {
    text: 'Watercooler: 24h stable run',
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: '*watercooler*\nNo major incidents in the last 24h. Keep shipping.',
        },
      },
    ],
  });

  return { skipped: false, incidents: 0 };
}

export default {
  runRoundtableWatercooler,
};
