import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { sendNudgeInternal } from '../services/mobile/nudgeSendService.js';

const logger = baseLogger.withContext('AppNudgeSenderJob');

function buildDedupeKey(audit) {
  const externalPostId = audit?.requestPayload?.externalPostId || null;
  const platform = audit?.platform || 'unknown';
  if (externalPostId) return `${platform}:${externalPostId}`;
  return `${platform}:audit:${audit.id}`;
}

function renderMessage(audit) {
  const platform = audit?.platform || 'unknown';
  const score = audit?.requestPayload?.severityScore;
  const suffix = score != null ? ` (score=${Number(score).toFixed(2)})` : '';

  // Keep it short, empathetic, and non-prescriptive.
  return `今、しんどさを検出しました${suffix}。まずは深呼吸を1回。次に、いま一番つらいところを「1語」だけ心の中でラベル付けしてみて。`;
}

export async function runAppNudgeSenderJob(options = {}) {
  const nowMs = options.nowMs ?? Date.now();
  const sinceMs = options.sinceMs ?? (nowMs - 10 * 60 * 1000);
  const since = new Date(sinceMs);
  const alphaUserId = String(process.env.NUDGE_ALPHA_USER_ID || '').trim();

  if (!alphaUserId) {
    return { ok: false, error: 'NUDGE_ALPHA_USER_ID is required for 1.6.2 alpha routing' };
  }

  const recent = await prisma.agentAuditLog.findMany({
    where: {
      eventType: 'suffering_detected',
      createdAt: { gte: since },
    },
    orderBy: { createdAt: 'asc' },
    take: 50,
  });

  let considered = 0;
  let enqueued = 0;
  let deduped = 0;
  let skipped = 0;

  for (const audit of recent) {
    considered += 1;
    const dedupeKey = buildDedupeKey(audit);

    // Skip if we already recorded enqueue for this dedupeKey.
    const existing = await prisma.agentAuditLog.findFirst({
      where: {
        eventType: 'app_nudge_enqueued',
        requestPayload: { path: ['dedupeKey'], equals: dedupeKey },
      },
      orderBy: { createdAt: 'desc' },
    });
    if (existing) {
      skipped += 1;
      continue;
    }

    const out = await sendNudgeInternal({
      userId: alphaUserId,
      message: renderMessage(audit),
      title: 'いま、少しだけ',
      problemType: 'suffering_detected',
      templateId: 'send_nudge',
      metadata: {
        sourceAuditId: audit.id,
        platform: audit.platform || null,
        externalPostId: audit?.requestPayload?.externalPostId || null,
      },
      dedupeKey,
    });

    if (out?.deduped) {
      deduped += 1;
    } else if (out?.sent) {
      enqueued += 1;
    } else {
      // quota/kill switch/etc.
      skipped += 1;
    }

    await prisma.agentAuditLog.create({
      data: {
        eventType: 'app_nudge_enqueued',
        platform: 'app',
        requestPayload: {
          dedupeKey,
          alphaUserId,
          sourceAuditId: audit.id,
          result: out,
        },
        executedBy: 'system',
      },
    });
  }

  const result = { ok: true, since: since.toISOString(), considered, enqueued, deduped, skipped };
  logger.info('App nudge sender job completed', result);
  return result;
}

export default runAppNudgeSenderJob;

