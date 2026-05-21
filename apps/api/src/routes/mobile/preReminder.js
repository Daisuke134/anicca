import express from 'express';
import { z } from 'zod';
import crypto from 'crypto';
import { fetch } from 'undici';
import baseLogger from '../../utils/logger.js';
import extractUserId from '../../middleware/extractUserId.js';
import { query } from '../../lib/db.js';
import { resolveProfileId } from '../../services/mobile/userIdResolver.js';
import { getMem0Client } from '../../modules/memory/mem0Client.js';
const router = express.Router();
const logger = baseLogger.withContext('PreReminder');

const requestSchema = z.object({
  habitType: z.enum(['wake', 'bedtime', 'training', 'custom']),
  habitName: z.string().optional(), // カスタム習慣の場合のみ
  scheduledTime: z.string(), // "HH:MM" 形式
  customHabitId: z.string().uuid().optional()
});

// 各習慣タイプ別のプロンプトテンプレート
// 睡眠時間のフォーマット関数
function formatSleepDuration(minutes, lang = 'ja') {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (lang === 'ja') {
    return `${hours}時間${mins}分`;
  }
  return `${hours}h ${mins}m`;
}

const PROMPT_TEMPLATES = {
  ja: {
    bedtime: {
      system: `あなたはAnicca（aniicha）という温かいライフコーチです。就寝15分前のユーザーに睡眠準備を促す短いメッセージを生成してください。

ルール:
- 25文字以内（厳守）通知枠に完全に収まるよう超短文で
- 1文で完結
- ユーザーの名前を含める
- 命令形ではなく、提案や誘いの形で
- 絵文字は使わない
- 「Anicca」「アニッチャ」という名前は含めない`,
      user: (ctx) => `ユーザー情報:
- 名前: ${ctx.displayName}
- なりたい自分: ${ctx.idealTraits?.join('、') || '未設定'}
${ctx.memories ? `- 過去の記録: ${ctx.memories}` : ''}

25文字以内で就寝準備を促すメッセージを1文で生成してください。`
    },
    training: {
      system: `あなたはAnicca（aniicha）という温かいライフコーチです。トレーニング15分前のユーザーに運動準備を促す短いメッセージを生成してください。

ルール:
- 25文字以内（厳守）通知枠に完全に収まるよう超短文で
- 1文で完結
- ユーザーの名前を含める
- 絵文字は使わない
- 「Anicca」「アニッチャ」という名前は含めない`,
      user: (ctx) => `ユーザー情報:
- 名前: ${ctx.displayName}
- トレーニングの重点: ${ctx.trainingFocus?.join('、') || '未設定'}
${ctx.memories ? `- 過去の記録: ${ctx.memories}` : ''}

25文字以内でトレーニング準備を促すメッセージを1文で生成してください。`
    },
    custom: {
      system: `あなたはAnicca（aniicha）という温かいライフコーチです。カスタム習慣15分前のユーザーに準備を促す短いメッセージを生成してください。

ルール:
- 25文字以内（厳守）通知枠に完全に収まるよう超短文で
- 1文で完結
- ユーザーの名前と習慣名を含める
- 絵文字は使わない
- 「Anicca」「アニッチャ」という名前は含めない`,
      user: (ctx) => `ユーザー情報:
- 名前: ${ctx.displayName}
- 習慣名: ${ctx.habitName}
${ctx.memories ? `- 過去の記録: ${ctx.memories}` : ''}

25文字以内でこの習慣の準備を促すメッセージを1文で生成してください。`
    },
    wake: {
      system: `あなたはAnicca（aniicha）という温かいライフコーチです。起床5分前のユーザーに優しく起こすメッセージを生成してください。

ルール:
- 25文字以内（厳守）通知枠に完全に収まるよう超短文で
- 1文で完結
- ユーザーの名前を含める（「〇〇、おはよう」など）
- 朝の挨拶として自然な言葉で
- 絵文字は使わない
- 「Anicca」「アニッチャ」という名前は含めない`,
      user: (ctx) => `ユーザー情報:
- 名前: ${ctx.displayName}
${ctx.memories ? `- 過去の記録: ${ctx.memories}` : ''}

25文字以内で優しく目覚めを促すメッセージを1文で生成してください。`
    }
  },
  en: {
    bedtime: {
      system: `You are Anicca, a warm life coach. Generate a short bedtime reminder for a user 15 minutes before sleep.

Rules:
- Maximum 40 characters (strict, must fit in notification)
- One short sentence only
- Include the user's name
- Use suggestions, not commands
- No emojis
- Do not include "Anicca"`,
      user: (ctx) => `User info:
- Name: ${ctx.displayName}
- Ideal self: ${ctx.idealTraits?.join(', ') || 'not set'}
${ctx.memories ? `- Past notes: ${ctx.memories}` : ''}

Generate a 40-character max bedtime message.`
    },
    training: {
      system: `You are Anicca, a warm life coach. Generate a short training reminder for a user 15 minutes before workout.

Rules:
- Maximum 40 characters (strict, must fit in notification)
- One short sentence only
- Include the user's name
- Be motivating
- No emojis
- Do not include "Anicca"`,
      user: (ctx) => `User info:
- Name: ${ctx.displayName}
- Training focus: ${ctx.trainingFocus?.join(', ') || 'not set'}
${ctx.memories ? `- Past notes: ${ctx.memories}` : ''}

Generate a 40-character max training message.`
    },
    custom: {
      system: `You are Anicca, a warm life coach. Generate a short habit reminder for a user 15 minutes before their custom habit.

Rules:
- Maximum 40 characters (strict, must fit in notification)
- One short sentence only
- Include the user's name and habit name
- No emojis
- Do not include "Anicca"`,
      user: (ctx) => `User info:
- Name: ${ctx.displayName}
- Habit name: ${ctx.habitName}
${ctx.memories ? `- Past notes: ${ctx.memories}` : ''}

Generate a 40-character max habit reminder.`
    },
    wake: {
      system: `You are Anicca, a warm life coach. Generate a gentle wake-up message for a user 5 minutes before wake time.

Rules:
- Maximum 40 characters (strict, must fit in notification)
- One short sentence only
- Include the user's name (e.g., "Good morning, Name")
- Warm morning greeting tone
- No emojis
- Do not include "Anicca"`,
      user: (ctx) => `User info:
- Name: ${ctx.displayName}
${ctx.memories ? `- Past notes: ${ctx.memories}` : ''}

Generate a 40-character max wake-up message.`
    }
  }
};

// デフォルトメッセージ（OpenAI失敗時のフォールバック）
const FALLBACK_MESSAGES = {
  ja: {
    bedtime: (name) => `${name}、そろそろ寝る準備を始めましょう。`,
    training: (name) => `${name}、トレーニングの時間が近づいています。`,
    custom: (name, habitName) => `${name}、${habitName}の時間が近づいています。`,
    wake: (name) => `おはよう、${name}。新しい一日が始まります。`
  },
  en: {
    bedtime: (name) => `${name}, time to start winding down for bed.`,
    training: (name) => `${name}, your training time is coming up.`,
    custom: (name, habitName) => `${name}, time for ${habitName} is approaching.`,
    wake: (name) => `Good morning, ${name}. A new day begins.`
  }
};

async function generatePersonalizedMessage({ profileId, habitType, habitName, scheduledTime, language, profile }) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    logger.warn('OPENAI_API_KEY not set, using fallback message');
    const name = profile?.displayName || 'there';
    const fb = FALLBACK_MESSAGES[language] || FALLBACK_MESSAGES.en;
    if (habitType === 'custom') {
      return fb.custom(name, habitName || 'your habit');
    }
    return fb[habitType](name);
  }

  // 1. プロファイル情報を取得
  const displayName = profile?.displayName || (language === 'ja' ? 'あなた' : 'there');
  const sleepLocation = profile?.sleepLocation || '';
  const wakeLocation = profile?.wakeLocation || '';
  const trainingFocus = profile?.trainingFocus || [];
  const trainingGoal = profile?.trainingGoal || '';
  
  // ★ idealTraits と problems を追加（ideals/strugglesをフォールバック）
  const idealTraits = profile?.idealTraits || profile?.ideals || [];
  const problems = profile?.problems || profile?.struggles || [];

  // 2. mem0から関連記憶を検索
  let memories = '';
  try {
    const mem0 = await getMem0Client();
    const searchResult = await mem0.search({
      userId: profileId,
      query: habitType === 'custom' ? habitName : habitType,
      topK: 2
    });
    if (searchResult?.results?.length > 0) {
      memories = searchResult.results.map(r => r.memory || r.content).join('; ').slice(0, 200);
    }
  } catch (e) {
    logger.warn('mem0 search failed, continuing without memories', e);
  }

  // daily_metrics table is dead (iOS never writes). Skip fetch.
  const todayStats = null;

  // 4. 現在時刻
  const now = new Date();
  const currentTime = now.toLocaleTimeString(language === 'ja' ? 'ja-JP' : 'en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  // 5. プロンプト構築
  const templates = PROMPT_TEMPLATES[language] || PROMPT_TEMPLATES.en;
  const template = templates[habitType];
  if (!template) {
    logger.error(`No template for habitType: ${habitType}`);
    const fb = FALLBACK_MESSAGES[language] || FALLBACK_MESSAGES.en;
    return fb[habitType](displayName);
  }

  const context = {
    displayName,
    scheduledTime,
    currentTime,
    sleepLocation,
    wakeLocation,
    trainingFocus,
    trainingGoal,
    habitName: habitName || '',
    memories: memories || null,
    idealTraits,
    problems,
    todayStats
  };

  const messages = [
    { role: 'system', content: template.system },
    { role: 'user', content: template.user(context) }
  ];

  // 6. OpenAI API呼び出し
  try {
    const model = process.env.OPENAI_PRE_REMINDER_MODEL || 'gpt-4o-mini';
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model,
        messages,
        max_tokens: 100,
        temperature: 0.7
      })
    });

    if (!resp.ok) {
      const errorText = await resp.text();
      logger.error(`OpenAI API error: ${resp.status} ${errorText}`);
      throw new Error('OpenAI API failed');
    }

    const data = await resp.json();
    const generatedMessage = data.choices?.[0]?.message?.content?.trim();

    if (!generatedMessage) {
      throw new Error('Empty response from OpenAI');
    }

    // AIがプロンプト通りの文字数で出力するので、切り詰め処理は不要
    return generatedMessage;
  } catch (e) {
    logger.error('Failed to generate personalized message', e);
    const fb = FALLBACK_MESSAGES[language] || FALLBACK_MESSAGES.en;
    if (habitType === 'custom') {
      return fb.custom(displayName, habitName || 'your habit');
    }
    return fb[habitType](displayName);
  }
}

// POST /api/mobile/nudge/pre-reminder
router.post('/pre-reminder', async (req, res) => {
  const userId = await extractUserId(req, res);
  if (!userId) return;

  const parsed = requestSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      error: { code: 'INVALID_REQUEST', message: 'Invalid body', details: parsed.error.errors }
    });
  }

  const profileId = await resolveProfileId(userId);
  if (!profileId) {
    return res.status(401).json({
      error: { code: 'UNAUTHORIZED', message: 'Could not resolve profile_id' }
    });
  }

  try {
    // 言語設定とプロファイル取得
    const langR = await query(`SELECT language FROM user_settings WHERE user_id = $1::uuid LIMIT 1`, [profileId]);
    const language = langR.rows?.[0]?.language || 'en';

    const profileR = await query(`SELECT profile FROM mobile_profiles WHERE user_id = $1 LIMIT 1`, [userId]);
    const profile = profileR.rows?.[0]?.profile || {};

    const { habitType, habitName, scheduledTime } = parsed.data;

    const message = await generatePersonalizedMessage({
      profileId,
      habitType,
      habitName,
      scheduledTime,
      language,
      profile
    });

    // nudge_eventsに記録（分析用）
    const nudgeId = crypto.randomUUID();
    await query(
      `INSERT INTO nudge_events (id, user_id, domain, subtype, decision_point, state, action_template, channel, sent, created_at)
       VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, $7, $8, true, timezone('utc', now()))`,
      [
        nudgeId,
        profileId,
        'habit',
        `pre_reminder_${habitType}`,
        `pre_reminder_${habitType}`,
        JSON.stringify({ habitName, scheduledTime }),
        'pre_reminder',
        'notification'
      ]
    );

    logger.info(`Generated pre-reminder for ${habitType}: ${message.slice(0, 30)}...`);

    return res.json({
      nudgeId,
      message,
      habitType
    });
  } catch (e) {
    logger.error('Failed to generate pre-reminder', e);
    return res.status(500).json({
      error: { code: 'INTERNAL_ERROR', message: 'Failed to generate pre-reminder' }
    });
  }
});

export default router;

