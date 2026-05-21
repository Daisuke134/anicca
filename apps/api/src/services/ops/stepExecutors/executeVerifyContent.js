import { verifyWithRegeneration } from '../../verifier.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 生成コンテンツを仏教原則で検証
 *
 * Input: { content: string, hookId: string, platform: string }
 * Output: { content: string, verificationScore: number, passed: boolean, attempts: number }
 */
export async function executeVerifyContent({ input }) {
  const { content, platform } = input;

  if (!content) {
    throw new Error('verify_content requires input.content from previous step');
  }

  const result = await verifyWithRegeneration(
    async (feedback) => {
      if (!feedback) return content;
      return callLLM(`以下のコンテンツを修正してください。
元のコンテンツ: "${content}"
フィードバック: ${feedback}
プラットフォーム: ${platform}`);
    },
    {
      threshold: 3,
      maxRetries: 3,
      skillName: 'verify_content',
      context: { platform }
    }
  );

  logger.info(`Content verification: ${result.passed ? 'PASSED' : 'FAILED'} (score: ${result.score}, attempts: ${result.attempts})`);

  if (!result.passed) {
    throw new Error(`Content verification failed after ${result.attempts} attempts (score: ${result.score}/5)`);
  }

  return {
    output: {
      ...input,
      content: result.content,
      verificationScore: result.score,
      passed: result.passed,
      attempts: result.attempts
    },
    events: []
  };
}
