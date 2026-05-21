/**
 * Phase 7+8: LLM生成Nudge - Cron Job
 *
 * 毎朝5:00 JST (20:00 UTC) に実行
 * Day 1: ルールベース、Day 2+: LLMで生成
 *
 * Railway Cron Schedule: 0 20 * * *
 * 環境変数: CRON_MODE=nudges
 */

import pg from 'pg';
import crypto from 'crypto';
import {
  shouldUseLLM,
  generateRuleBasedNudges
} from './nudgeHelpers.js';
import { classifyUserType } from '../services/userTypeService.js';
import { runCommanderAgent, normalizeToDecision, generateRuleBasedFallback, validateNoDuplicates } from '../agents/commander.js';
import { runCrossPlatformSync } from './syncCrossPlatform.js';
import { runAggregateTypeStats } from './aggregateTypeStats.js';
import { collectAllGrounding } from '../agents/groundingCollectors.js';
import { logCommanderDecision, buildSlackNudgeSummary, sendSlackNotification } from '../agents/reasoningLogger.js';
import { replaceDuplicates } from './duplicateReplacement.js';

const { Pool } = pg;

// 直接環境変数から取得（environment.jsを使わない）
const DATABASE_URL = process.env.DATABASE_URL;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

if (!DATABASE_URL) {
  console.error('❌ DATABASE_URL is not set');
  process.exit(1);
}

if (!OPENAI_API_KEY) {
  console.error('❌ OPENAI_API_KEY is not set');
  process.exit(1);
}

// DB接続
const pool = new Pool({
  connectionString: DATABASE_URL,
  max: 5,
  idleTimeoutMillis: 30_000,
});

async function query(text, params) {
  const client = await pool.connect();
  try {
    return await client.query(text, params);
  } finally {
    client.release();
  }
}

// 問題タイプからスケジュール時刻を取得
function getScheduledHourForProblem(problem) {
  const scheduleMap = {
    staying_up_late: 21,
    cant_wake_up: 6,
    self_loathing: 7,
    rumination: 7,
    procrastination: 9,
    anxiety: 7,
    lying: 8,
    bad_mouthing: 8,
    porn_addiction: 22,
    alcohol_dependency: 18,
    anger: 9,
    obsessive: 9,
    loneliness: 12
  };
  return scheduleMap[problem] || 9;
}

// ユーザーの過去フィードバックを取得（パーソナライズ用）
async function getUserFeedback(userId, problem) {
  const result = await query(`
    SELECT
      ne.state->>'hook' as hook,
      ne.state->>'content' as content,
      ne.state->>'tone' as tone,
      no.reward,
      no.signals->>'outcome' as outcome,
      no.signals->>'thumbsUp' as thumbs_up,
      no.signals->>'thumbsDown' as thumbs_down
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.subtype = $2
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    ORDER BY ne.created_at DESC
    LIMIT 20
  `, [userId, problem]);

  const rows = result.rows;
  if (rows.length === 0) return null;

  // 成功例（reward=1 または thumbsUp）
  const successful = rows
    .filter(r => r.reward === 1 || r.thumbs_up === 'true')
    .slice(0, 3)
    .map(r => `- "${r.hook}" → "${r.content}" (tone: ${r.tone})`);

  // 失敗例（reward=0 または thumbsDown または outcome=ignored）
  const failed = rows
    .filter(r => r.reward === 0 || r.thumbs_down === 'true' || r.outcome === 'ignored')
    .slice(0, 3)
    .map(r => `- "${r.hook}" → "${r.content}" (tone: ${r.tone})`);

  // 好まれるトーン（成功例から抽出）
  const successfulTones = rows
    .filter(r => r.reward === 1 || r.thumbs_up === 'true')
    .map(r => r.tone)
    .filter(Boolean);
  const preferredTone = successfulTones.length > 0
    ? [...new Set(successfulTones)].join(', ')
    : null;

  // 避けるべきトーン（失敗例から抽出）
  const failedTones = rows
    .filter(r => r.reward === 0 || r.thumbs_down === 'true')
    .map(r => r.tone)
    .filter(Boolean);
  const avoidedTone = failedTones.length > 0
    ? [...new Set(failedTones)].join(', ')
    : null;

  return { successful, failed, preferredTone, avoidedTone };
}

// 1.5.0: Get user type from DB or compute on-the-fly
async function getUserTypeForNudge(userId, problems) {
  // Try DB first
  const dbResult = await query(
    `SELECT primary_type, type_scores, confidence FROM user_type_estimates WHERE user_id = $1::uuid`,
    [userId]
  );
  if (dbResult.rows.length > 0) {
    const row = dbResult.rows[0];
    return { primaryType: row.primary_type, scores: row.type_scores, confidence: Number(row.confidence) };
  }
  // Fallback: compute from problems
  return classifyUserType(problems);
}

// 1.5.0: Get cross-user patterns from type_stats (only if data exists)
// 言語別の文字数制限
const CHAR_LIMITS = {
  ja: { hook: 12, content: 45 },
  en: { hook: 25, content: 100 }
};

// プロンプトを構築（パーソナライズ対応）
function buildPrompt(problem, preferredLanguage = 'en', feedback = null) {
  const isJapanese = preferredLanguage === 'ja';
  const limits = CHAR_LIMITS[preferredLanguage] || CHAR_LIMITS.en;

  const problemNamesJa = {
    staying_up_late: '夜更かし',
    cant_wake_up: '朝起きられない',
    self_loathing: '自己嫌悪',
    rumination: '反芻思考',
    procrastination: '先延ばし',
    anxiety: '不安',
    lying: '嘘をつく',
    bad_mouthing: '悪口',
    porn_addiction: 'ポルノ依存',
    alcohol_dependency: 'アルコール依存',
    anger: '怒り',
    obsessive: '強迫観念',
    loneliness: '孤独'
  };

  const problemNamesEn = {
    staying_up_late: 'Staying Up Late',
    cant_wake_up: 'Can\'t Wake Up',
    self_loathing: 'Self-Loathing',
    rumination: 'Rumination',
    procrastination: 'Procrastination',
    anxiety: 'Anxiety',
    lying: 'Lying',
    bad_mouthing: 'Bad-Mouthing',
    porn_addiction: 'Porn Addiction',
    alcohol_dependency: 'Alcohol Dependency',
    anger: 'Anger',
    obsessive: 'Obsessive Thoughts',
    loneliness: 'Loneliness'
  };

  const problemNames = isJapanese ? problemNamesJa : problemNamesEn;
  const problemName = problemNames[problem] || problem;

  const toneDefinitions = isJapanese
    ? `- strict: 厳しい、直接的、言い訳を許さない。例：「まだ寝てる？」
- gentle: 優しい、共感的、寄り添う。例：「大丈夫」
- logical: 論理的、データや事実ベース。例：「睡眠不足は危険」
- provocative: 挑発的、プライドを刺激。例：「また負ける？」
- philosophical: 哲学的、深い問い。例：「この5分が…」`
    : `- strict: Direct, no excuses. Example: "Still in bed?"
- gentle: Kind, empathetic. Example: "It's okay, one step at a time."
- logical: Data-driven, factual. Example: "Sleep deprivation cuts judgment by 40%."
- provocative: Challenges pride. Example: "Gonna lose again?"
- philosophical: Deep questions. Example: "These 5 minutes could change everything."`;

  const exampleOutput = isJapanese
    ? `{
  "hook": "まだ布団の中？",
  "content": "あと5分で起きたら、今日は違う1日になる。",
  "tone": "strict",
  "reasoning": "Strict tone worked 3 times for this user. Gentle was ignored."
}`
    : `{
  "hook": "Still scrolling?",
  "content": "Put the phone down. Tomorrow-you will thank you.",
  "tone": "strict",
  "reasoning": "Strict tone worked for this user. Gentle was ignored twice."
}`;

  const languageInstruction = isJapanese
    ? '4. Use Japanese. Natural, conversational, not robotic.'
    : '4. Use English. Natural, conversational, not robotic.';

  // フィードバックセクションを構築（パーソナライズの核心）
  let feedbackSection = '';
  if (feedback) {
    feedbackSection += '\n## User Profile';
    if (feedback.preferredTone) {
      feedbackSection += `\n- Preferred tone: ${feedback.preferredTone} (this person responds well to this)`;
    }
    if (feedback.avoidedTone) {
      feedbackSection += `\n- Avoided tone: ${feedback.avoidedTone} (this person ignores or dislikes this)`;
    }
    feedbackSection += '\n';

    if (feedback.successful && feedback.successful.length > 0) {
      feedbackSection += `\n## ✅ What Worked (These hooks got tapped/liked)\n`;
      feedbackSection += feedback.successful.join('\n') + '\n';
    }

    if (feedback.failed && feedback.failed.length > 0) {
      feedbackSection += `\n## ❌ What Failed (These hooks were ignored/disliked)\n`;
      feedbackSection += feedback.failed.join('\n') + '\n';
    }
  }

  return `You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

## Your Mission
Generate a notification hook and one-screen content that will make this specific person take action. The notification alone should be powerful enough to change behavior.

## Problem Type
${problemName}
${feedbackSection}
## Tone Definitions
${toneDefinitions}

## Output Requirements

### Hook (Notification)
- Maximum ${limits.hook} characters (CRITICAL - must fit in notification preview)
- Action-oriented
- Uses the tone that WORKS for this person (see User Profile above)
- AVOID the tone that failed (see What Failed above)

### Content (One-Screen)
- Maximum ${limits.content} characters
- Specific action or insight
- Directly related to the hook

## Output Format (JSON)

${exampleOutput}

## Critical Rules
1. NEVER exceed character limits. Hook ≤ ${limits.hook}, Content ≤ ${limits.content}.
2. Output a SINGLE JSON object, not an array.
3. If past hooks failed, TRY SOMETHING DIFFERENT. Learn from What Worked and What Failed.
${languageInstruction}`;
}

// LLM出力バリデーション
function validateLLMOutput(output) {
  if (!output || typeof output !== 'object') return null;
  if (typeof output.hook !== 'string' || output.hook.length === 0) return null;
  if (typeof output.content !== 'string' || output.content.length === 0) return null;
  if (!['strict', 'gentle', 'logical', 'provocative', 'philosophical'].includes(output.tone)) return null;
  if (typeof output.reasoning !== 'string') return null;
  return output;
}

// メイン処理 (Phase 7+8)
export async function runGenerateNudges() {
  console.log('✅ [GenerateNudges] Starting Phase 7+8 nudge generation cron job');

  // Step 0a: Cross-user learning stats aggregation (optional, non-fatal)
  try {
    await runAggregateTypeStats(query);
    console.log('✅ [GenerateNudges] type_stats aggregation completed');
  } catch (err) {
    console.warn(`⚠️ [GenerateNudges] type_stats aggregation failed (non-fatal): ${err.message}`);
  }

  // Step 0b: Cross-Platform Learning — 前日のメトリクスを処理
  try {
    console.log('🔁 [GenerateNudges] Running cross-platform learning pipeline...');
    await runCrossPlatformSync(query);
    console.log('✅ [GenerateNudges] Cross-platform learning complete.');
  } catch (err) {
    console.warn(`⚠️ [GenerateNudges] Cross-platform learning failed (non-fatal): ${err?.message || err}`);
  }

  // 1. 全アクティブユーザーを取得（v1.6.0: app_version追加）
  const usersResult = await query(`
    SELECT DISTINCT
      mp.device_id as profile_id,
      mp.user_id,
      COALESCE(mp.profile->'struggles', mp.profile->'problems', '[]'::jsonb) as problems,
      COALESCE(mp.profile->>'preferredLanguage', 'en') as preferred_language,
      COALESCE(mp.profile->>'appVersion', '1.0.0') as app_version
    FROM mobile_profiles mp
    WHERE (
      (mp.profile->'struggles' IS NOT NULL AND jsonb_array_length(mp.profile->'struggles') > 0)
      OR (mp.profile->'problems' IS NOT NULL AND jsonb_array_length(mp.profile->'problems') > 0)
    )
  `);

  const users = usersResult.rows;
  console.log(`✅ [GenerateNudges] Found ${users.length} users with problems`);

  let totalGenerated = 0;
  let totalRuleBased = 0;
  let totalErrors = 0;
  const nudgeResults = [];  // Phase 6: collect results for Slack summary

  // 2. 各ユーザーに対して処理
  for (const user of users) {
    const problems = user.problems || [];
    const preferredLanguage = user.preferred_language || 'en';
    const appVersion = user.app_version || '1.0.0';  // v1.6.0: バージョン分岐用
    const limits = CHAR_LIMITS[preferredLanguage] || CHAR_LIMITS.en;

    try {
      // 1.5.0: Get user type for cross-user learning
      const userTypeResult = await getUserTypeForNudge(user.user_id, problems);
      const userType = userTypeResult.primaryType;

      // Phase 7+8: Day 1判定
      const useLLM = await shouldUseLLM(query, user.user_id);
      let scheduleResult;

      if (useLLM) {
        // Day 2+: Commander Agent（1.6.0）
        console.log(`🪷 [GenerateNudges] User ${user.user_id}: Day 2+ → Commander Agent (v${appVersion})`);

        let decision = null;
        let slotTable = null;
        
        // 1. Collect all grounding variables (parallel DB queries)
        try {
          const groundingResult = await collectAllGrounding(
            query, user.user_id, problems, preferredLanguage, appVersion
          );
          slotTable = groundingResult.slotTable;
          
          // Skip Commander if no slots (user has no problems selected)
          if (slotTable.length === 0) {
            console.log(`⚠️ [GenerateNudges] User ${user.user_id}: No slots (no problems selected), skipping`);
            decision = {
              userId: user.user_id,
              appNudges: [],
              tiktokPosts: [],
              xPosts: [],
              overallStrategy: 'No problems selected',
              rootCauseHypothesis: null,
              frequencyDecision: { count: 0, reasoning: 'No problems selected' },
            };
          } else {
            // 2. Run Commander Agent
            try {
              const agentOutput = await runCommanderAgent({ 
                grounding: groundingResult.grounding, 
                slotCount: slotTable.length 
              });

              // 3. Normalize to CommanderDecision (guardrails + enrichment)
              decision = normalizeToDecision(agentOutput, slotTable, user.user_id, preferredLanguage);

              // ========== 重複チェック & 置換 (Patch 6-B) ==========
              const dupCheck = validateNoDuplicates(decision.appNudges || []);
              if (!dupCheck.valid) {
                console.warn(`⚠️ [GenerateNudges] Duplicate content detected for ${user.user_id}, replacing...`);
                for (const dup of dupCheck.duplicates) {
                  console.warn(`  - [${dup.type}] slot ${dup.slotIndex}: "${dup.text}"`);
                }

                // Replace duplicates with unique fallbacks
                decision.appNudges = replaceDuplicates(decision.appNudges, preferredLanguage);

                // Final validation - should never fail after replacement
                const finalCheck = validateNoDuplicates(decision.appNudges);
                if (!finalCheck.valid) {
                  console.error(`❌ [GenerateNudges] CRITICAL: Duplicates remain after replacement! Falling back to rule-based.`);
                  // Fall through to rule-based fallback
                  throw new Error('Duplicate replacement failed');
                }
              }

              // 4. Store raw agent output for audit (notification_schedules)
              try {
                await query(
                  `INSERT INTO notification_schedules (id, user_id, schedule, agent_raw_output, created_at)
                   VALUES ($1::uuid, $2::uuid, $3::jsonb, $4::jsonb, timezone('utc', now()))
                   ON CONFLICT (user_id) DO UPDATE SET
                     schedule = EXCLUDED.schedule,
                     agent_raw_output = EXCLUDED.agent_raw_output,
                     created_at = EXCLUDED.created_at`,
                  [
                    crypto.randomUUID(),
                    user.user_id,
                    JSON.stringify(decision),
                    JSON.stringify(agentOutput),
                  ]
                );
              } catch (nsErr) {
                console.warn(`⚠️ [GenerateNudges] notification_schedules save failed (non-fatal): ${nsErr.message}`);
              }

              // Phase 6: Log Commander decision
              logCommanderDecision(user.user_id, decision, 'llm', preferredLanguage);
              nudgeResults.push({ userId: user.user_id, decision, mode: 'llm' });
              
            } catch (commanderErr) {
              // Commander failed but we have slotTable → use generateRuleBasedFallback
              console.error(`❌ [GenerateNudges] Commander Agent failed for ${user.user_id}: ${commanderErr.message}`);
              console.warn(`⚠️ [GenerateNudges] Using generateRuleBasedFallback (schema-compliant)`);
              
              const fallbackOutput = generateRuleBasedFallback(slotTable, preferredLanguage);
              decision = normalizeToDecision(fallbackOutput, slotTable, user.user_id, preferredLanguage);

              // ========== 重複チェック & 置換 (Patch 6-B) - Fallback path ==========
              const dupCheckFallback = validateNoDuplicates(decision.appNudges || []);
              if (!dupCheckFallback.valid) {
                console.warn(`⚠️ [GenerateNudges] Duplicate in rule-based fallback for ${user.user_id}, replacing...`);
                for (const dup of dupCheckFallback.duplicates) {
                  console.warn(`  - [${dup.type}] slot ${dup.slotIndex}: "${dup.text}"`);
                }
                decision.appNudges = replaceDuplicates(decision.appNudges, preferredLanguage);

                // Final validation - log error but don't throw (no further fallback available)
                const finalFallbackCheck = validateNoDuplicates(decision.appNudges);
                if (!finalFallbackCheck.valid) {
                  console.error(`❌ [GenerateNudges] CRITICAL: Duplicates remain in fallback after replacement for ${user.user_id}`);
                  // Last resort: disable duplicate nudges to prevent user seeing same content
                  for (const dup of finalFallbackCheck.duplicates) {
                    const nudge = decision.appNudges.find(n => n.slotIndex === dup.slotIndex);
                    if (nudge) {
                      nudge.enabled = false;
                      nudge.reasoning = (nudge.reasoning || '') + ' [guardrail: duplicate disabled]';
                    }
                  }
                }
              }
              
              // Store fallback output for audit
              try {
                await query(
                  `INSERT INTO notification_schedules (id, user_id, schedule, agent_raw_output, created_at)
                   VALUES ($1::uuid, $2::uuid, $3::jsonb, $4::jsonb, timezone('utc', now()))
                   ON CONFLICT (user_id) DO UPDATE SET
                     schedule = EXCLUDED.schedule,
                     agent_raw_output = EXCLUDED.agent_raw_output,
                     created_at = EXCLUDED.created_at`,
                  [
                    crypto.randomUUID(),
                    user.user_id,
                    JSON.stringify(decision),
                    JSON.stringify({ ...fallbackOutput, fallbackReason: commanderErr.message }),
                  ]
                );
              } catch (nsErr) {
                console.warn(`⚠️ [GenerateNudges] notification_schedules save failed (non-fatal): ${nsErr.message}`);
              }
              
              logCommanderDecision(user.user_id, decision, 'fallback', preferredLanguage);
              nudgeResults.push({ userId: user.user_id, decision, mode: 'fallback' });
            }
          }
        } catch (groundingErr) {
          // Grounding collection failed - no slotTable available, use legacy fallback
          console.error(`❌ [GenerateNudges] Grounding collection failed for ${user.user_id}: ${groundingErr.message}`);
          console.warn(`⚠️ [GenerateNudges] Falling back to legacy rule-based`);
        }

        if (decision) {
          // Convert CommanderDecision → legacy schedule format for DB save
          scheduleResult = {
            schedule: decision.appNudges.map(n => ({
              problemType: n.problemType,
              scheduledTime: n.scheduledTime,
              hook: n.hook,
              content: n.content,
              tone: n.tone,
              reasoning: n.reasoning,
              rootCauseHypothesis: decision.rootCauseHypothesis || decision.overallStrategy,
              slotIndex: n.slotIndex,
              enabled: n.enabled,
            })),
            overallStrategy: decision.overallStrategy,
          };
        } else {
          // Final fallback: legacy rule-based (when grounding failed)
          scheduleResult = generateRuleBasedNudges(problems, preferredLanguage, appVersion);
          totalRuleBased++;
        }
      } else {
        // Day 1: ルールベース (v1.6.0: appVersion渡し)
        console.log(`📋 [GenerateNudges] User ${user.user_id}: Day 1 → Rule-based mode (v${appVersion})`);
        scheduleResult = generateRuleBasedNudges(problems, preferredLanguage, appVersion);
        totalRuleBased++;
      }

      // スケジュールをDBに保存
      for (const item of scheduleResult.schedule) {
        const nudgeId = crypto.randomUUID();
        const [hour, minute] = item.scheduledTime.split(':').map(Number);

        await query(
          `INSERT INTO nudge_events (id, user_id, domain, subtype, decision_point, state, action_template, channel, sent, created_at)
           VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6::jsonb, $7, $8, $9, timezone('utc', now()))`,
          [
            nudgeId,
            user.user_id,
            'problem_nudge',
            item.problemType,
            useLLM ? 'llm_generation' : 'rule_based',
            JSON.stringify({
              id: nudgeId,
              scheduledTime: item.scheduledTime,
              scheduledHour: hour,  // 後方互換
              scheduledMinute: minute,
              slotIndex: item.slotIndex ?? null,  // 1.6.0: フラット化テーブルのインデックス
              enabled: item.enabled ?? true,       // 1.6.0: Phase 7 用
              hook: item.hook.slice(0, limits.hook * 2),
              content: item.content.slice(0, limits.content * 2),
              tone: item.tone,
              reasoning: item.reasoning,
              rootCauseHypothesis: item.rootCauseHypothesis || null,
              language: preferredLanguage,
              overallStrategy: scheduleResult.overallStrategy,
              user_type: userType,  // 1.5.0: for aggregateTypeStats
            }),
            'notification',
            'push',
            false
          ]
        );

        totalGenerated++;

        if (process.env.LOG_NUDGE_CONTENT === 'true') {
          console.log(`📝 [GenerateNudges] ${item.scheduledTime} ${item.problemType}: "${item.hook}"`);
        }
      }

      console.log(`✅ [GenerateNudges] User ${user.user_id}: ${scheduleResult.schedule.length} nudges scheduled`);

    } catch (error) {
      console.error(`❌ [GenerateNudges] Failed for user ${user.user_id}:`, error.message);
      totalErrors++;
    }
  }

  console.log(`✅ [GenerateNudges] Complete: ${totalGenerated} generated, ${totalRuleBased} rule-based, ${totalErrors} errors`);

  // Phase 6: Send Slack summary
  if (nudgeResults.length > 0) {
    const slackPayload = buildSlackNudgeSummary(nudgeResults);
    const webhookUrl = process.env.SLACK_METRICS_WEBHOOK_URL;
    await sendSlackNotification(webhookUrl, slackPayload);
  }
}

// Cron モードの場合のみ自動実行（HTTP経由ではimportのみ）
if (process.env.CRON_MODE) {
  runGenerateNudges()
    .then(async () => {
      console.log('✅ [GenerateNudges] Cron job finished successfully');
      await pool.end();
      process.exit(0);
    })
    .catch(async (error) => {
      console.error('❌ [GenerateNudges] Cron job failed:', error.message);
      await pool.end();
      process.exit(1);
    });
}
