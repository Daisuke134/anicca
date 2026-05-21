import { selectHookThompson } from '../../hookSelector.js';
import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * Hook選択 → LLMでコンテンツ下書き生成
 *
 * Input: { slot?: 'morning'|'evening' }
 * Output: { content: string, hookId: string, hookText: string, platform: string }
 */
export async function executeDraftContent({ input, proposalPayload, skillName }) {
  const platform = skillName === 'tiktok-poster' ? 'tiktok' : 'x';
  const slot = input?.slot || proposalPayload?.slot || 'morning';

  const hooks = await prisma.hookCandidate.findMany({
    where: {
      ...(platform === 'x'
        ? { xSampleSize: { gt: 0 } }
        : { tiktokSampleSize: { gt: 0 } })
    },
    orderBy: { createdAt: 'desc' },
    take: 20
  });

  if (hooks.length === 0) {
    throw new Error('No hook candidates available');
  }

  const selectedHook = selectHookThompson(hooks.map(h => {
    const rate = platform === 'x'
      ? Number(h.xEngagementRate || 0)
      : Number(h.tiktokLikeRate || 0);
    const sampleSize = platform === 'x' ? h.xSampleSize : h.tiktokSampleSize;
    const successCount = Math.round(rate * sampleSize);
    return {
      ...h,
      successCount,
      failureCount: Math.max(0, sampleSize - successCount)
    };
  }));

  const prompt = buildDraftPrompt(selectedHook, platform, slot);
  const content = await callLLM(prompt);

  logger.info(`Draft content generated for ${platform} (hook: ${selectedHook.id})`);

  return {
    output: {
      content,
      hookId: selectedHook.id,
      hookText: selectedHook.text,
      platform
    },
    events: []
  };
}

function buildDraftPrompt(hook, platform, slot) {
  const charLimit = platform === 'x' ? 280 : 2200;
  return `あなたは仏教の行動変容アプリ Anicca のSNSマーケター。
以下のhookをベースに ${platform} 向けの投稿を作成:

Hook: "${hook.text}"
関連する苦しみ: ${hook.targetProblemTypes?.join(', ') || '一般'}
時間帯: ${slot}
文字数制限: ${charLimit}文字以内

ルール:
- 「簡単に習慣化！」等の軽い表現は絶対禁止
- 挫折経験を共感で包むトーン
- 直接的な宣伝・リンクは入れない
- ハッシュタグは2-3個まで`;
}
