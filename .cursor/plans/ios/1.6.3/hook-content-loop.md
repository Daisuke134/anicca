# Hook-Based Content Loop Spec

Version: 1.0
Created: 2026-02-12
Status: Draft

---

## 概要

Hook DB を活用した自動コンテンツ投稿ループ。
競合で効いた Hook をリミックスし、投稿後にパフォーマンスを学習して次に活かす。

## 目的

1. 毎回ゼロから考えない → 効いた Hook をリミックス
2. 投稿して終わりにしない → 25h後に学習
3. どんどん良くなる → 効いた Hook を優先

---

## As-Is (現状)

```
trend-hunter (4h毎)
  → TikTok/Reddit/X からトレンド収集
  → hook_candidate DB に保存
  → 終わり ❌

executors:
  - runTrendScan.js ← これだけ実装済み
  - draft_content   ❌ 未実装
  - verify_content  ❌ 未実装
  - post_x          ❌ 未実装
  - post_tiktok     ❌ 未実装
  - fetch_metrics   ❌ 未実装

結果: Hook は貯まるが、投稿も学習もできない
```

## To-Be (目標)

```
┌──────────────────────────────────────────────────────────────────┐
│                   HOOK-BASED CONTENT LOOP                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [trend-hunter] ───────────────────────────────────────────────┐ │
│   cron: 0 */4 * * * (4h毎)                                     │ │
│   ・TikTok/Reddit/X から競合の効いた Hook 収集                  │ │
│   ・hook_candidate DB に保存                                    │ │
│                                                                ▼ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    hook_candidate DB                        │ │
│  │  ・text, source, competitor, tags                           │ │
│  │  ・originalViews (競合での実績)                              │ │
│  │  ・ourViews, ourLikes (自分での実績)                         │ │
│  │  ・lastUsed, useCount                                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                │ │
│  [x-poster / tiktok-poster] ◄──────────────────────────────────┘ │
│   cron: 0 9,21 * * * (9時, 21時)                                 │
│                                                                  │
│   Step 1: draft_content                                          │
│     ・Hook DB から top50 取得 (競合views順, 過去7日未使用)        │
│     ・LLM でリミックス                                           │
│     ・使用記録を更新                                             │
│                                                                  │
│   Step 2: verify_content                                         │
│     ・文字数チェック                                             │
│     ・禁止ワードチェック                                         │
│     ・重複チェック                                               │
│     ・Candle原則チェック                                         │
│                                                                  │
│   Step 3: post_x / post_tiktok                                   │
│     ・API で投稿                                                 │
│     ・postId 保存                                                │
│     ・25h後の fetch_metrics をスケジュール                       │
│                                                                  │
│  [fetch_metrics] ◄──────────────── 25h後に自動実行               │
│     ・views, likes, shares, saves 取得                          │
│     ・Hook DB の ourViews/ourLikes を更新                        │
│     ・パフォーマンス評価                                         │
│     ・次回の Hook 選択に反映                                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 実装するもの (5 executors)

### 1. draft_content

**目的:** Hook DB から最適な Hook を選び、リミックスする

**ロジック:**
```typescript
async function executeDraftContent(params: {
  platform: "x" | "tiktok";
  slot: "morning" | "evening";
}): Promise<DraftResult> {
  
  // 1. Hook DB から候補取得
  const candidates = await db.hookCandidate.findMany({
    where: {
      // 過去7日に使ってない
      lastUsed: { lt: subDays(new Date(), 7) },
      // 競合で効いた (views > 10,000)
      originalViews: { gt: 10000 },
    },
    orderBy: [
      { ourViews: "desc" },      // 自分で効いた順
      { originalViews: "desc" }, // 競合で効いた順
    ],
    take: 50,
  });

  // 2. 候補がない場合はオリジナル生成
  if (candidates.length === 0) {
    return generateOriginal(params.platform);
  }

  // 3. Top候補を選択 (重み付きランダム)
  const selected = weightedRandom(candidates);

  // 4. LLM でリミックス
  const maxLength = params.platform === "x" ? 260 : 2000;
  const remix = await llm.generate({
    model: "gpt-4o",
    prompt: `
      元のHook: "${selected.text}"
      競合: ${selected.source}
      
      Anicca（習慣化アプリ）の文脈でリミックスしてください。
      - 共感的なトーン
      - ${maxLength}文字以内
      - 最初の1行がフック（50文字以内）
    `,
  });

  // 5. 使用記録を更新
  await db.hookCandidate.update({
    where: { id: selected.id },
    data: { 
      lastUsed: new Date(),
      useCount: { increment: 1 },
    },
  });

  return {
    content: remix,
    hookCandidateId: selected.id,
    source: selected.source,
    isRemix: true,
  };
}
```

**出力:**
```json
{
  "content": "I stopped checking my phone first thing...",
  "hookCandidateId": "hook_a3f2c1",
  "source": "@larry_hamlin",
  "isRemix": true
}
```

---

### 2. verify_content

**目的:** 投稿前に品質チェック

**ロジック:**
```typescript
async function executeVerifyContent(params: {
  content: string;
  platform: "x" | "tiktok";
}): Promise<VerifyResult> {
  
  const maxLength = params.platform === "x" ? 260 : 2000;
  const firstLine = params.content.split("\n")[0];
  
  const checks = [
    {
      name: "length",
      pass: params.content.length <= maxLength,
      detail: `${params.content.length}/${maxLength}`,
    },
    {
      name: "no_banned_words",
      pass: !BANNED_WORDS.some(w => 
        params.content.toLowerCase().includes(w)
      ),
      detail: "禁止ワードチェック",
    },
    {
      name: "has_hook",
      pass: firstLine.length <= 100,
      detail: `フック長: ${firstLine.length}文字`,
    },
    {
      name: "not_duplicate",
      pass: await checkNotRecentlyPosted(params.content, 30),
      detail: "過去30日の重複チェック",
    },
  ];

  const allPass = checks.every(c => c.pass);
  
  return {
    status: allPass ? "ok" : "failed",
    checks,
    failedChecks: checks.filter(c => !c.pass),
  };
}

const BANNED_WORDS = [
  "suicide", "kill myself", "self-harm",
  "guaranteed", "100%", "miracle cure",
  // ... 
];
```

**出力 (成功):**
```json
{
  "status": "ok",
  "checks": [
    { "name": "length", "pass": true, "detail": "98/260" },
    { "name": "no_banned_words", "pass": true },
    { "name": "has_hook", "pass": true, "detail": "フック長: 48文字" },
    { "name": "not_duplicate", "pass": true }
  ],
  "failedChecks": []
}
```

**出力 (失敗):**
```json
{
  "status": "failed",
  "checks": [...],
  "failedChecks": [
    { "name": "length", "pass": false, "detail": "285/260" }
  ]
}
```

---

### 3. post_x

**目的:** X に投稿し、メトリクス収集をスケジュール

**ロジック:**
```typescript
async function executePostX(params: {
  content: string;
  hookCandidateId?: string;
}): Promise<PostResult> {
  
  // 1. X API で投稿
  const tweet = await twitterClient.v2.tweet(params.content);
  
  // 2. DB に保存
  const xPost = await db.xPost.create({
    data: {
      externalId: tweet.data.id,
      content: params.content,
      hookCandidateId: params.hookCandidateId,
      postedAt: new Date(),
    },
  });

  // 3. 25h後の fetch_metrics step をスケジュール
  const fetchAt = addHours(new Date(), 25);
  await db.opsMissionStep.create({
    data: {
      missionId: currentMission.id,
      stepKind: "fetch_metrics",
      status: "scheduled",
      scheduledAt: fetchAt,
      params: {
        platform: "x",
        postId: xPost.id,
        externalId: tweet.data.id,
      },
    },
  });

  return {
    postId: xPost.id,
    externalId: tweet.data.id,
    scheduledMetricsFetch: fetchAt,
  };
}
```

**出力:**
```json
{
  "postId": "xpost_8a7f3c",
  "externalId": "1892847362541",
  "scheduledMetricsFetch": "2026-02-13T10:00:00Z"
}
```

---

### 4. post_tiktok

**目的:** TikTok に投稿

**ロジック:** post_x と同様 (TikTok API を使用)

```typescript
async function executePostTiktok(params: {
  content: string;
  hookCandidateId?: string;
  mediaPath?: string;
}): Promise<PostResult> {
  
  // 1. TikTok API で投稿
  const post = await tiktokClient.uploadVideo({
    caption: params.content,
    videoPath: params.mediaPath,
  });
  
  // 2. DB に保存
  const tiktokPost = await db.tiktokPost.create({
    data: {
      externalId: post.id,
      content: params.content,
      hookCandidateId: params.hookCandidateId,
      postedAt: new Date(),
    },
  });

  // 3. 25h後の fetch_metrics をスケジュール
  // ... (post_x と同様)

  return {
    postId: tiktokPost.id,
    externalId: post.id,
    scheduledMetricsFetch: fetchAt,
  };
}
```

---

### 5. fetch_metrics

**目的:** 投稿後25hでメトリクス取得し、Hook DB を更新

**ロジック:**
```typescript
async function executeFetchMetrics(params: {
  platform: "x" | "tiktok";
  postId: string;
  externalId: string;
}): Promise<MetricsResult> {
  
  // 1. プラットフォーム API からメトリクス取得
  let metrics: Metrics;
  if (params.platform === "x") {
    const tweet = await twitterClient.v2.singleTweet(params.externalId, {
      "tweet.fields": ["public_metrics"],
    });
    metrics = {
      views: tweet.data.public_metrics.impression_count,
      likes: tweet.data.public_metrics.like_count,
      retweets: tweet.data.public_metrics.retweet_count,
      replies: tweet.data.public_metrics.reply_count,
    };
  } else {
    // TikTok API
    metrics = await tiktokClient.getVideoMetrics(params.externalId);
  }

  // 2. Post レコードを更新
  await db[`${params.platform}Post`].update({
    where: { id: params.postId },
    data: {
      views: metrics.views,
      likes: metrics.likes,
      metricsFetchedAt: new Date(),
    },
  });

  // 3. Hook DB を更新 (使った Hook があれば)
  const post = await db[`${params.platform}Post`].findUnique({
    where: { id: params.postId },
  });
  
  if (post.hookCandidateId) {
    await db.hookCandidate.update({
      where: { id: post.hookCandidateId },
      data: {
        ourViews: { increment: metrics.views },
        ourLikes: { increment: metrics.likes },
      },
    });
  }

  // 4. パフォーマンス評価
  const avgViews = await getAverageViews(params.platform);
  const rating = metrics.views / avgViews;
  const stars = rating >= 2 ? 3 : rating >= 1 ? 2 : 1;

  return {
    metrics,
    rating,
    stars,
    hookUpdated: !!post.hookCandidateId,
  };
}
```

**出力:**
```json
{
  "metrics": {
    "views": 4521,
    "likes": 127,
    "retweets": 23,
    "replies": 8
  },
  "rating": 2.15,
  "stars": 3,
  "hookUpdated": true
}
```

---

## Cron 設定

| Job | Cron | 頻度 | 説明 |
|-----|------|------|------|
| trend-hunter | `0 */4 * * *` | 4h毎 | Hook 収集 (既存) |
| x-poster-morning | `0 9 * * *` | 毎日9時 | X 投稿 |
| x-poster-evening | `0 21 * * *` | 毎日21時 | X 投稿 |
| tiktok-poster-morning | `0 9 * * *` | 毎日9時 | TikTok 投稿 |
| tiktok-poster-evening | `0 21 * * *` | 毎日21時 | TikTok 投稿 |
| mission-worker | `* * * * *` | 毎分 | Step 実行 (既存) |

※ fetch_metrics は cron ではなく、投稿完了時に scheduled step として生成

---

## Slack 通知フォーマット

### 投稿完了時

```
🐦 X 投稿完了

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 投稿内容:
"{content}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎣 Hook 情報:
  元ネタ: {source}
  元Hook: "{original_hook}"
  競合実績: {original_views} views

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ メトリクス収集予定: {fetch_time}
```

### メトリクス収集後

```
📊 X 投稿メトリクス (25h)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 投稿:
"{content}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 パフォーマンス:
  Views: {views}
  Likes: {likes} ({like_rate}%)
  Retweets: {retweets}
  Replies: {replies}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎣 Hook 評価: {stars} (平均の{rating}倍)
  元ネタ: {source}
  このHookの累計使用: {use_count}回
  このHookの平均views: {avg_views}

💡 学習: {learning_message}
```

### 週次サマリー (毎週月曜)

```
📊 コンテンツパフォーマンス週次レポート

期間: {start_date} - {end_date}
投稿数: X {x_count}本 / TikTok {tiktok_count}本

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏆 Top 3 X 投稿:

1. "{content_1}" 
   Views: {views_1} | Hook: {hook_1}
   
2. "{content_2}"
   Views: {views_2} | Hook: {hook_2}
   
3. "{content_3}"
   Views: {views_3} | Hook: {hook_3}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Hook パフォーマンス分析:

| Hook系統 | 使用回数 | 平均Views | 評価 |
|----------|---------|-----------|------|
| {hook_type_1} | {count_1} | {avg_1} | {rating_1} |
| {hook_type_2} | {count_2} | {avg_2} | {rating_2} |
| オリジナル | {orig_count} | {orig_avg} | {orig_rating} |

💡 学習:
{weekly_learnings}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 来週の戦略:
{next_week_strategy}
```

---

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Hook DB 空 | candidates = [] | isRemix: false, オリジナル生成 |
| 2 | Hook DB あり | candidates = 50件 | isRemix: true, top候補選択 |
| 3 | verify 成功 | content = 98文字 | status: ok |
| 4 | verify 失敗 (長すぎ) | content = 285文字 | status: failed |
| 5 | verify 失敗 (禁止ワード) | content に "suicide" | status: failed |
| 6 | post_x 成功 | - | postId, scheduledMetricsFetch |
| 7 | fetch_metrics | views: 4521 | Hook DB 更新, stars: 3 |
| 8 | 同じHook 7日以内再使用 | lastUsed: 3日前 | 候補から除外 |

---

## Hook DB スキーマ

```prisma
model HookCandidate {
  id              String   @id @default(cuid())
  
  // 元の情報
  text            String   // "I quit sugar for 30 days..."
  source          String   // "@larry_hamlin"
  platform        String   // "tiktok" | "x" | "reddit"
  originalViews   Int      // 競合での views
  tags            String[] // ["transformation", "quit", "timeline"]
  
  // 自分での実績
  ourViews        Int      @default(0)
  ourLikes        Int      @default(0)
  useCount        Int      @default(0)
  lastUsed        DateTime?
  
  // メタ
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
  
  // リレーション
  xPosts          XPost[]
  tiktokPosts     TiktokPost[]
}
```

---

## 成功指標

| Metric | 現状 | 目標 (3ヶ月) |
|--------|------|-------------|
| 平均 views (X) | ? | 3,000 |
| 平均 views (TikTok) | ? | 10,000 |
| リミックス vs オリジナル比率 | 0:100 | 70:30 |
| Hook DB サイズ | 234 | 1,000+ |
| 週次投稿数 | 0 | 28 (1日4本) |

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| Hook DB 枯渇 | trend-hunter 頻度UP、閾値下げ |
| API レート制限 | リトライ + バックオフ |
| 同じ Hook 使いすぎ | 7日クールダウン強制 |
| パフォーマンス悪化 | 自動で低評価 Hook を除外 |
| 競合から苦情 | 十分なリミックス (60%以上変更) |

---

## Changelog

- 2026-02-12: v1.0 初版作成
