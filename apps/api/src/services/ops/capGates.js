import { prisma } from '../../lib/prisma.js';
import { getPolicy } from './policyService.js';

/**
 * Check cap gate for a step kind
 * @param {string} stepKind
 * @returns {Promise<{ok: boolean, reason?: string}>}
 */
export async function checkCapGate(stepKind) {
  const gates = {
    post_x: checkPostXGate,
    post_tiktok: checkPostTiktokGate,
    send_nudge: checkSendNudgeGate
  };

  const gateFn = gates[stepKind];
  if (!gateFn) return { ok: true };
  return gateFn();
}

async function checkPostXGate() {
  const autopost = await getPolicy('x_autopost');
  if (autopost?.enabled === false) {
    return { ok: false, reason: 'x_autopost disabled' };
  }

  const quota = await getPolicy('x_daily_quota');
  const limit = quota?.limit ?? 3;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'tweet_posted',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `X daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}

async function checkPostTiktokGate() {
  const autopost = await getPolicy('tiktok_autopost');
  if (autopost?.enabled === false) {
    return { ok: false, reason: 'tiktok_autopost disabled' };
  }

  const quota = await getPolicy('tiktok_daily_quota');
  const limit = quota?.limit ?? 1;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'tiktok_posted',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `TikTok daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}

async function checkSendNudgeGate() {
  const quota = await getPolicy('nudge_daily_quota');
  const limit = quota?.limit ?? 10;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const count = await prisma.opsEvent.count({
    where: {
      kind: 'nudge_sent',
      createdAt: { gte: todayStart }
    }
  });

  if (count >= limit) {
    return { ok: false, reason: `Nudge daily quota reached (${count}/${limit})` };
  }
  return { ok: true };
}
