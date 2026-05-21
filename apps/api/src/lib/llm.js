import OpenAI from 'openai';
import { logger } from './logger.js';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY || 'test-key' });

/**
 * LLMにプロンプトを送信し、レスポンステキストを返す
 *
 * @param {string} prompt - プロンプト文字列
 * @param {Object} [options] - オプション
 * @param {string} [options.model='gpt-4o-mini'] - モデル名
 * @param {number} [options.maxTokens=1000] - 最大トークン数
 * @param {number} [options.temperature=0.7] - 温度
 * @returns {Promise<string>} レスポンステキスト
 */
export async function callLLM(prompt, options = {}) {
  const { model = 'gpt-4o-mini', maxTokens = 1000, temperature = 0.7 } = options;

  try {
    const response = await openai.chat.completions.create({
      model,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: maxTokens,
      temperature
    });
    return response.choices[0]?.message?.content || '';
  } catch (err) {
    logger.error('LLM call failed:', err.message);
    throw new Error(`LLM call failed: ${err.message}`);
  }
}
