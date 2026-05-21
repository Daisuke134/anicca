import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { sendNudgeInternal } from '../services/mobile/nudgeSendService.js';

const logger = baseLogger.withContext('ProactiveAppNudgeJob');

// "No sensors" policy: send a gentle, proactive nudge on a fixed schedule.
// Idempotency is guaranteed via dedupeKey (and mirrored to agent_audit_logs).

const DEFAULT_SLOTS = ['morning', 'afternoon', 'evening'];

function jstDateString(now = new Date()) {
  // YYYY-MM-DD in JST
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

function buildDedupeKey({ dateJst, slot }) {
  return `app:proactive:${dateJst}:${slot}`;
}

function renderMessage(slot) {
  // Keep it short, empathetic, and non-prescriptive.
  switch (slot) {
    case 'morning':
      return { title: '今日を軽く', message: '起きたての心は繊細。まずは呼吸を1回だけ整えよう。次に、今日いちばん小さくしたい「苦しみ」を1語で名付けてみて。' };
    case 'afternoon':
      return { title: 'いま、ひと息', message: '疲れが溜まりやすい時間。肩を1回だけ落として、目線を遠くに置いてみよう。今の自分に、いちばん優しい一手は何？' };
    case 'evening':
      return { title: '夜の守り', message: '夜は反芻が強くなりがち。今この瞬間だけ、手のひらをゆるめよう。眠る前に「やめたいこと」を1つだけ減らせたら十分。' };
    default:
      return { title: 'ひと息だけ', message: '今この瞬間だけ、呼吸を1回。次に、いちばんつらいところを1語でラベル付けしてみて。' };
  }
}

export async function runProactiveAppNudgeJob(options = {}) {
  const alphaUserId = String(process.env.NUDGE_ALPHA_USER_ID || '').trim();
  if (!alphaUserId) {
    return { ok: false, error: 'NUDGE_ALPHA_USER_ID is required for 1.6.2 alpha routing' };
  }

  const now = options.now ? new Date(options.now) : new Date();
  const dateJst = options.dateJst || jstDateString(now);
  const slot = String(options.slot || '').trim() || DEFAULT_SLOTS[0];

  if (!DEFAULT_SLOTS.includes(slot)) {
    return { ok: false, error: `Invalid slot. Allowed: ${DEFAULT_SLOTS.join(', ')}` };
  }

  const dedupeKey = buildDedupeKey({ dateJst, slot });

  // Skip if we already recorded enqueue for this dedupeKey (fast no-op).
  const existing = await prisma.agentAuditLog.findFirst({
    where: {
      eventType: 'app_proactive_nudge_enqueued',
      requestPayload: { path: ['dedupeKey'], equals: dedupeKey },
    },
    orderBy: { createdAt: 'desc' },
  });
  if (existing) {
    return { ok: true, deduped: true, dedupeKey, dateJst, slot };
  }

  const { title, message } = renderMessage(slot);
  const out = await sendNudgeInternal({
    userId: alphaUserId,
    title,
    message,
    problemType: 'proactive',
    templateId: 'send_nudge',
    metadata: { dateJst, slot, source: 'proactive-app-nudge' },
    dedupeKey,
  });

  await prisma.agentAuditLog.create({
    data: {
      eventType: 'app_proactive_nudge_enqueued',
      platform: 'app',
      requestPayload: { dedupeKey, alphaUserId, dateJst, slot, result: out },
      executedBy: 'system',
    },
  });

  const result = { ok: true, dateJst, slot, dedupeKey, result: out };
  logger.info('Proactive app nudge completed', result);
  return result;
}

export default runProactiveAppNudgeJob;

