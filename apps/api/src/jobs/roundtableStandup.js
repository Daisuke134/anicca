import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { sendSlackMessage } from '../services/slackNotifier.js';

const logger = baseLogger.withContext('RoundtableStandup');

async function countAudit(eventType, since) {
  return prisma.agentAuditLog.count({
    where: {
      eventType,
      createdAt: { gte: since },
    },
  });
}

async function countTable(model, where) {
  return prisma[model].count({ where });
}

async function computeAppTapSummary(since) {
  const result = await prisma.$queryRaw`
    SELECT
      COUNT(*)::int as outcome_count,
      SUM(CASE WHEN no.reward = 1 THEN 1 ELSE 0 END)::int as tap_count
    FROM nudge_events ne
    JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.domain = 'problem_nudge'
      AND ne.created_at >= ${since}
  `;

  const row = Array.isArray(result) ? result[0] : result;
  const outcomeCount = Number(row?.outcome_count ?? 0);
  const tapCount = Number(row?.tap_count ?? 0);
  const tapRate = outcomeCount > 0 ? tapCount / outcomeCount : 0;
  return { outcomeCount, tapCount, tapRate };
}

export async function runRoundtableStandup(options = {}) {
  const nowMs = options.nowMs ?? Date.now();
  const since = new Date(nowMs - 24 * 60 * 60 * 1000);

  const suffering = await countAudit('suffering_detected', since);
  const crisis = await countAudit('crisis:detected', since);
  const safeT = await countAudit('safe_t_interrupted', since);
  const xCredits = await countAudit('x_credits_depleted', since);

  const xPosts = await countTable('xPost', { postedAt: { gte: since } }).catch(() => 0);
  const tiktokPosts = await countTable('tiktokPost', { postedAt: { gte: since } }).catch(() => 0);

  const app = await computeAppTapSummary(since).catch(() => ({ outcomeCount: 0, tapCount: 0, tapRate: 0 }));

  const message = {
    text: 'Anicca Standup (Daily)',
    blocks: [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*standup*\n*yesterday:*\n- suffering_detected: ${suffering}\n- crisis:detected: ${crisis} (safe_t_interrupt: ${safeT})\n- x_credits_depleted: ${xCredits}\n\n*today:*\n- Maintain detect-only on X; route to App Nudge when needed\n- Monitor Moltbook opt-in flow\n- Keep App Nudge quota under control\n\n*risks:*\n- SAFE-T regression risk (must be 0)\n- X rate limit/credits may pause posting\n- Quota spikes if triggers misfire\n\n*metrics:*\n- app outcomes: ${app.outcomeCount}, taps: ${app.tapCount}, tap_rate: ${(app.tapRate * 100).toFixed(1)}%\n- x_posts_24h: ${xPosts}, tiktok_posts_24h: ${tiktokPosts}`,
        },
      },
    ],
  };

  await sendSlackMessage('#ops', message);
  logger.info('Standup posted', { suffering, crisis, safeT, xCredits, xPosts, tiktokPosts, app });

  return { suffering, crisis, safeT, xCredits, xPosts, tiktokPosts, app };
}

export default {
  runRoundtableStandup,
};
