# 05 — Step Executors + Data Passing

> **元ファイル**: `../closed-loop-ops.md` Section 15-16
> **ナビ**: [← API Routes](./04-api-routes-security.md) | [README](./README.md) | [次: Slack Approval →](./06-slack-approval.md)

---

## 15. Step Executor 実装（step_kind ごとの具体処理）

> **Gap P0 #1 解消**: 各 step_kind が「何をするか」を具体的に定義する
> **設計方針**: Strategy パターンで step_kind → executor 関数をマッピング。新しい step_kind の追加は Map に1行追加するだけ。

### 15.0 依存モジュール定義（B4解消: callLLM + verifyWithRegeneration）

> **これらは7/12のexecutorが依存する共通モジュール。実装者は先にこれらを作ること。**

#### lib/llm.js（LLM呼び出し共通関数）

```javascript
// apps/api/src/lib/llm.js

import OpenAI from 'openai';
import { logger } from './logger.js';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

/**
 * LLMにプロンプトを送信し、レスポンステキストを返す
 * フォールバック: OpenAI → Anthropic → エラー
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
```

#### services/verifier.js（コンテンツ検証 + 再生成ループ）

```javascript
// apps/api/src/services/verifier.js

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

  while (attempts < maxRetries + 1) {
    attempts++;
    const scoreResult = await scoreContent(content, context);
    feedbackHistory.push(scoreResult.feedback);

    if (scoreResult.score >= threshold) {
      return { content, score: scoreResult.score, passed: true, attempts, feedback: feedbackHistory };
    }

    if (attempts > maxRetries) break;

    logger.info(`${skillName}: score ${scoreResult.score}/${threshold}, regenerating (attempt ${attempts})`);
    content = await generatorFn(scoreResult.feedback);
  }

  return { content, score: 0, passed: false, attempts, feedback: feedbackHistory };
}

async function scoreContent(content, context) {
  // H16解消: SAFE-T 危機検出 — コンテンツ内の危機表現を検出
  // 「死にたい」「消えたい」等 → score=0 + crisis flag
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
    return JSON.parse(result);
  } catch {
    return { score: 0, feedback: result };
  }
}
```

**テスト（B4対応 — 実装者必須）:**

| # | テスト名 | 対象 |
|---|---------|------|
| T54 | `test_callLLM_returnsString` | callLLM 正常系 |
| T55 | `test_callLLM_throwsOnFailure` | callLLM エラー系 |
| T56 | `test_verifyWithRegeneration_passesOnFirstTry` | verifier 初回合格 |
| T57 | `test_verifyWithRegeneration_regeneratesOnFailure` | verifier 再生成 |
| T58 | `test_verifyWithRegeneration_failsAfterMaxRetries` | verifier 最大回数超過 |

### 15.1 Executor Registry

```javascript
// apps/api/src/services/ops/stepExecutors/registry.js

import { executeDraftContent } from './executeDraftContent.js';
import { executeVerifyContent } from './executeVerifyContent.js';
import { executePostX } from './executePostX.js';
import { executePostTiktok } from './executePostTiktok.js';
import { executeFetchMetrics } from './executeFetchMetrics.js';
import { executeAnalyzeEngagement } from './executeAnalyzeEngagement.js';
import { executeDiagnose } from './executeDiagnose.js';
import { executeDetectSuffering } from './executeDetectSuffering.js';
import { executeDraftNudge } from './executeDraftNudge.js';
import { executeSendNudge } from './executeSendNudge.js';
import { executeEvaluateHook } from './executeEvaluateHook.js';
import { executeRunTrendScan } from './executeRunTrendScan.js';

/**
 * step_kind → executor 関数のマッピング
 * 新しい step_kind の追加はここに1行追加するだけ
 */
const EXECUTOR_MAP = new Map([
  ['draft_content',       executeDraftContent],
  ['verify_content',      executeVerifyContent],
  ['post_x',              executePostX],
  ['post_tiktok',         executePostTiktok],
  ['fetch_metrics',       executeFetchMetrics],
  ['analyze_engagement',  executeAnalyzeEngagement],
  ['diagnose',            executeDiagnose],
  ['detect_suffering',    executeDetectSuffering],
  ['draft_nudge',         executeDraftNudge],
  ['send_nudge',          executeSendNudge],
  ['evaluate_hook',       executeEvaluateHook],
  ['run_trend_scan',      executeRunTrendScan],   // trend-hunter: 4ソース収集→hook生成→保存→イベント発行
]);

/**
 * step_kind に対応する executor を取得
 * @param {string} stepKind
 * @returns {Function} executor 関数
 * @throws {Error} 未知の step_kind
 */
export function getExecutor(stepKind) {
  const executor = EXECUTOR_MAP.get(stepKind);
  if (!executor) {
    throw new Error(`Unknown step_kind: ${stepKind}. Available: ${[...EXECUTOR_MAP.keys()].join(', ')}`);
  }
  return executor;
}
```

### 15.2 Executor Interface（共通シグネチャ）

```typescript
// 全 executor はこのシグネチャに従う（TypeScript型参考）
type StepExecutor = (context: {
  stepId: string;
  missionId: string;
  skillName: string;
  input: Record<string, unknown>;       // 前ステップの output またはミッション payload
  proposalPayload: Record<string, unknown>; // 元の提案 payload
}) => Promise<{
  output: Record<string, unknown>;  // 次ステップへの引き継ぎデータ
  events?: Array<{                  // 発行するイベント（0個以上）
    kind: string;
    tags: string[];
    payload?: Record<string, unknown>;
  }>;
}>;
```

### 15.3 各 Executor の実装

#### draft_content（コンテンツ下書き生成）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDraftContent.js

// hookSelector.js: apps/api/src/services/hookSelector.js（既存ファイル）
// Thompson Sampling でhook候補を選択する。テスト: hookSelector.test.js
import { selectHookThompson } from '../../hookSelector.js';
import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * Hook選択 → LLMでコンテンツ下書き生成
 *
 * Input: { slot?: 'morning'|'evening' } (cron payload から)
 * Output: { content: string, hookId: string, hookText: string, platform: string }
 */
export async function executeDraftContent({ input, proposalPayload, skillName }) {
  const platform = skillName === 'tiktok-poster' ? 'tiktok' : 'x';
  const slot = input?.slot || proposalPayload?.slot || 'morning';

  // 1. Hook候補をDBから取得
  // 実スキーマ: HookCandidate.text, xSampleSize, tiktokSampleSize, xEngagementRate, tiktokLikeRate
  const hooks = await prisma.hookCandidate.findMany({
    where: {
      // platform に応じたフィルタ（投稿実績があるhookを優先）
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

  // 2. Thompson Sampling でhook選択
  // スキーマ: xEngagementRate(Decimal), xSampleSize(Int), tiktokLikeRate(Decimal), tiktokSampleSize(Int)
  const selectedHook = await selectHookThompson(hooks.map(h => {
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

  // 3. LLMでコンテンツ生成
  const prompt = buildDraftPrompt(selectedHook, platform, slot);
  const content = await callLLM(prompt);

  logger.info(`Draft content generated for ${platform} (hook: ${selectedHook.id})`);

  return {
    output: {
      content,
      hookId: selectedHook.id,
      hookText: selectedHook.text,  // スキーマ: HookCandidate.text
      platform
    },
    events: [] // draft は外部影響なし。イベント不要
  };
}

function buildDraftPrompt(hook, platform, slot) {
  // P1 #12 解消: X は全角文字も 1 文字カウント（Twitter Legacy weighted length は廃止）
  // URL は短縮されて 23 文字固定。安全マージンとして日本語は 250 文字目安。
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
- 直接的な宣伝・リンクは入れない（1.6.2 フェーズでは）
- ハッシュタグは2-3個まで`;
}
```

#### verify_content（コンテンツ検証）

> **P0 #26 解消**: verifier インターフェースの定義

**検証基準（5点満点、閾値3/5）:**

| 項目 | 1点 | 基準 |
|------|-----|------|
| ペルソナ適合性 | 25-35歳・挫折経験者に刺さるか | 「簡単に！」系は0点 |
| 共感トーン | 責めずに寄り添っているか | 命令形・上から目線は0点 |
| 仏教原則 | 四諦・八正道に反しないか | 嘘・大げさ・煽りは0点 |
| プラットフォーム適合 | 文字数制限・ハッシュタグ数 | X:280字、TikTok:2200字 |
| ブランドセーフティ | 不適切表現・競合言及なし | 政治・宗教批判は0点 |

**verifyWithRegeneration インターフェース:**

```typescript
interface VerifyOptions {
  threshold: number;      // 合格点（デフォルト3）
  maxRetries: number;     // 最大再生成回数（デフォルト3）
  skillName: string;      // ログ用
  context: Record<string, unknown>;
}

interface VerifyResult {
  content: string;        // 最終コンテンツ（再生成された可能性あり）
  score: number;          // 最終スコア（0-5）
  passed: boolean;        // score >= threshold
  attempts: number;       // 試行回数（1-4）
  feedback: string[];     // 各試行のフィードバック
}

// generatorFn: フィードバックを受けてコンテンツを再生成する関数
// 初回は feedback=null、2回目以降はスコアが低かった理由を含む
type GeneratorFn = (feedback: string | null) => Promise<string>;

async function verifyWithRegeneration(
  generatorFn: GeneratorFn,
  options: VerifyOptions
): Promise<VerifyResult>;
```

**フロー:**
```
generatorFn(null) → content
    ↓
LLM scorer (5項目各1点) → score=2 (不合格)
    ↓ feedback: "共感トーンが不足。命令形を避けて"
generatorFn(feedback) → improved content
    ↓
LLM scorer → score=4 (合格)
    ↓
return { content: improved, score: 4, passed: true, attempts: 2 }
```

```javascript
// apps/api/src/services/ops/stepExecutors/executeVerifyContent.js

import { verifyWithRegeneration } from '../../verifier.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 生成コンテンツを仏教原則で検証
 *
 * Input: { content: string, hookId: string, platform: string } (draft_content の output)
 * Output: { content: string, verificationScore: number, passed: boolean, attempts: number }
 */
export async function executeVerifyContent({ input }) {
  const { content, platform } = input;

  if (!content) {
    throw new Error('verify_content requires input.content from previous step');
  }

  // verifier.js の verifyWithRegeneration を使用
  // 不合格の場合は自動再生成（最大3回）
  const result = await verifyWithRegeneration(
    async (feedback) => {
      if (!feedback) return content; // 初回はそのまま
      // 再生成: フィードバックを反映
      return callLLM(`以下のコンテンツを修正してください。
元のコンテンツ: "${content}"
フィードバック: ${feedback}
プラットフォーム: ${platform}`);
    },
    {
      threshold: 3, // 5点中3点以上で合格
      maxRetries: 3,
      skillName: 'verify_content',
      context: { platform }
    }
  );

  logger.info(`Content verification: ${result.passed ? 'PASSED' : 'FAILED'} (score: ${result.score}, attempts: ${result.attempts})`);

  if (!result.passed) {
    throw new Error(`Content verification failed after ${result.attempts} attempts (score: ${result.score}/5)`);
  }

  // H13修正: spread を先に、具体フィールドを後に置くことで上書きバグを防止
  // 修正前: { content: result.content, ...input } → input.content が result.content を上書きしてしまう
  // 修正後: { ...input, content: result.content } → result.content が input.content を上書き（正しい）
  return {
    output: {
      ...input,                            // 前ステップのデータを引き継ぎ（hookId, platform 等）
      content: result.content,             // 検証済みコンテンツで上書き（再生成された可能性あり）
      verificationScore: result.score,
      passed: result.passed,
      attempts: result.attempts
    },
    events: []
  };
}
```

#### post_x（X投稿実行）

```javascript
// apps/api/src/services/ops/stepExecutors/executePostX.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * X (Twitter) API で投稿
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string, platform: string }
 * Events: tweet_posted
 *
 * 注意: VPS Worker から呼ばれる。実際のX API呼び出しはVPS側のexecツールで実行。
 * Railway API側ではDB記録とイベント発行のみ。
 *
 * 実スキーマ XPost: text, hookCandidateId, slot, postedAt, xPostId, agentReasoning,
 *   impressionCount(BigInt), likeCount(BigInt), retweetCount(BigInt), replyCount(BigInt), engagementRate(Decimal)
 *   ※ verificationScore, status フィールドは存在しない
 */
export async function executePostX({ input, missionId }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_x requires input.content');
  }

  const xPost = await prisma.xPost.create({
    data: {
      text: content,                     // スキーマ: text (String @db.Text)
      hookCandidateId: hookId || null,
      slot: input.slot || null,          // スキーマ: slot (String? @db.VarChar(20))
      postedAt: new Date(),              // スキーマ: postedAt (DateTime?)
      agentReasoning: JSON.stringify({ verificationScore, missionId })
      // xPostId は VPS 側で X API 投稿後に PATCH で更新
    }
  });

  logger.info(`X post recorded: ${xPost.id}`);

  return {
    output: {
      postId: xPost.id,
      dbRecordId: xPost.id,
      platform: 'x'
    },
    events: [{
      kind: 'tweet_posted',
      tags: ['tweet', 'posted'],
      payload: {
        postId: xPost.id,
        hookId,
        verificationScore,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}
```

#### post_tiktok（TikTok投稿実行）

```javascript
// apps/api/src/services/ops/stepExecutors/executePostTiktok.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * TikTok投稿
 *
 * Input: { content: string, hookId: string, verificationScore: number }
 * Output: { postId: string }
 * Events: tiktok_posted
 */
export async function executePostTiktok({ input, missionId }) {
  const { content, hookId, verificationScore } = input;

  if (!content) {
    throw new Error('post_tiktok requires input.content');
  }

  // 実スキーマ TiktokPost: caption, hookCandidateId, slot, postedAt, tiktokVideoId, agentReasoning,
  //   viewCount(BigInt), likeCount(BigInt), commentCount(BigInt), shareCount(BigInt)
  //   ※ verificationScore, status フィールドは存在しない
  const tiktokPost = await prisma.tiktokPost.create({
    data: {
      caption: content,
      hookCandidateId: hookId || null,
      slot: input.slot || null,           // スキーマ: slot (String? @db.VarChar(20))
      postedAt: new Date(),               // スキーマ: postedAt (DateTime)
      agentReasoning: JSON.stringify({ verificationScore, missionId })
    }
  });

  logger.info(`TikTok post recorded: ${tiktokPost.id}`);

  return {
    output: {
      postId: tiktokPost.id,
      platform: 'tiktok'
    },
    events: [{
      kind: 'tiktok_posted',
      tags: ['tiktok', 'posted'],
      payload: {
        postId: tiktokPost.id,
        hookId,
        contentPreview: content.substring(0, 50)
      }
    }]
  };
}
```

#### fetch_metrics（エンゲージメントデータ取得）

```javascript
// apps/api/src/services/ops/stepExecutors/executeFetchMetrics.js

import { prisma } from '../../../lib/prisma.js';
import { logger } from '../../../lib/logger.js';

/**
 * 投稿のエンゲージメントデータ取得
 * VPS側で X API / TikTok API を呼び出し、結果を返す
 *
 * Input: { triggeredBy: string, eventId: string } (trigger payload から)
 * Output: { metrics: { impressions, engagements, engagementRate }, postId: string }
 */
export async function executeFetchMetrics({ input, proposalPayload }) {
  // トリガーイベントから元の投稿を特定
  const event = await prisma.opsEvent.findUnique({
    where: { id: input.eventId || proposalPayload.eventId }
  });

  if (!event) {
    throw new Error(`Event not found: ${input.eventId}`);
  }

  const postId = event.payload?.postId;
  const platform = event.kind.includes('tweet') ? 'x' : 'tiktok';

  // メトリクスは VPS Worker が X/TikTok API から取得してこのoutputに格納する
  // ここではDBに記録されているメトリクスを返す（VPS Worker が事前にDB更新している想定）

  // 実スキーマ注意: impressionCount, likeCount, retweetCount, replyCount は BigInt
  // Number() で変換が必要（BigInt は JSON.stringify や算術演算で直接使えない）
  let metrics;
  if (platform === 'x') {
    const post = await prisma.xPost.findUnique({ where: { id: postId } });
    const impressions = Number(post?.impressionCount || 0n);
    const likes = Number(post?.likeCount || 0n);
    const retweets = Number(post?.retweetCount || 0n);
    const replies = Number(post?.replyCount || 0n);
    const engagements = likes + retweets + replies;
    metrics = {
      impressions,
      engagements,
      likes, retweets, replies,
      engagementRate: impressions > 0
        ? (engagements / impressions * 100).toFixed(2)
        : Number(post?.engagementRate || 0).toFixed(2)  // スキーマに engagementRate(Decimal) もある
    };
  } else {
    const post = await prisma.tiktokPost.findUnique({ where: { id: postId } });
    const views = Number(post?.viewCount || 0n);
    const likes = Number(post?.likeCount || 0n);
    const comments = Number(post?.commentCount || 0n);
    const shares = Number(post?.shareCount || 0n);
    metrics = {
      views,
      likes, comments, shares,
      engagementRate: views > 0
        ? (likes / views * 100).toFixed(2)
        : '0'
    };
  }

  logger.info(`Metrics fetched for ${platform} post ${postId}: ${JSON.stringify(metrics)}`);

  return {
    output: { metrics, postId, platform },
    events: [{
      kind: `${platform}_metrics_fetched`,
      tags: [platform, 'metrics', 'fetched'],
      payload: { postId, ...metrics }
    }]
  };
}
```

#### analyze_engagement（エンゲージメント分析）

```javascript
// apps/api/src/services/ops/stepExecutors/executeAnalyzeEngagement.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * メトリクスを分析 → shared-learnings に記録 → hook_candidates 更新
 *
 * Input: { metrics: Object, postId: string, platform: string }
 * Output: { analysis: string, isHighEngagement: boolean, learnings: string[] }
 * Events: engagement:high (閾値超) or engagement:low
 */
export async function executeAnalyzeEngagement({ input, missionId }) {
  const { metrics, postId, platform } = input;

  if (!metrics) {
    throw new Error('analyze_engagement requires input.metrics from fetch_metrics step');
  }

  const engagementRate = parseFloat(metrics.engagementRate || '0');
  const isHighEngagement = engagementRate > 5.0; // 5%以上を「高エンゲージメント」

  // LLMで分析
  const analysis = await callLLM(`以下の投稿メトリクスを分析し、学びを3つ箇条書きで:
Platform: ${platform}
Metrics: ${JSON.stringify(metrics)}
Engagement Rate: ${engagementRate}%
判定: ${isHighEngagement ? '高エンゲージメント' : '低エンゲージメント'}`);

  // hook_candidates のスコア更新（Thompson Sampling フィードバック）
  if (postId) {
    const post = platform === 'x'
      ? await prisma.xPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } })
      : await prisma.tiktokPost.findUnique({ where: { id: postId }, select: { hookCandidateId: true } });

    if (post?.hookCandidateId) {
      // 実スキーマ HookCandidate: xSampleSize(Int), xEngagementRate(Decimal),
      //   tiktokSampleSize(Int), tiktokLikeRate(Decimal)
      // ※ xEngagements, tiktokEngagements フィールドは存在しない
      // サンプルサイズを+1し、エンゲージメント率を再計算
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
```

#### detect_suffering（苦しみ検出）

> **H16解消: SAFE-T 危機検出プロトコル**
> severity >= 0.9 の検出は `crisis:detected` イベントを発行し、通常フロー（Nudge等）を中断。
> `step/complete` ハンドラ（§16.3）で detections を走査し、crisis 判定を行う。

```javascript
// apps/api/src/services/ops/stepExecutors/executeDetectSuffering.js

import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * Web検索で苦しみに関するトレンド・投稿を検出
 * VPS Worker の web_search ツールで実行
 *
 * Input: {} (パラメータなし)
 * Output: { detections: Array<{text, severity, problemType, source}> }
 * Events: suffering_detected (severity >= 0.6), crisis:detected (severity >= 0.9)
 *
 * SAFE-T Protocol:
 * - severity >= 0.9 → crisis:detected イベント発行 → 通常フロー中断 + Slack #ops-approval に即時通知
 * - crisis 判定は step/complete ハンドラ (§16.3) で自動実行される
 */
export async function executeDetectSuffering({ skillName }) {
  // この関数は VPS Worker から呼ばれ、web_search ツールを使う
  // Railway API 側ではスケルトンのみ定義。実際の検出ロジックは SKILL.md に記述

  // VPS Worker が検出結果を output に格納して step/complete に報告する想定
  // ここでは「VPS が返した output をそのまま通す」パススルー構造

  logger.info('detect_suffering: VPS Worker が web_search で検出を実行');

  return {
    output: {
      note: 'VPS Worker executes web_search and returns detections in step/complete output'
    },
    events: []
    // 注: 実際のイベント発行は VPS Worker が step/complete を呼ぶ際に、
    // Railway API の completeStep ハンドラが output.detections を見てイベントを発行する
    // SAFE-T: severity >= 0.9 は crisis:detected として特別処理される（§16.3参照）
  };
}
```

#### diagnose（ミッション失敗診断）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDiagnose.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * 失敗したミッションの原因を分析し、学びを記録
 *
 * Input: { eventId: string } (mission:failed イベントから)
 * Output: { diagnosis: string, rootCause: string, recommendation: string }
 */
export async function executeDiagnose({ input, proposalPayload }) {
  const eventId = input.eventId || proposalPayload.eventId;
  const event = await prisma.opsEvent.findUnique({ where: { id: eventId } });

  if (!event) {
    throw new Error(`Event not found: ${eventId}`);
  }

  // 失敗したミッションの詳細を取得
  const missionId = event.payload?.missionId;
  const mission = missionId ? await prisma.opsMission.findUnique({
    where: { id: missionId },
    include: {
      steps: { orderBy: { stepOrder: 'asc' } },
      proposal: true
    }
  }) : null;

  const failedSteps = mission?.steps?.filter(s => s.status === 'failed') || [];

  // LLMで診断
  const diagnosis = await callLLM(`以下のミッション失敗を診断:
Mission: ${mission?.proposal?.title || 'unknown'}
Skill: ${event.source}
Failed Steps: ${JSON.stringify(failedSteps.map(s => ({
    kind: s.stepKind,
    error: s.lastError
  })))}

根本原因を特定し、再発防止策を提案:`);

  logger.info(`Diagnosis complete for mission ${missionId}`);

  return {
    output: {
      diagnosis,
      failedMissionId: missionId,
      failedStepKinds: failedSteps.map(s => s.stepKind)
    },
    events: [{
      kind: 'diagnosis:completed',
      tags: ['diagnosis', 'completed'],
      payload: { missionId, diagnosisPreview: diagnosis.substring(0, 200) }
    }]
  };
}
```

#### draft_nudge（Nudge下書き生成）

```javascript
// apps/api/src/services/ops/stepExecutors/executeDraftNudge.js

import { callLLM } from '../../../lib/llm.js';

/**
 * 苦しみ検出結果に基づいてNudge下書きを生成
 *
 * Input: { detections: Array<{text, severity, problemType}> } (detect_suffering の output)
 * Output: { nudgeContent: string, targetProblemType: string, severity: number }
 */
export async function executeDraftNudge({ input }) {
  const detections = input.detections || [];
  const topDetection = detections.sort((a, b) => (b.severity || 0) - (a.severity || 0))[0];

  if (!topDetection) {
    return { output: { nudgeContent: null, skipped: true }, events: [] };
  }

  const nudgeContent = await callLLM(`以下の苦しみに対する Nudge メッセージ（通知文）を生成:
苦しみ: "${topDetection.text}"
種別: ${topDetection.problemType}
重要度: ${topDetection.severity}

ルール:
- 責めない、共感するトーン
- 小さすぎるステップを提案
- 50文字以内`);

  return {
    output: {
      nudgeContent,
      targetProblemType: topDetection.problemType,
      severity: topDetection.severity
    },
    events: []
  };
}
```

#### send_nudge（Nudge送信）

```javascript
// apps/api/src/services/ops/stepExecutors/executeSendNudge.js

import { logger } from '../../../lib/logger.js';

/**
 * Nudge送信（Push通知）
 *
 * Input: { nudgeContent: string, targetProblemType: string }
 * Output: { sent: boolean }
 * Events: nudge_sent
 *
 * 注: 実際の送信は VPS Worker が Railway API の /api/mobile/nudge/ を呼ぶ
 */
export async function executeSendNudge({ input }) {
  const { nudgeContent, targetProblemType } = input;

  if (!nudgeContent || input.skipped) {
    logger.info('send_nudge skipped: no content');
    return { output: { sent: false, skipped: true }, events: [] };
  }

  // VPS Worker が実際に送信を実行
  logger.info(`Nudge ready to send: ${targetProblemType} — "${nudgeContent}"`);

  return {
    output: {
      sent: true,
      nudgeContent,
      targetProblemType
    },
    events: [{
      kind: 'nudge_sent',
      tags: ['nudge', 'sent'],
      payload: { targetProblemType, contentPreview: nudgeContent.substring(0, 30) }
    }]
  };
}
```

#### evaluate_hook（Hook評価）

```javascript
// apps/api/src/services/ops/stepExecutors/executeEvaluateHook.js

import { prisma } from '../../../lib/prisma.js';
import { callLLM } from '../../../lib/llm.js';
import { logger } from '../../../lib/logger.js';

/**
 * trend-hunter が見つけた hook_candidate を x-poster が評価
 *
 * Input: { eventId: string } (hook_saved イベントの eventId。Reaction Matrix が payload.hookId → eventId を注入)
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

  // 実スキーマ: HookCandidate.text, targetProblemTypes, xEngagementRate
  // ※ hookText, problemTypes, relevanceScore フィールドは存在しない
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
      payload: { hookId: hook.id, hookText: hook.text }  // スキーマ: HookCandidate.text
    }] : []
  };
}
```

#### run_trend_scan（トレンドスキャン — trend-hunter フルパイプライン）

```javascript
// apps/api/src/services/ops/stepExecutors/executeRunTrendScan.js

import { logger } from '../../../lib/logger.js';

/**
 * trend-hunter のフルパイプラインを単一ステップとして実行
 * VPS SKILL.md が内部で4ソース収集→LLMフィルタ→hook生成→Railway保存→イベント発行を全て行う
 *
 * Input: {} (空 — Cron payload から)
 * Output: { savedCount: number, sources: string[], errors: string[] }
 * Events: hook ごとに hook_saved イベント + scan_completed サマリー
 *
 * 注意: このexecutorのロジックはRailway API側ではなく、VPS SKILL.md側で実行される。
 * Railway API側は入出力スキーマの定義のみ。
 */
export async function executeRunTrendScan({ input, proposalPayload }) {
  // VPS Worker が SKILL.md の trend-hunter を実行し、結果を step/complete で報告する。
  // ここにはインターフェース定義のみ。
  // VPS SKILL.md 側の実装: trend-hunter/03-processing-flow.md 参照
  logger.info('run_trend_scan: Interface definition only — execution is on VPS SKILL.md');

  // VPS Worker からの完了報告の expected output shape:
  // ★ イベント発行経路: step executor コンテキストでは body.events が唯一の正規経路
  //   （step executor 内から直接 POST /api/ops/events は禁止 — 二重発火防止）
  //   VPS SKILL.md がイベントを配列に収集し、VPS Worker が step/complete で一括送信する
  //   ※ standalone cron（step コンテキストなし）では直接 POST /api/ops/events が許可される
  //   → 04-config-integration.md「イベント発行経路」参照
  return {
    output: {
      savedCount: 0,         // 保存した hook 数
      sources: [],            // 成功したソース名 ['twitter', 'tiktok', 'reddit', 'github']
      errors: [],             // 失敗したソースのエラーメッセージ
      empathyCount: 0,        // 共感系 hook 数
      solutionCount: 0        // 問題解決系 hook 数
    },
    events: [
      // hook ごとに個別 hook_saved イベント（04-config-integration.md 正規仕様準拠）
      // { kind: 'hook_saved', tags: ['hook_candidate', 'found'], payload: { hookId, hookType, targetTypes } }
      // ... (savedHooks.length 個)
      // + scan_completed サマリー（監視用）
      // { kind: 'scan_completed', tags: ['scan', 'completed'], payload: { savedCount, empathyCount, solutionCount } }
    ]
  };
}
```

### 15.4 VPS Worker が Executor を呼ぶフロー

```
VPS Worker (1分毎ポーリング)
    |
    v
GET /api/ops/step/next
    |
    v (step が返ってきた)
    |
    v
step.stepKind を確認
    |
    +----> 'draft_content'    → hookSelector + LLM（VPS上で直接実行）
    +----> 'verify_content'   → verifier.js（VPS上で直接実行）
    +----> 'post_x'           → X API 呼び出し（VPS上で exec ツール）
    +----> 'detect_suffering'  → web_search（VPS上で web_search ツール）
    +----> 'run_trend_scan'   → trend-hunter SKILL.md（4ソース収集→hook生成→保存→イベント発行）
    +----> ...
    |
    v
PATCH /api/ops/step/:id/complete { status, output, events }
    |                                              ↑ events は output の外側
    v
Railway API が output を DB に保存 → 次のステップの input になる
Railway API が events をイベントとして発行 → Trigger 評価へ
```

> **重要**: Railway API 側の executor はロジックの「定義」。VPS Worker は SKILL.md に従って
> 実際のAPI呼び出しやLLM呼び出しを実行し、その結果を step/complete で報告する。
> Railway API 側の executor は「どんなデータが流れるか」を規定するインターフェース。

---

## 16. Step-to-Step データパッシング

> **Gap P0 #6 解消**: Step 0 の output が Step 1 の input になる仕組み
> **設計方針**: Temporal Workflow の子ワークフロー引数渡しパターンを参考に、
> シンプルに「前ステップの output を次ステップの input にマージ」する

### 16.1 データフロー図（x-poster パイプライン例）

```
Step 0: draft_content
  input:  { slot: "morning" }  ← proposalPayload から
  output: { content: "挫折は恥じゃない...", hookId: "abc", platform: "x" }
                  ↓
Step 1: verify_content
  input:  { content: "挫折は恥じゃない...", hookId: "abc", platform: "x" }  ← Step 0 の output
  output: { content: "挫折は恥じゃない...", verificationScore: 4, passed: true, hookId: "abc", platform: "x" }
                  ↓
Step 2: post_x
  input:  { content: "挫折は恥じゃない...", verificationScore: 4, hookId: "abc", platform: "x" }  ← Step 1 の output
  output: { postId: "xyz", platform: "x" }
  events: [{ kind: "tweet_posted", tags: ["tweet", "posted"], payload: { postId: "xyz", hookId: "abc" } }]
```

### 16.2 GET /api/ops/step/next の修正（前ステップ output 注入）

```javascript
// 既存の GET /api/ops/step/next を修正
// 変更箇所: ★ マーク

router.get('/step/next', async (req, res) => {
  // P0 #23 解消: 並行 Worker の競合防止
  // Prisma $transaction はデフォルト READ COMMITTED → 同時読み取りで同一ステップを claim する可能性あり
  // 解決: $queryRaw で SELECT ... FOR UPDATE SKIP LOCKED を使用
  // SKIP LOCKED: 他トランザクションがロック中の行をスキップ（PostgreSQL 9.5+）
  // これにより Worker A がロック中の行を Worker B はスキップして次の行を取得する
  const step = await prisma.$transaction(async (tx) => {
    // SELECT FOR UPDATE SKIP LOCKED で排他的に claim
    const [next] = await tx.$queryRaw`
      SELECT id, mission_id, step_kind, step_order, input, created_at
      FROM ops_mission_steps
      WHERE status = 'queued'
      ORDER BY created_at ASC, step_order ASC
      LIMIT 1
      FOR UPDATE SKIP LOCKED
    `;

    if (!next) return null;

    // 同一ミッション内で前のステップが完了しているか確認
    let previousOutput = {};
    if (next.step_order > 0) {
      const prevStep = await tx.opsMissionStep.findFirst({
        where: {
          missionId: next.mission_id,
          stepOrder: next.step_order - 1
        }
      });
      if (prevStep && prevStep.status !== 'succeeded') {
        return null; // 前のステップがまだ完了していない
      }
      previousOutput = prevStep?.output || {};
    }

    // running に更新（claim）
    const updated = await tx.opsMissionStep.update({
      where: { id: next.id },
      data: {
        status: 'running',
        reservedAt: new Date(),
        input: {
          ...(next.input || {}),
          ...previousOutput
        }
      },
      include: {
        mission: {
          include: { proposal: true }
        }
      }
    });

    return { ...updated, mergedInput: { ...(next.input || {}), ...previousOutput } };
  });

  if (!step) {
    return res.json({ step: null });
  }

  res.json({
    step: {
      id: step.id,
      missionId: step.missionId,
      stepKind: step.stepKind,
      stepOrder: step.stepOrder,
      input: step.mergedInput,  // ★ 変更: マージ済み input を返す
      proposalPayload: step.mission.proposal.payload,
      skillName: step.mission.proposal.skillName
    }
  });
});
```

### 16.3 PATCH /api/ops/step/:id/complete の修正（イベント自動発行）

```javascript
// 既存の PATCH /api/ops/step/:id/complete を修正
// 変更箇所: ★ マーク

router.patch('/step/:id/complete', async (req, res) => {
  const { id } = req.params;
  const parsed = StepCompleteSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ error: parsed.error.flatten() });
  }

  const { status, output, error, events: bodyEvents } = parsed.data;

  const step = await prisma.opsMissionStep.update({
    where: { id },
    data: {
      status,
      output: output || {},
      lastError: error || null,
      completedAt: new Date()
    },
    include: {  // ★ 追加: mission + proposal を include
      mission: { include: { proposal: true } }
    }
  });

  // ★ 追加: body.events があればイベントを発行
  // 注意: Executor は { output, events } を返す。VPS Worker は step/complete に
  // { status, output, events } として送信する。events は output の外側。
  const { emitEvent } = await import('../../services/ops/eventEmitter.js');
  if (bodyEvents && Array.isArray(bodyEvents)) {
    for (const evt of bodyEvents) {
      await emitEvent(
        step.mission.proposal.skillName,
        evt.kind,
        evt.tags || [],
        evt.payload || {},
        step.missionId
      );
    }
  }

  // ★ 追加: detect_suffering の detections からイベント発行
  // H16解消: SAFE-T 危機検出プロトコル
  // severity >= 0.9 → crisis:detected（通常フロー中断 + 即時通知）
  // severity >= 0.6 → suffering_detected（通常のNudgeトリガー）
  if (step.stepKind === 'detect_suffering' && output?.detections) {
    for (const detection of output.detections) {
      if (detection.severity >= 0.9) {
        // SAFE-T: 危機レベル — 通常フロー中断、即時通知
        await emitEvent(
          step.mission.proposal.skillName,
          'crisis:detected',
          ['crisis', 'detected', 'safe_t'],
          { ...detection, protocol: 'SAFE-T', action: 'halt_normal_flow_and_alert' },
          step.missionId
        );
        logger.warn(`SAFE-T CRISIS: severity=${detection.severity} — "${detection.text?.substring(0, 50)}"`);
      } else if (detection.severity >= 0.6) {
        await emitEvent(
          step.mission.proposal.skillName,
          'suffering_detected',
          ['suffering', 'detected'],
          detection,
          step.missionId
        );
      }
    }
  }

  // ミッション最終化判定
  const missionStatus = await maybeFinalizeMission(step.missionId);

  res.json({ ok: true, stepStatus: status, missionStatus });
});
```
