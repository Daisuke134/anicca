import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { evaluateTriggers } from '../services/triggerEvaluator.js';

const logger = baseLogger.withContext('InitiativeGenerator');

const FAILURE_EVENT_TYPES = [
  'x_post_failed',
  'tiktok_post_failed',
  'blotato_post_failed',
  'x_credits_depleted',
];

export async function computeAppTappedRate7d() {
  const result = await prisma.$queryRaw`
    SELECT
      AVG(CASE WHEN no.reward = 1 THEN 1.0 ELSE 0.0 END) as tap_rate
    FROM nudge_events ne
    JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
  `;

  const row = Array.isArray(result) ? result[0] : result;
  const rate = row?.tap_rate;
  return rate == null ? null : Number(rate);
}

export async function runInitiativeGenerator(options = {}) {
  const nowMs = options.nowMs ?? Date.now();
  const since24h = new Date(nowMs - 24 * 60 * 60 * 1000);

  const audit = await prisma.agentAuditLog.findMany({
    where: {
      createdAt: { gte: since24h },
      eventType: { in: ['suffering_detected', ...FAILURE_EVENT_TYPES] },
    },
    select: { eventType: true, createdAt: true },
  });

  // Normalize multiple failure types into a single stream event.
  const events = (audit || []).map((row) => ({
    eventType: FAILURE_EVENT_TYPES.includes(row.eventType) ? 'post_failure' : row.eventType,
    createdAt: row.createdAt,
  }));

  const triggers = [
    { id: 'suffering_spike', eventType: 'suffering_detected', minCount: 5, windowMs: 24 * 60 * 60 * 1000 },
    { id: 'post_failures', eventType: 'post_failure', minCount: 3, windowMs: 24 * 60 * 60 * 1000 },
  ];
  const matched = evaluateTriggers(triggers, events, new Date(nowMs));

  const sufferingMatch = matched.find((m) => m.triggerId === 'suffering_spike');
  const postFailureMatch = matched.find((m) => m.triggerId === 'post_failures');
  const sufferingCount = sufferingMatch?.matchedCount || 0;
  const postFailureCount = postFailureMatch?.matchedCount || 0;

  const tappedRate7d = await computeAppTappedRate7d().catch(() => null);

  const created = [];

  if (sufferingCount >= 5) {
    created.push(await prisma.initiative.create({
      data: {
        kind: 'suffering_spike',
        reason: `suffering_detected count in 24h = ${sufferingCount} (>= 5)`,
        payload: { sufferingCount, windowHours: 24 },
      },
    }));
  }

  if (tappedRate7d != null && tappedRate7d <= 0.20) {
    created.push(await prisma.initiative.create({
      data: {
        kind: 'low_tap_rate',
        reason: `App tapped_rate 7d moving avg = ${tappedRate7d.toFixed(3)} (<= 0.20)`,
        payload: { tappedRate7d },
      },
    }));
  }

  if (postFailureCount >= 3) {
    created.push(await prisma.initiative.create({
      data: {
        kind: 'post_failures',
        reason: `post failures in 24h = ${postFailureCount} (>= 3)`,
        payload: { postFailureCount, windowHours: 24 },
      },
    }));
  }

  logger.info('Initiative generator completed', {
    sufferingCount,
    tappedRate7d,
    postFailureCount,
    created: created.length,
  });

  return { sufferingCount, tappedRate7d, postFailureCount, createdCount: created.length };
}

export default {
  runInitiativeGenerator,
  computeAppTappedRate7d,
};
