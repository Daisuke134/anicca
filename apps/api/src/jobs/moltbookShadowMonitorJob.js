import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { detectSuffering } from '../services/sufferingDetectionService.js';

const logger = baseLogger.withContext('MoltbookShadowMonitorJob');

function trimWithEllipsis(text, maxChars) {
  const s = String(text || '');
  if (s.length <= maxChars) return s;
  if (maxChars <= 3) return s.slice(0, maxChars);
  return `${s.slice(0, maxChars - 3)}...`;
}

function generateShadowReply(context) {
  const hook = 'ひと息だけ';
  const content = `読んだよ。今は「正しくする」より、まず「楽にする」を優先しよう。もし可能なら、今の気持ちを10秒だけ観察して、肩を落としてみて。`;
  // Enforce 400 chars total (hook + spacer + content)
  const h = trimWithEllipsis(hook, 120);
  const remaining = Math.max(0, 400 - h.length - 1);
  const c = remaining > 0 ? trimWithEllipsis(content, remaining) : '';
  return { hook: h, content: c };
}

// Synthetic monitor input for Day-0 verification (shadow only, no external posting).
const SHADOW_FEED = [
  { externalPostId: 'moltbook-shadow-1', platformUserId: 'moltbook:shadow', region: 'JP', context: '最近ずっと眠れない。しんどい。', optIn: true },
];

export async function runMoltbookShadowMonitorJob(options = {}) {
  const now = new Date();
  const feed = options.feed || SHADOW_FEED;

  let generated = 0;
  let optInBlocked = 0;
  let crisis = 0;

  for (const item of feed) {
    if (!item.optIn) {
      optInBlocked += 1;
      await prisma.agentAuditLog.create({
        data: {
          eventType: 'moltbook_shadow_optin_blocked',
          platform: 'moltbook',
          requestPayload: { externalPostId: item.externalPostId || null, platformUserId: item.platformUserId || null, region: item.region || null },
          executedBy: 'system',
        },
      });
      continue;
    }

    const detection = detectSuffering({
      context: item.context,
      severityScore: item.severityScore ?? null,
      severity: item.severity ?? null,
      source: 'moltbook_shadow_monitor',
    });

    if (detection.safeTTriggered) crisis += 1;

    for (const eventType of detection.eventTypes) {
      await prisma.agentAuditLog.create({
        data: {
          eventType,
          platform: 'moltbook',
          requestPayload: { externalPostId: item.externalPostId || null, platformUserId: item.platformUserId || null, region: item.region || null, severityScore: detection.severityScore, source: 'shadow_monitor' },
          responsePayload: { detections: detection.detections },
          executedBy: 'system',
        },
      });
    }

    const reply = generateShadowReply(item.context);
    generated += 1;

    await prisma.agentAuditLog.create({
      data: {
        eventType: 'moltbook_shadow_generated',
        platform: 'moltbook',
        requestPayload: { externalPostId: item.externalPostId || null, platformUserId: item.platformUserId || null, region: item.region || null },
        responsePayload: { generated: reply, policy: { shadowMode: true, sendExternal: false, maxChars: 400 } },
        executedBy: 'system',
      },
    });
  }

  const result = { ok: true, now: now.toISOString(), feedCount: feed.length, generated, optInBlocked, crisis };
  logger.info('Moltbook shadow monitor completed', result);
  return result;
}

export default runMoltbookShadowMonitorJob;

