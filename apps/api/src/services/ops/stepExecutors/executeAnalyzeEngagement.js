import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * メトリクスを分析 → hook_candidates 更新
 *
 * Input: { metrics: Object, postId: string, platform: string }
 * Output: { analysis: string, isHighEngagement: boolean, learnings: string[] }
 * Events: engagement:high or engagement:low
 */
export async function executeAnalyzeEngagement({ input, missionId }) {
  const { metrics, postId, platform } = input;

  if (!metrics) {
    throw new Error('analyze_engagement requires input.metrics from fetch_metrics step');
  }

  const engagementRate = parseFloat(metrics.engagementRate || '0');
  const isHighEngagement = engagementRate > 5.0;

  const analysis = await callLLM(`以下の投稿メトリクスを分析し、学びを3つ箇条書きで:
Platform: ${platform}
Metrics: ${JSON.stringify(metrics)}
Engagement Rate: ${engagementRate}%
判定: ${isHighEngagement ? '高エンゲージメント' : '低エンゲージメント'}`);

  if (postId) {
    const post = platform === 'x'
      ? await prisma.xPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } })
      : await prisma.tiktokPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } });

    if (post?.hookCandidateId) {
      const hook = await prisma.hookCandidate.findUnique({ where: { id: post.hookCandidateId } });
      if (hook) {
        if (platform === 'x') {
          const newSample = hook.xSampleSize + 1;
          const oldSuccesses = Math.round(Number(hook.xEngagementRate) * hook.xSampleSize);
          const newSuccesses = oldSuccesses + (isHighEngagement ? 1 : 0);
          await prisma.hookCandidate.update({
            where: { id: post.hookCandidateId },
            data: {
              xSampleSize: newSample,
              xEngagementRate: newSample > 0 ? newSuccesses / newSample : 0,
              xHighPerformer: (newSample > 0 ? newSuccesses / newSample : 0) > 0.05
            }
          });
        } else {
          const newSample = hook.tiktokSampleSize + 1;
          const oldSuccesses = Math.round(Number(hook.tiktokLikeRate) * hook.tiktokSampleSize);
          const newSuccesses = oldSuccesses + (isHighEngagement ? 1 : 0);
          await prisma.hookCandidate.update({
            where: { id: post.hookCandidateId },
            data: {
              tiktokSampleSize: newSample,
              tiktokLikeRate: newSample > 0 ? newSuccesses / newSample : 0,
              tiktokHighPerformer: (newSample > 0 ? newSuccesses / newSample : 0) > 0.05
            }
          });
        }
      }
    }
  }

  logger.info(`Engagement analysis: ${platform} post ${postId} — ${isHighEngagement ? 'HIGH' : 'LOW'} (${engagementRate}%)`);

  return {
    output: {
      analysis,
      isHighEngagement,
      engagementRate,
      platform
    },
    events: [{
      kind: isHighEngagement ? 'engagement:high' : 'engagement:low',
      tags: ['engagement', isHighEngagement ? 'high' : 'low'],
      payload: { postId, platform, engagementRate, analysis: analysis.substring(0, 200) }
    }]
  };
}
