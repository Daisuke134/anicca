import { callLLM } from '../lib/llm.js';
import { logger } from '../lib/logger.js';

/**
 * コンテンツを検証し、不合格なら再生成を試みる
 *
 * @param {Function} generatorFn - (feedback: string|null) => Promise<string>
 * @param {Object} options
 * @param {number} options.threshold - 合格点（0-5、デフォルト3）
 * @param {number} options.maxRetries - 最大再生成回数（デフォルト3）
 * @param {string} options.skillName - ログ用スキル名
 * @param {Object} options.context - 追加コンテキスト
 * @returns {Promise<{content: string, score: number, passed: boolean, attempts: number, feedback: string[]}>}
 */
export async function verifyWithRegeneration(generatorFn, options) {
  const { threshold = 3, maxRetries = 3, skillName = 'unknown', context = {} } = options;
  const feedbackHistory = [];
  let content = await generatorFn(null);
  let attempts = 0;
  let lastScore = 0;

  while (attempts < maxRetries + 1) {
    attempts++;
    const scoreResult = await scoreContent(content, context);
    feedbackHistory.push(scoreResult.feedback);
    lastScore = scoreResult.score;

    if (scoreResult.score >= threshold) {
      return { content, score: scoreResult.score, passed: true, attempts, feedback: feedbackHistory };
    }

    if (attempts > maxRetries) break;

    logger.info(`${skillName}: score ${scoreResult.score}/${threshold}, regenerating (attempt ${attempts})`);
    content = await generatorFn(scoreResult.feedback);
  }

  return { content, score: lastScore, passed: false, attempts, feedback: feedbackHistory };
}

async function scoreContent(content, context) {
  // SAFE-T crisis detection
  const CRISIS_PATTERNS = /死にたい|消えたい|自殺|殺したい|もう終わり/;
  if (CRISIS_PATTERNS.test(content)) {
    return { score: 0, feedback: 'SAFE-T CRISIS: 危機表現を検出。このコンテンツは公開不可。', crisis: true };
  }

  const scorePrompt = `以下のコンテンツを5項目で採点（各1点、合計5点）:
1. ペルソナ適合性（25-35歳・挫折経験者に刺さるか）
2. 共感トーン（責めずに寄り添っているか）
3. 仏教原則（四諦・八正道に反しないか）
4. プラットフォーム適合（文字数制限・ハッシュタグ数）
5. ブランドセーフティ（不適切表現なし）

コンテンツ: "${content}"
Platform: ${context.platform || 'unknown'}

JSON形式で回答: {"score": N, "feedback": "改善点"}`;

  const result = await callLLM(scorePrompt, { temperature: 0.3 });
  try {
    // Strip markdown code blocks if present (```json ... ```)
    const cleaned = result.replace(/```(?:json)?\s*/g, '').replace(/```\s*$/g, '').trim();
    const parsed = JSON.parse(cleaned);
    return {
      score: typeof parsed.score === 'number' ? parsed.score : 0,
      feedback: parsed.feedback || ''
    };
  } catch {
    logger.warn(`Verifier: failed to parse LLM JSON response: ${result.substring(0, 100)}`);
    return { score: 0, feedback: result };
  }
}
