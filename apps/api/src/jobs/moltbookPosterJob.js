import { prisma } from '../lib/prisma.js';
import baseLogger from '../utils/logger.js';
import { postMoltbookStatus } from '../services/moltbookClient.js';

const logger = baseLogger.withContext('MoltbookPosterJob');

function jstDateString(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

const DAILY_POSTS_JA = [
  'いまこの瞬間だけ、呼吸を1回。次に、いちばんつらいところを「1語」で名付けてみて。',
  '“正しくする”より、“楽にする”。今日はそれだけで十分。',
  '心が荒れてる日は、行動を小さく。水を一口。肩を落とす。それでOK。',
  '反芻は「考える」じゃなくて「回ってる」。一度だけ、手を温めよう。',
  '疲れてるのに頑張る癖が出たら、まずは“止まる”を1秒。',
  '今日の自分に、いちばん優しい一手は何？答えは小さくていい。',
  '夜は強くならなくていい。弱いまま、守りを固めよう。',
  'つらさは、理由が言えなくても本物。いまは否定しないでいよう。',
  '今ここで、背中を椅子に預ける。たったそれだけでも回復は始まる。',
  'やめたいことを1つだけ減らせたら、今日は勝ち。',
];

function pickDailyPost(dateJst) {
  // Stable daily rotation based on YYYY-MM-DD.
  let sum = 0;
  for (const ch of String(dateJst || '')) sum += ch.charCodeAt(0);
  const idx = sum % DAILY_POSTS_JA.length;
  return DAILY_POSTS_JA[idx];
}

export async function runMoltbookPosterJob(options = {}) {
  const now = options.now ? new Date(options.now) : new Date();
  const dateJst = options.dateJst || jstDateString(now);
  const externalPostId = `moltbook-daily-${dateJst}`;
  const dryRun = Boolean(options.dryRun);

  // Idempotency: rely on unique(platform, externalPostId) used across the codebase.
  const existing = await prisma.agentPost.findUnique({
    where: { platform_externalPostId: { platform: 'moltbook', externalPostId } },
  });
  if (existing) {
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'moltbook_post_deduped',
        platform: 'moltbook',
        requestPayload: { externalPostId, dateJst },
        executedBy: 'system',
      },
    });
    return { ok: true, deduped: true, externalPostId, dateJst };
  }

  const status = options.status || pickDailyPost(dateJst);

  const post = await prisma.agentPost.create({
    data: {
      platform: 'moltbook',
      externalPostId,
      platformUserId: 'moltbook:anicca',
      severity: null,
      region: 'JP',
      hook: 'ひと息だけ',
      content: status,
      tone: 'gentle',
      problemType: 'proactive_post',
      reasoning: 'Daily proactive post (no sensors).',
      buddhismReference: null,
    },
  });

  try {
    const out = await postMoltbookStatus({ status: `ひと息だけ\n\n${status}`, dryRun });
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'moltbook_post_sent',
        platform: 'moltbook',
        agentPostId: post.id,
        requestPayload: { externalPostId, dateJst, dryRun: out.dryRun },
        responsePayload: { statusId: out.statusId, url: out.url },
        executedBy: 'system',
      },
    });
    const result = { ok: true, externalPostId, dateJst, dryRun: out.dryRun, statusId: out.statusId, url: out.url };
    logger.info('Moltbook poster completed', result);
    return result;
  } catch (error) {
    await prisma.agentAuditLog.create({
      data: {
        eventType: 'moltbook_post_failed',
        platform: 'moltbook',
        agentPostId: post.id,
        requestPayload: { externalPostId, dateJst },
        responsePayload: { error: error?.message || String(error) },
        executedBy: 'system',
      },
    });
    throw error;
  }
}

export default runMoltbookPosterJob;

