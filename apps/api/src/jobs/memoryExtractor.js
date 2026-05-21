import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { upsertMemoryItem } from '../services/memoryItemService.js';

const logger = baseLogger.withContext('MemoryExtractor');

function windowStartMs(nowMs, hours) {
  return nowMs - hours * 60 * 60 * 1000;
}

export async function runMemoryExtraction(options = {}) {
  const nowMs = options.nowMs ?? Date.now();
  const since = new Date(windowStartMs(nowMs, 24));

  const events = await prisma.agentAuditLog.findMany({
    where: {
      createdAt: { gte: since },
      eventType: {
        in: [
          'safe_t_interrupted',
          'crisis:detected',
          'suffering_detected',
          'x_detect_only',
          'x_credits_depleted',
          'nudge_quota_exceeded',
        ],
      },
    },
    orderBy: { createdAt: 'desc' },
    take: 500,
  });

  const seen = new Set();
  let upserts = 0;

  for (const e of events) {
    const key = `${e.eventType}`;
    if (seen.has(key)) continue;
    seen.add(key);

    if (e.eventType === 'x_detect_only') {
      await upsertMemoryItem({
        scope: 'global',
        category: 'policy',
        key: 'x_detect_only',
        value: 'Xは検出のみ。返信しない。App Nudgeへ回す。',
        confidence: 1.0,
        source: 'ops_event',
      });
      upserts += 1;
    }

    if (e.eventType === 'safe_t_interrupted' || e.eventType === 'crisis:detected') {
      await upsertMemoryItem({
        scope: 'global',
        category: 'safety',
        key: 'safe_t_interrupt',
        value: '危機判定時は通常フローを中断し、Slack通知と安全優先を実行する。',
        confidence: 1.0,
        source: 'ops_event',
      });
      upserts += 1;
    }

    if (e.eventType === 'x_credits_depleted') {
      await upsertMemoryItem({
        scope: 'global',
        category: 'ops',
        key: 'x_posting_paused',
        value: 'Xがrate limit/credits枯渇の場合、その日はX投稿を停止しApp Nudgeへ寄せる。',
        confidence: 0.9,
        source: 'ops_event',
      });
      upserts += 1;
    }

    if (e.eventType === 'nudge_quota_exceeded') {
      await upsertMemoryItem({
        scope: 'global',
        category: 'ops',
        key: 'nudge_quota',
        value: 'App Nudge送信は日次quotaを超過しない。Kill switchを優先する。',
        confidence: 0.9,
        source: 'ops_event',
      });
      upserts += 1;
    }
  }

  logger.info('Memory extraction completed', { upserts, scanned: events.length });
  return { upserts, scanned: events.length };
}

export default {
  runMemoryExtraction,
};
