import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * trend-hunter が見つけた hook_candidate を評価
 *
 * Input: { eventId: string }
 * Output: { evaluation: string, shouldPost: boolean }
 */
export async function executeEvaluateHook({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload.eventId;
  const event = await prisma.opsEvent.findUnique({ where: { id: eventId } });

  if (!event?.payload?.hookId) {
    return { output: { shouldPost: false, reason: 'no hook in event' }, events: [] };
  }

  const hook = await prisma.hookCandidate.findUnique({
    where: { id: event.payload.hookId }
  });

  if (!hook) {
    return { output: { shouldPost: false, reason: 'hook not found' }, events: [] };
  }

  const evaluation = await callLLM(`以下の hook を X 投稿に使えるか評価:
Hook: "${hook.text}"
Problem Types: ${hook.targetProblemTypes?.join(', ')}
X Engagement Rate: ${Number(hook.xEngagementRate || 0)}

判定基準:
1. ターゲットペルソナ（6-7年挫折した25-35歳）に刺さるか
2. 「簡単に習慣化！」系の軽い表現でないか
3. 共感ベースのトーンか
→ shouldPost: true/false で回答`);

  const shouldPost = evaluation.toLowerCase().includes('true');

  logger.info(`Hook evaluation: ${hook.id} — shouldPost: ${shouldPost}`);

  return {
    output: { evaluation, shouldPost, hookId: hook.id },
    events: shouldPost ? [{
      kind: 'hook:approved_for_post',
      tags: ['hook', 'approved'],
      payload: { hookId: hook.id, hookText: hook.text }
    }] : []
  };
}
