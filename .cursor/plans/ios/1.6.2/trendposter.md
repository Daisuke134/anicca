# trend-hunter 改訂設計書

> **目的**: 13 ProblemType に関連するバイラルコンテンツをマルチソースから検出し、Aniccaの投稿hookに変換する
> **最終更新**: 2026-02-08
> **ステータス**: ドラフト（レビュー中）
> **参照**: `1.6.2-ultimate-spec.md` の Phase 3 (3.2 trend-hunter)

---

## ⚠️ ユーザー事前作業（実装開始前に必ず完了すること）

> **この設計書のユーザー事前作業が全て完了するまで、実装を開始してはならない。**
> エージェントは実装開始前にこのチェックリストを確認し、未完了の項目があればユーザーに依頼すること。

### 実装前に必要なGUI作業

| # | サービス | 作業内容 | 所要時間 | 手順 | 取得するもの | 完了 |
|---|---------|---------|---------|------|------------|------|
| 1 | **TwitterAPI.io** | アカウント登録 + APIキー取得 | 2分 | ① https://twitterapi.io/ にアクセス → ② 「Sign in with Google」クリック → ③ ダッシュボードでAPIキーをコピー | `TWITTERAPI_KEY` | ⬜ |
| 2 | **reddapi.dev** | アカウント登録 + Liteプラン契約 + APIキー生成 | 5分 | ① https://reddapi.dev/auth にアクセス → ② Google/GitHubでログイン → ③ Liteプラン($9.90/月)購入 → ④ /account でAPIキー生成 | `REDDAPI_API_KEY` | ⬜ |
| 3 | **VPS環境変数追加** | 取得したキーをVPSの.envに追加 | 1分 | `ssh anicca@46.225.70.241` → `.env` に2つのキーを追記 → Gateway再起動 | - | ⬜ |

### GUI作業が不要なもの（確認済み）

| サービス | 理由 |
|---------|------|
| **Apify**（TikTokトレンド取得） | `APIFY_API_TOKEN` が GitHub Secrets に登録済み。`clockworks~tiktok-scraper` を既に運用中 |
| **TikTok Creative Center** | Apify経由で取得するため直接アクセス不要 |
| **Railway API** | `ANICCA_AGENT_TOKEN` が VPS .env に設定済み |
| **Brave Search** | `BRAVE_API_KEY` が VPS .env に設定済み |

### 確認事項（エージェント向け）

| # | 確認項目 | 方法 |
|---|---------|------|
| 1 | `APIFY_API_TOKEN` がVPSの `.env` にもあるか | `ssh anicca@46.225.70.241` → `grep APIFY ~/.env` |
| 2 | TwitterAPI.io の無料クレジット($0.10 = 666件)でテスト実行可能か | APIキー取得後に `curl` でテスト |
| 3 | reddapi.dev Liteプラン(500 calls/月)で十分か | 月間推定: 6回/日 × 3クエリ × 30日 = 540回 → **ギリギリ。要モニタリング** |

### VPS .env に追記するキー

```bash
# 以下を /home/anicca/.env に追記
TWITTERAPI_KEY=<ダッシュボードからコピーした値>
REDDAPI_API_KEY=<アカウントページで生成した値>

# 追記後にGateway再起動
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart openclaw-gateway
```

---

## 0. 改訂の背景

### 現Specの問題

| 問題 | 詳細 |
|------|------|
| **苦しみキーワードに囚われすぎ** | `buddhism OR meditation OR anxiety` で検索 → ニッチすぎてバイラルに繋がらない |
| **トレンドを見てない** | 「今何がバズってるか」を検出してない。キーワード固定検索だけ |
| **データソースが曖昧** | X API + TikTok API と書いてあるが、具体的にどのエンドポイントか不明 |
| **hook候補の生成ロジックが弱い** | 「LLMで抽出」としか書いてない。トレンド→Aniccaアングルの変換が設計されてない |

### 改訂コンセプト

```
現在:  苦しみキーワード固定検索 → hook候補抽出
       ↑ ニッチすぎ、バイラルしない

改訂:  ProblemType別バイラル検出 → Aniccaアングル変換 → hook候補生成
       ↑ 既にバズっているものの中から、13個の苦しみに関連するものを見つける
```

### 2種類のバイラルコンテンツ

| タイプ | 内容 | Aniccaでの活用 |
|--------|------|---------------|
| **共感系** | 当事者が苦しみを語り、「わかる」「俺もそう」とバズっている | そのまま共感hookとして使える。「あなただけじゃない」系 |
| **問題解決系** | 専門家や一般人が「○○を手放す方法5選」等でバズっている | Aniccaの機能紹介hookに変換できる。「アプリでこれができる」系 |

---

## 1. SKILL.md（改訂案）

```yaml
---
name: trend-hunter
description: 13 ProblemType のバイラルコンテンツをマルチソースから検出し、hook候補を生成するスキル
metadata: { "openclaw": { "emoji": "🔍", "requires": { "env": ["TWITTERAPI_KEY", "REDDAPI_API_KEY", "APIFY_API_TOKEN", "ANICCA_AGENT_TOKEN"] } } }
---

# trend-hunter

## 概要

Aniccaの13 ProblemType に関連するコンテンツで、既にバイラルになっているものを
複数プラットフォームから検出する。

検出対象は2種類:
1. **共感系**: 当事者が苦しみを語り、大量の共感を得ている投稿
2. **問題解決系**: その苦しみへの対処法を発信し、バズっている投稿

見つかったバイラルコンテンツから、Aniccaの投稿hook候補を生成してDBに保存する。

## データソース（優先順）

| # | ソース | 取得方法 | コスト | 何を取るか |
|---|--------|---------|--------|-----------|
| 1 | X/Twitter | **TwitterAPI.io**（サードパーティAPI） | **$0.15/1,000件**（月~$9） | バズツイート + いいね数/RT数 |
| 2 | TikTok | **Apify** `clockworks/tiktok-trends-scraper`（既存Apifyアカウント利用） | **既存Apify枠内**（$5/月で~800件） | トレンドハッシュタグ + 投稿数 + 再生数 + 成長率 |
| 3 | Reddit | **reddapi.dev** Liteプラン セマンティック検索 | **$9.90/月**（500 API calls） | 急成長トピック + ユーザーの生の声 |
| 4 | GitHub Trending | HTTPスクレイピング（trend-watcher方式） | 無料 | テック系トレンド（補助） |

### X データ取得方法の選定根拠（2026-02-08 調査済み）

| 手段 | 検索 | メトリクス | コスト | 判定 |
|------|------|----------|--------|------|
| X API Free | 不可（write-only） | 不可 | $0 | 使えない |
| X API Basic | 7日間 | 可 | **$200/月** | 高すぎる（まだ結果出てない段階） |
| Firecrawl + x.com | **明示的にブロック** | 不可 | - | 使えない |
| Brave `site:x.com` | 極少・不安定 | 不可 | $0 | 信頼性低い |
| **TwitterAPI.io** | **無制限** | **可（いいね/RT）** | **$0.15/1k件** | **採用** |

**X API v2 Free は検索不可（write-only）。Basic は $200/月で初期段階には高すぎる。**
**TwitterAPI.io を採用**: $0.15/1,000ツイートの従量課金。月間推定3,000件取得で月$0.45。
メトリクス（いいね数/RT数/リプライ数）も取得可能。X開発者アカウント不要。

**リスク**: TwitterAPI.ioはサードパーティサービスでX ToS違反の可能性あり。
サービス停止時のフォールバック: TikTok + Reddit の結果のみで続行。

### TikTok データ取得方法の選定根拠

| 手段 | 結果 |
|------|------|
| Firecrawl + Creative Center | トップ3ハッシュタグのみ。「View More」以降はログイン必須 |
| browser (Playwright) + Creative Center | フルリスト取得可能だがログイン必須（TikTok Business アカウント） |
| **Apify `clockworks/tiktok-trends-scraper`** | **Creative Centerのフルデータを自動取得。ログイン不要。JSON出力** |

**Apify を採用**: コードベースで既に `clockworks~tiktok-scraper` を運用中（`APIFY_API_TOKEN` 登録済み）。
同じ `clockworks` 開発者の `tiktok-trends-scraper` を追加利用するだけ。GUI作業なし。

取得できるデータ:
```json
{
  "name": "#dopaminedetox",
  "rank": 5,
  "industryName": "Education",
  "videoCount": 1572,
  "viewCount": 5659920,
  "rankDiff": +3,
  "markedAsNew": true,
  "isPromoted": false,
  "countryCode": "JP"
}
```

## 13 ProblemType とクエリマッピング

### ProblemType別 検索クエリ辞書

各ProblemTypeに対して、共感系・問題解決系の2パターンのクエリを定義する。

| ProblemType | 共感系クエリ（当事者の叫び） | 問題解決系クエリ（対処法バズ） |
|-------------|---------------------------|---------------------------|
| **staying_up_late** | "また3時だ" "夜更かし やめられない" "can't stop scrolling at night" "it's 3am again" | "夜更かし 直す方法" "how to fix sleep schedule" "screen time before bed" |
| **cant_wake_up** | "朝起きれない つらい" "スヌーズ 10回" "can't wake up hate myself" "morning person is a myth" | "早起き コツ" "morning routine that works" "how to become a morning person" |
| **self_loathing** | "自分が嫌い" "自己嫌悪 ループ" "I hate myself" "why am I like this" | "自己嫌悪 手放す" "self compassion tips" "how to stop hating yourself" |
| **rumination** | "反芻思考 止まらない" "ずっと考えてしまう" "can't stop overthinking" "my brain won't shut up" | "反芻 止める方法" "how to stop ruminating" "overthinking solutions" |
| **procrastination** | "先延ばし 自分最悪" "やらなきゃいけないのに" "procrastination is ruining my life" "I keep putting things off" | "先延ばし 克服" "procrastination hack" "how to just start" |
| **anxiety** | "不安 消えない" "漠然とした不安" "anxiety won't go away" "constant worry" | "不安 対処法" "anxiety relief techniques" "how to calm anxiety" |
| **lying** | "嘘ついてしまう" "嘘がやめられない" "I can't stop lying" "why do I keep lying" | "嘘 やめる方法" "compulsive lying help" "how to be more honest" |
| **bad_mouthing** | "悪口 やめたい" "人の悪口 言ってしまう" "I talk behind people's backs" "can't stop gossiping" | "悪口 やめる" "how to stop talking bad about others" "gossip habit break" |
| **porn_addiction** | "ポルノ依存" "やめたいのにやめられない" "porn addiction struggle" "nofap relapse" | "ポルノ やめる方法" "nofap tips" "how to quit porn" |
| **alcohol_dependency** | "酒 やめられない" "また飲んでしまった" "can't stop drinking" "alcohol ruining my life" | "禁酒 方法" "how to stop drinking" "sobriety tips" "sober curious" |
| **anger** | "怒り コントロールできない" "すぐキレてしまう" "anger issues" "I can't control my temper" | "怒り 管理" "anger management tips" "how to control anger" |
| **obsessive** | "強迫的思考" "同じこと何回も確認" "obsessive thoughts won't stop" "OCD intrusive thoughts" | "強迫観念 対処" "how to deal with obsessive thoughts" "intrusive thoughts tips" |
| **loneliness** | "孤独 つらい" "誰にもわかってもらえない" "so lonely it hurts" "nobody understands me" | "孤独 乗り越える" "how to cope with loneliness" "feeling alone tips" |

### クエリローテーション戦略

1実行あたり全13個は検索しない（Rate Limit + コスト対策）。
ローテーションで1回あたり3-4個のProblemTypeを検索する。

```javascript
// 13 ProblemTypesを3グループに分割（4-5個ずつ）
const ROTATION_GROUPS = [
  ['staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination', 'procrastination'],
  ['anxiety', 'lying', 'bad_mouthing', 'porn_addiction'],
  ['alcohol_dependency', 'anger', 'obsessive', 'loneliness'],
];

// 実行回数 % 3 でグループを選択
// 1日6回実行 × 3グループ = 2日で全ProblemType網羅
const groupIndex = executionCount % ROTATION_GROUPS.length;
const targetTypes = ROTATION_GROUPS[groupIndex];
```

## 処理フロー

### Step 1: トレンド収集（ProblemType別 × ソース別）

選択されたProblemTypeグループに対して、各ソースから並列で検索。

#### 1a. TikTok（Apify `clockworks/tiktok-trends-scraper` 経由）

```javascript
// Apify TikTok Trends Scraper — Creative Center のトレンドデータを自動取得
// 既存の APIFY_API_TOKEN を利用（clockworks~tiktok-scraper と同じアカウント）
// ログイン不要、GUI作業なし

const APIFY_TOKEN = process.env.APIFY_API_TOKEN;
const ACTOR_ID = 'clockworks~tiktok-trends-scraper';

// 日本 + グローバルのトレンドハッシュタグを取得
const regions = ['JP', 'US', 'GB']; // 日本、アメリカ、イギリス

for (const region of regions) {
  // Apify Actor を実行
  const runResult = await exec(`curl -s -X POST \
    "https://api.apify.com/v2/acts/${ACTOR_ID}/runs?token=${APIFY_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"countryCode": "${region}", "period": 7, "dataType": "hashtag"}'`);

  const runId = JSON.parse(runResult).data.id;

  // 完了待ち（最大5分、5秒間隔でポーリング）
  let status = 'RUNNING';
  while (status === 'RUNNING') {
    await sleep(5000);
    const check = await exec(`curl -s \
      "https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}"`);
    status = JSON.parse(check).data.status;
  }

  // 結果取得
  const datasetId = JSON.parse(await exec(`curl -s \
    "https://api.apify.com/v2/actor-runs/${runId}?token=${APIFY_TOKEN}"`)).data.defaultDatasetId;

  const items = await exec(`curl -s \
    "https://api.apify.com/v2/datasets/${datasetId}/items?token=${APIFY_TOKEN}"`);

  const hashtags = JSON.parse(items);

  // ProblemType関連のハッシュタグをフィルタ
  // カテゴリ: Education, Life, Sports & Outdoor（メンタルヘルス系が多い）
  const relevant = hashtags.filter(h =>
    ['Education', 'Life'].includes(h.industryName) ||
    PROBLEM_TYPE_KEYWORDS.some(kw =>
      h.name.toLowerCase().includes(kw)
    )
  );

  trends.push(...relevant.map(h => ({
    source: 'tiktok',
    hashtag: h.name,
    rank: h.rank,
    videoCount: h.videoCount,
    viewCount: h.viewCount,
    rankDiff: h.rankDiff,       // ランク変動（+3 = 急上昇）
    isNew: h.markedAsNew,       // 新規トレンド
    region: h.countryCode,
    industry: h.industryName,
  })));
}

// ProblemType関連キーワード（ハッシュタグ名のフィルタ用）
const PROBLEM_TYPE_KEYWORDS = [
  'sleep', 'insomnia', 'nightowl', 'wakeup', 'morning',     // staying_up_late, cant_wake_up
  'selfcare', 'selflove', 'selfworth', 'mentalhealth',       // self_loathing
  'overthinking', 'anxiety', 'worry', 'stress',               // rumination, anxiety
  'procrastination', 'productivity', 'motivation', 'lazy',    // procrastination
  'honesty', 'trust', 'lying',                                 // lying
  'anger', 'angermanagement', 'calm',                          // anger
  'ocd', 'obsessive', 'intrusive',                             // obsessive
  'lonely', 'loneliness', 'alone',                             // loneliness
  'addiction', 'sober', 'nofap', 'recovery',                   // porn_addiction, alcohol_dependency
  'habit', 'routine', 'discipline', 'mindset',                 // 全般
  // 日本語ハッシュタグ
  '夜更かし', '朝活', '不安', 'メンタル', '習慣', '依存',
  '自己嫌悪', '先延ばし', '孤独', '怒り',
];

// コスト見積もり:
// 1回の実行: 3リージョン × 1 Actor Run = 3 Apify runs
// 1日6実行: 18 runs（各run で ~50-100ハッシュタグ取得）
// Apify Free: $5/月で約800件。18 × 30 = 540 runs → 無料枠内
```

#### 1b. Reddit（reddapi.dev セマンティック検索）

```javascript
// reddapi - 各ProblemTypeに対してセマンティック検索
// 共感系: 当事者の投稿を検索
// 問題解決系: 対処法を検索

for (const problemType of targetTypes) {
  const queries = QUERY_DICT[problemType];

  // 共感系: 当事者の叫び
  const empathyResult = await exec(`curl -s -X POST "https://reddapi.dev/api/v1/search/semantic" \
    -H "Authorization: Bearer ${REDDAPI_API_KEY}" \
    -d '{"query": "${queries.empathy_en}", "limit": 20}'`);

  // 問題解決系: 対処法バズ
  const solutionResult = await exec(`curl -s -X POST "https://reddapi.dev/api/v1/search/semantic" \
    -H "Authorization: Bearer ${REDDAPI_API_KEY}" \
    -d '{"query": "${queries.solution_en}", "limit": 20}'`);

  // score（upvote）が高いものだけ取得（バイラル判定）
  trends.push(...parseRedditResults(empathyResult, { problemType, type: 'empathy', minScore: 100 }));
  trends.push(...parseRedditResults(solutionResult, { problemType, type: 'solution', minScore: 100 }));
}

// 加えて、トレンドAPI で急成長トピックも取得
const trending = await exec(`curl -s "https://reddapi.dev/api/v1/trends" \
  -H "Authorization: Bearer ${REDDAPI_API_KEY}"`);
// growth_rate 上位から ProblemType に関連するものをフィルタ
```

#### 1c. X/Twitter（TwitterAPI.io 経由 — 公式X API不使用）

```javascript
// TwitterAPI.io: $0.15/1,000ツイート。メトリクス（いいね/RT/リプライ）取得可能。
// X API Free は write-only で検索不可。Basic は $200/月で高すぎる。
// Firecrawl は x.com を明示的にブロック。Brave site:x.com は不安定。

const TWITTERAPI_BASE = 'https://api.twitterapi.io/twitter';

for (const problemType of targetTypes) {
  const queries = QUERY_DICT[problemType];

  // 共感系（英語）: いいね1000以上のバズ投稿
  const empathyEn = await exec(`curl -s -X GET \
    "${TWITTERAPI_BASE}/tweet/advanced_search?query=${encodeURIComponent(queries.empathy_en + ' min_faves:1000')}&queryType=Top&cursor=" \
    -H "X-API-Key: ${TWITTERAPI_KEY}"`);

  // 問題解決系（英語）
  const solutionEn = await exec(`curl -s -X GET \
    "${TWITTERAPI_BASE}/tweet/advanced_search?query=${encodeURIComponent(queries.solution_en + ' min_faves:500')}&queryType=Top&cursor=" \
    -H "X-API-Key: ${TWITTERAPI_KEY}"`);

  // 共感系（日本語）: いいね100以上（日本語圏はボリューム少ないので閾値低め）
  const empathyJa = await exec(`curl -s -X GET \
    "${TWITTERAPI_BASE}/tweet/advanced_search?query=${encodeURIComponent(queries.empathy_ja + ' min_faves:100')}&queryType=Top&cursor=" \
    -H "X-API-Key: ${TWITTERAPI_KEY}"`);

  // 問題解決系（日本語）
  const solutionJa = await exec(`curl -s -X GET \
    "${TWITTERAPI_BASE}/tweet/advanced_search?query=${encodeURIComponent(queries.solution_ja + ' min_faves:50')}&queryType=Top&cursor=" \
    -H "X-API-Key: ${TWITTERAPI_KEY}"`);

  // レスポンスからメトリクス付きで取得
  // { text, likes, retweets, replies, author, url }
  trends.push(
    ...parseTweetsWithMetrics(empathyEn, { problemType, type: 'empathy', lang: 'en' }),
    ...parseTweetsWithMetrics(solutionEn, { problemType, type: 'solution', lang: 'en' }),
    ...parseTweetsWithMetrics(empathyJa, { problemType, type: 'empathy', lang: 'ja' }),
    ...parseTweetsWithMetrics(solutionJa, { problemType, type: 'solution', lang: 'ja' }),
  );
}

// レスポンスパーサー
function parseTweetsWithMetrics(response, meta) {
  const data = JSON.parse(response);
  return (data.tweets || []).map(tweet => ({
    source: 'x',
    problemType: meta.problemType,
    queryType: meta.type,
    lang: meta.lang,
    text: tweet.text,
    metrics: {
      likes: tweet.likeCount,
      retweets: tweet.retweetCount,
      replies: tweet.replyCount,
    },
    author: tweet.author?.userName,
    url: `https://x.com/${tweet.author?.userName}/status/${tweet.id}`,
  }));
}

// コスト見積もり:
// 1実行あたり: 4クエリ × 4ProblemType = 16リクエスト（各20件 = 320ツイート）
// 1日6実行: 96リクエスト（1,920ツイート）
// 月間コスト: 1,920 × 30 ÷ 1,000 × $0.15 = **約$8.64/月**
```

#### 1d. GitHub Trending（補助 — trend-watcher方式）

```javascript
// trend-watcher の httpRequest + parseTrendingHTML を流用
// メンタルヘルス・セルフケア系のリポジトリをチェック

const html = await httpRequest('https://github.com/trending?since=daily', 8000);
const repos = parseTrendingHTML(html);

// カテゴリフィルタ: メンタルヘルス、瞑想、習慣系
const MENTAL_HEALTH_KEYWORDS = [
  'meditation', 'mindfulness', 'habit', 'mental-health', 'wellness',
  'self-care', 'journaling', 'mood', 'anxiety', 'sleep',
];

const relevant = repos.filter(repo => {
  const text = `${repo.name} ${repo.description}`.toLowerCase();
  return MENTAL_HEALTH_KEYWORDS.some(kw => text.includes(kw));
});

// テック系トレンドは補助データとして保存（hook生成の優先度は低い）
trends.push(...relevant.map(r => ({
  source: 'github',
  type: 'tech_trend',
  ...r,
})));
```

### Step 2: Aniccaフィルタ（LLM判定）

収集したトレンドをLLMに渡して、hook候補としての価値を判定する。

```javascript
const FILTER_PROMPT = `
あなたはAniccaのトレンドアナリストです。

## Aniccaのターゲットペルソナ
- 25-35歳、6-7年間習慣化に失敗し続けている人
- 習慣アプリを10個以上試して全部3日坊主で挫折
- 「自分はダメな人間だ」と信じ込んでいる
- 諦めモードだが心の奥では変わりたい

## Aniccaの13 ProblemTypes
staying_up_late, cant_wake_up, self_loathing, rumination,
procrastination, anxiety, lying, bad_mouthing, porn_addiction,
alcohol_dependency, anger, obsessive, loneliness

## 2種類のバイラルコンテンツ
1. 共感系: 当事者が苦しみを語り、「わかる」「俺もそう」とバズっている
   → Aniccaの「あなただけじゃない」系hookに変換
2. 問題解決系: 「○○をやめる方法5選」「△△の対処法」等でバズっている
   → Aniccaの機能紹介hookに変換

## 以下のトレンドを分析してください:

{trends_json}

各トレンドに対して以下をJSON配列で返してください:
{
  "trend_id": "元のID",
  "relevance_score": 0-10,
  "virality": "high|medium|low",
  "content_type": "empathy|solution",
  "problemTypes": ["関連するProblemType（複数可）"],
  "angle": "Aniccaがこのトレンドにどう乗れるか（1行）",
  "skip_reason": "スキップ理由（relevance < 5 の場合のみ）"
}

## 判定基準
- relevance_score >= 5 AND virality != 'low' → 通過
- 苦しみの当事者投稿で大量共感 → 高スコア（共感系hook向き）
- 対処法・方法論で高エンゲージメント → 高スコア（問題解決系hook向き）
- ProblemTypeに直接関係ない一般的な話題 → 低スコア
`;
```

### Step 3: hook候補生成（LLM生成）

```javascript
const HOOK_PROMPT = `
フィルタを通過したトレンド:
{filtered_trends_json}

## hook生成ルール

### 絶対禁止
- 「簡単に習慣化！」「たった○日で！」→ ペルソナは信じない、警戒する
- 上から目線のアドバイス → ペルソナは反発する
- 「あなたは大丈夫」的な安易な励まし → 空虚に感じる

### 刺さるhookパターン
- 共感系: 「6年間、何も変われなかった」「習慣アプリ10個全部挫折」
- 問題解決系: 具体的で小さいステップ。「まず1つだけ」「完璧じゃなくていい」
- トレンドのハッシュタグ/キーワードを自然に含める（検索流入のため）

### 共感系hookの生成パターン
元トレンド: 「夜中3時にスマホ見てるの俺だけ？」（バズ: いいね5000+）
→ hook: 「毎晩『今日こそ早く寝る』って決めて、気づいたら3時。
   6年間ずっとこれ。同じ人いる？ #夜更かし #寝れない」

### 問題解決系hookの生成パターン
元トレンド: 「夜更かしを直す5つの方法」（バズ: RT2000+）
→ hook: 「夜更かしを直す方法、全部知ってる。全部試した。全部3日で終わった。
   方法が悪いんじゃない。続けられない自分がいるだけ。
   だから方法じゃなくて、続ける仕組みを変えた。 #夜更かし」

## 出力（JSON配列、最大5件）
{
  "content": "hookテキスト（max 500 chars）",
  "contentType": "empathy|solution",
  "trendSource": {
    "platform": "tiktok|reddit|x|github",
    "url": "元トレンドのURL（あれば）",
    "hashtags": ["関連ハッシュタグ"],
    "metrics": { "likes": 5000, "retweets": 2000 }
  },
  "angle": "切り口の説明",
  "problemTypes": ["staying_up_late"],
  "platform": "x|tiktok|both"
}
`;
```

### Step 4: 重複チェック & 保存

```javascript
// 1. 既存hookを取得
const existingHooks = await exec(`curl -s \
  -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" \
  "https://anicca-proxy-staging.up.railway.app/api/agent/hooks"`);

// 2. 各候補に対して重複チェック
for (const candidate of hookCandidates) {
  // テキスト類似度チェック（LLMに判定させる）
  const isDuplicate = await checkSimilarity(candidate.content, existingHooks, threshold=0.8);

  if (!isDuplicate) {
    // 3. Railway DB に保存
    await exec(`curl -s -X POST \
      -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" \
      -H "Content-Type: application/json" \
      "https://anicca-proxy-staging.up.railway.app/api/agent/hooks" \
      -d '${JSON.stringify({
        content: candidate.content,
        problemType: candidate.problemTypes[0], // 主要ProblemType
        source: "trend-hunter",
        metadata: {
          contentType: candidate.contentType,
          trendSource: candidate.trendSource,
          allProblemTypes: candidate.problemTypes,
          platform: candidate.platform,
          angle: candidate.angle,
        }
      })}'`);
  }
}

// 4. Slack #trends に結果サマリー
await slack.send('#trends',
  `🔍 トレンドスキャン完了\n` +
  `対象: ${targetTypes.join(', ')}\n` +
  `TikTok: ${tiktokCount}件 | Reddit: ${redditCount}件 | X: ${xCount}件\n` +
  `→ フィルタ通過: ${filteredCount}件 → 新規hook: ${savedCount}件\n` +
  `共感系: ${empathyCount} | 問題解決系: ${solutionCount}`
);
```

## Required Tools

| ツール | 用途 |
|--------|------|
| `exec` | TwitterAPI.io呼び出し、reddapi API呼び出し、Apify API呼び出し、Railway API呼び出し |
| `web_search` | 補助検索（Brave API経由） |
| `slack` | 結果サマリー投稿 |
| `read` | 設定ファイル、既存hook一覧 |
| `write` | DLQ書き込み |

## Error Handling

| エラー | 対応 |
|--------|------|
| TwitterAPI.io 失敗/停止 | TikTok + Reddit の結果のみで続行。Slack #alerts に通知 |
| Apify TikTok Scraper 失敗 | X + Reddit の結果のみで続行 |
| reddapi API失敗 | X + TikTok の結果のみで続行 |
| LLMフィルタ/生成失敗 | Fallback Chain（gpt-4o → gpt-4o-mini → claude-3-5-haiku → llama-3.3-70b） |
| Railway API保存失敗 | DLQ に書き込み、次回実行時にリトライ |
| 全ソース失敗 | Slack #alerts に通知、DLQに記録 |

## Cron設定

```yaml
trend-hunter:
  skill: trend-hunter
  cron: "0 */4 * * *"   # 4時間ごと（1日6回）
  session: isolated
  delivery:
    mode: "none"
  prompt: |
    trend-hunter スキルを実行してください。

    1. 今回のローテーショングループを決定（実行回数 % 3）
    2. 対象ProblemTypeに対して、TikTok / Reddit / X から並列でトレンド収集
    3. Aniccaフィルタ（LLM）で関連度・バイラル度を判定
    4. 通過したトレンドからhook候補を生成（共感系 + 問題解決系、最大5件/回）
    5. 重複チェック後、Railway DBに保存
    6. Slack #trends に結果サマリーを投稿

    exec, browser, web_search, slack ツールを使用してください。
```

## 必要な環境変数

| 変数 | 用途 | コスト | 取得方法 | ステータス |
|------|------|--------|---------|-----------|
| `TWITTERAPI_KEY` | TwitterAPI.io（X検索+メトリクス） | $0.15/1k件（月~$9） | twitterapi.io でGoogle登録 | **ユーザーGUI作業必要** |
| `REDDAPI_API_KEY` | reddapi.dev セマンティック検索 | $9.90/月（Liteプラン） | reddapi.dev でGoogle/GitHub登録 | **ユーザーGUI作業必要** |
| `APIFY_API_TOKEN` | Apify TikTok Trends Scraper | 既存Apify枠内（$5/月） | **既にGitHub Secretsに登録済み** | **VPSの.envにもあるか要確認** |
| `ANICCA_AGENT_TOKEN` | Railway API 認証 | なし | 既存（VPSの.envにある） | 済 |
| `BRAVE_API_KEY` | web_search（補助検索） | 既存 | VPSの.envにある | 済 |

### 月間コスト見積もり

| 項目 | 計算 | 月額 |
|------|------|------|
| TwitterAPI.io | 1,920ツイート/日 × 30日 ÷ 1,000 × $0.15 | ~$9 |
| reddapi.dev Lite | 500 API calls/月（固定） | $9.90 |
| Apify TikTok Trends | 既存無料枠（$5/月クレジット）内で~540 runs | $0 |
| LLM（フィルタ+hook生成） | 12回/日 × 30日、gpt-4o-mini推定 | ~$3 |
| **合計** | | **~$22/月** |

## trend-watcher（ClawHub）からの流用

| 流用するもの | 内容 |
|------------|------|
| **スキル構造** | SKILL.md + index.js + _meta.json の3ファイル構成 |
| **HTTPリクエスト関数** | `httpRequest()` — タイムアウト付き、Node.js標準のみ |
| **HTMLパーサーパターン** | `parseTrendingHTML()` — GitHub Trending用。TikTok Creative Center にも応用 |
| **カテゴリフィルタ方式** | キーワード辞書 → 13 ProblemType辞書に置き換え |
| **キャッシュデータ方式** | API失敗時のフォールバック用ローカルキャッシュ |

## reddapi（ClawHub）からの流用

| 流用するもの | 内容 |
|------------|------|
| **セマンティック検索パターン** | `"I wish there was an app that"` 系のクエリ設計 |
| **トレンドAPI** | `growth_rate` によるトレンド急成長検出 |
| **curlベースの実装** | OpenClaw exec ツールとの親和性が高い |

## x-poster との連携（データフロー）

```
trend-hunter (4h間隔)
    ↓ ProblemType別にバイラルコンテンツ検出
    ↓ 共感系 + 問題解決系の hook候補を生成
    ↓ POST /api/agent/hooks
    ↓
Railway DB (Hook テーブル)
    ↓ Thompson Sampling で選択
    ↓ contentType (empathy/solution) も考慮
    ↓
x-poster (09:00/21:00 JST)
    ↓ 朝=問題解決系（行動促進）、夜=共感系（寄り添い）
    ↓ content-verifier で検証
    ↓ X API で投稿
    ↓
投稿結果 → Hook統計更新 → Thompson Sampling の学習
    ↓
trend-hunter が学習結果を参照
    ↓ 高スコアProblemType → 検索頻度UP
    ↓ 低スコアProblemType → 検索頻度DOWN
```

## 共感系 vs 問題解決系の具体例

### staying_up_late（夜更かし）

**共感系バイラルの例:**
> 「毎日『今日は早く寝よう』って決めてるのに気づいたら2時半で
> スマホ握りしめてる人、いいねしてくれ」
> → いいね: 50,000+ RT: 12,000+

**Aniccaが乗せるhook:**
> 「毎晩同じ約束を自分にして、毎晩破る。6年間ずっとこれ。
> 意志の問題だと思ってた。違った。仕組みの問題だった。 #夜更かし」

---

**問題解決系バイラルの例:**
> 「夜更かしを科学的に直す方法5選:
> 1. ブルーライトカット 2. 寝室にスマホ持ち込まない...」
> → いいね: 30,000+ RT: 8,000+

**Aniccaが乗せるhook:**
> 「夜更かしを直す方法、全部知ってる。全部試した。全部3日で終わった。
> 知識が足りないんじゃない。『やめた後の暇な時間』に耐えられないだけ。
> だからAniccaは、その『暇な時間』に寄り添う。 #夜更かし #睡眠」

### self_loathing（自己嫌悪）

**共感系バイラルの例:**
> 「自分のこと好きな人ってマジでどうやってるの？
> 朝起きた瞬間から自分が嫌いなんだけど」
> → いいね: 80,000+ RT: 20,000+

**Aniccaが乗せるhook:**
> 「『自分を好きになろう』って言われても、好きになれないから困ってる。
> 好きにならなくていい。ただ、嫌いな自分のまま、1つだけ動いてみる。
> それだけでいい。 #自己嫌悪 #メンタルヘルス」

### obsessive（強迫的思考）

**共感系バイラルの例:**
> 「鍵閉めたか4回確認して、車に乗ってからもう1回戻る。
> これ毎日やってる人いる？」
> → いいね: 40,000+ RT: 15,000+

**Aniccaが乗せるhook:**
> 「『確認しなくていい、大丈夫』って頭では分かってる。
> でも体が勝手に戻る。これ、意志じゃどうにもならない。
> だから意志以外の仕組みが必要だった。 #強迫性障害 #OCD」
```

---

## 調査結果: ClawHubスキル精査

### 取得した5スキルの安全性判定

| スキル | 安全性 | 判定理由 |
|--------|--------|---------|
| **trend-watcher** | 安全 | 依存ライブラリなし（Node.js標準のみ）。GitHub Trendingをスクレイピングするだけ |
| **xtrends** | マルウェア | `openclawcli` という出所不明バイナリのインストールを要求。パスワード付きZIP + glot.ioスクリプト実行 |
| **x-search** | 要注意 | x402プロトコルで1リクエスト$0.05 USDC課金。暗号通貨ウォレットの秘密鍵をファイルに保存させる |
| **reddapi** | 安全 | curlでreddapi.dev APIを叩くだけ。外部バイナリなし |
| **twitter-search-skill** | 安全 | twitterapi.io + Pythonスクリプト。外部バイナリなし |

### 各スキルの詳細内容

（調査結果の全文は省略。必要時に再取得可能。）

| スキル | 主要技術 | DL数 | Aniccaへの有用性 |
|--------|---------|------|----------------|
| **trend-watcher** | Node.js + GitHub Trending HTMLスクレイピング | 300 | 高（構造テンプレート + HTTPリクエスト関数を流用） |
| **xtrends** | twurl（Twitter公式CLI）+ マルウェア | - | 使用禁止 |
| **x-search** | npx x402-tools-claude + USDC支払い | - | 不要（コスト高） |
| **reddapi** | curl + reddapi.dev REST API | 93 | 高（セマンティック検索 + growth_rate トレンド検出） |
| **twitter-search-skill** | Python + twitterapi.io | - | 高（**TwitterAPI.ioを採用決定**。クエリ構文+API仕様の参考） |

---

## 調査結果: X/TikTok データ取得手段（2026-02-08 実施）

### X (Twitter) データ取得方法の調査

| 手段 | 検索 | メトリクス（いいね/RT） | コスト/月 | 実用性 | 備考 |
|------|------|----------------------|----------|--------|------|
| X API Free | 不可（write-only） | 不可 | $0 | **不可** | 2025年8月にいいね/フォロー機能も削除 |
| X API Basic | 7日間（15k件/月） | 可 | $200 | 可だが高い | 以前$100だったが値上げ |
| X API Pro | フルアーカイブ（1M件/月） | 可 | $5,000 | 論外 | エンタープライズ向け |
| X API Pay-Per-Use | 不明 | 不明 | 従量制 | **クローズドベータ** | 招待制、一般利用不可 |
| **TwitterAPI.io** | **無制限** | **可** | **~$9** | **最有力** | $0.15/1k件。X開発者アカウント不要 |
| SociaVault | 可 | 可 | $99~ | 高め | 中規模モニタリング向け |
| Firecrawl + x.com | **明示的ブロック** | 不可 | - | **不可** | 「We do not support this site」エラー |
| Brave `site:x.com` | 極少 | 不可 | $0 | **不可** | インデックス依存、信頼性低 |
| Nitter | 不可 | 不可 | $0 | **不可** | 2024年2月に公式終了 |

**採用: TwitterAPI.io** — コスト最小（~$9/月）、メトリクス取得可能、認証簡単。

### TikTok Creative Center スクレイピング調査

| 手段 | 取得範囲 | メトリクス | 実用性 |
|------|---------|----------|--------|
| Firecrawl | **トップ3のみ** | ハッシュタグ名+投稿数のみ | 不十分 |
| **browser (Playwright)** | **フルリスト** | ハッシュタグ+投稿数+カテゴリ+New判定 | **採用** |

**Firecrawl実テスト結果（2026-02-08）:**
- `ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en` をスクレイピング
- トップ3（#zerotohero 49K, #livebringfans 42K, #championsleague 11K）のみ取得成功
- 「View More」以降はJS描画で取得不可
- **結論: Firecrawlでは不十分。browser (Playwright) ツールでフルリスト取得が必要**

---

## テスト可能なコード境界（P0-1）

### アーキテクチャ原則

```
Pure Functions（決定論的・テスト容易）
    ↕ データだけやり取り
Mockable Interfaces（外部API・LLM呼び出し）
```

**純粋関数**: 同じ入力 → 常に同じ出力。副作用なし。ユニットテストのみで100%カバー。
**Mockableインターフェース**: 外部APIやLLMの呼び出し。テスト時はモックに差し替え。

### モジュール一覧

| モジュール | 種別 | 責務 | 入力 | 出力 |
|-----------|------|------|------|------|
| `queryBuilder` | Pure | ProblemType → 検索クエリ文字列を組み立て | `(problemType, contentType, lang)` | `string` |
| `rotationSelector` | Pure | 実行回数からローテーショングループを選択 | `(executionCount)` | `string[]`（ProblemType配列） |
| `twitterResponseParser` | Pure | TwitterAPI.io の生JSONを正規化 | `(rawJson, meta)` | `NormalizedTrend[]` |
| `redditResponseParser` | Pure | reddapi.dev の生JSONを正規化 | `(rawJson, meta)` | `NormalizedTrend[]` |
| `tiktokResponseParser` | Pure | Apify TikTok の生JSONを正規化 | `(rawJson)` | `NormalizedTrend[]` |
| `viralityFilter` | Pure | メトリクス閾値でフィルタ | `(trends[], thresholds)` | `NormalizedTrend[]` |
| `textSimilarity` | Pure | 2テキスト間の類似度計算（Jaccard） | `(text1, text2)` | `number`（0.0-1.0） |
| `slackFormatter` | Pure | 結果サマリーをSlackメッセージ文字列に変換 | `(results)` | `string` |
| `twitterApiClient` | Mockable | TwitterAPI.io への HTTP呼び出し | `(query, options)` | `Promise<RawTwitterResponse>` |
| `redditApiClient` | Mockable | reddapi.dev への HTTP呼び出し | `(query, options)` | `Promise<RawRedditResponse>` |
| `tiktokApiClient` | Mockable | Apify Actor 実行 + 結果取得 | `(region, options)` | `Promise<RawTikTokResponse>` |
| `llmClient` | Mockable | LLMフィルタ + hook生成 | `(prompt, data)` | `Promise<LlmResponse>` |
| `railwayApiClient` | Mockable | Railway API GET/POST hooks | `(method, data?)` | `Promise<ApiResponse>` |
| `orchestrator` | 統合 | 全モジュールを繋いで実行 | `(config)` | `Promise<ExecutionResult>` |

### 正規化データ型

```typescript
// 全ソース共通の正規化型
interface NormalizedTrend {
  id: string;                          // ソース固有ID
  source: 'x' | 'tiktok' | 'reddit' | 'github';
  problemType: string;                 // 検索時のProblemType
  contentType: 'empathy' | 'solution'; // 検索クエリの種別
  lang: 'ja' | 'en';
  text: string;                        // 本文 or ハッシュタグ名
  url: string | null;                  // 元投稿URL
  metrics: {
    engagement: number;                // ソースごとの主要指標（正規化済み）
    // X: likeCount, Reddit: upvotes, TikTok: viewCount
  };
  author: string | null;
  raw: Record<string, unknown>;        // パーサーが捨てなかった元データ
}

// LLMフィルタ出力型
interface FilteredTrend {
  trendId: string;
  relevanceScore: number;              // 0-10
  virality: 'high' | 'medium' | 'low';
  contentType: 'empathy' | 'solution';
  problemTypes: string[];
  angle: string;
  skipReason: string | null;
}

// hook候補型
interface HookCandidate {
  content: string;                     // hookテキスト（max 500 chars）
  contentType: 'empathy' | 'solution';
  problemTypes: string[];
  platform: 'x' | 'tiktok' | 'both';
  trendSource: {
    platform: string;
    url: string | null;
    hashtags: string[];
    metrics: Record<string, number>;
  };
  angle: string;
}
```

---

## テストマトリックス（P0-2）

### Pure Functions テスト

#### queryBuilder

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 1 | `test_queryBuilder_empathy_ja` | `('staying_up_late', 'empathy', 'ja')` | `'"また3時だ" OR "夜更かし やめられない"'` を含む文字列 | 日本語共感系 |
| 2 | `test_queryBuilder_solution_en` | `('staying_up_late', 'solution', 'en')` | `'"how to fix sleep schedule" OR "screen time before bed"'` を含む文字列 | 英語問題解決系 |
| 3 | `test_queryBuilder_all_problemTypes` | 13個のProblemType全て | 全てnon-emptyの文字列を返す（null/undefinedなし） | 辞書網羅 |
| 4 | `test_queryBuilder_unknown_type_throws` | `('invalid_type', 'empathy', 'ja')` | `Error` をthrow | 不正入力 |
| 5 | `test_queryBuilder_min_faves_appended` | `('anxiety', 'empathy', 'en')` に `{minFaves: 1000}` オプション | `'min_faves:1000'` が末尾に付与 | X検索オプション |

#### rotationSelector

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 6 | `test_rotation_group0` | `executionCount=0` | `['staying_up_late','cant_wake_up','self_loathing','rumination','procrastination']` | グループ0 |
| 7 | `test_rotation_group1` | `executionCount=1` | `['anxiety','lying','bad_mouthing','porn_addiction']` | グループ1 |
| 8 | `test_rotation_group2` | `executionCount=2` | `['alcohol_dependency','anger','obsessive','loneliness']` | グループ2 |
| 9 | `test_rotation_wraps` | `executionCount=3` | グループ0と同じ | 循環 |
| 10 | `test_rotation_large_number` | `executionCount=999` | グループ `999%3=0` | 大きい数 |

#### twitterResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 11 | `test_parse_twitter_valid` | モックレスポンス（tweets配列2件） | `NormalizedTrend[]` 長さ2、source='x'、metrics.engagement=likeCount | 正常系 |
| 12 | `test_parse_twitter_empty` | `{"tweets":[],"has_next_page":false}` | 空配列 | 空レスポンス |
| 13 | `test_parse_twitter_missing_author` | author=null のtweet | `NormalizedTrend` でauthor=null、url=null | 欠損データ |
| 14 | `test_parse_twitter_malformed_json` | `"not json"` | `Error` をthrow | 不正JSON |

#### redditResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 15 | `test_parse_reddit_valid` | モックレスポンス（results配列3件） | `NormalizedTrend[]` 長さ3、source='reddit'、metrics.engagement=upvotes | 正常系 |
| 16 | `test_parse_reddit_empty` | `{"success":true,"data":{"results":[]}}` | 空配列 | 空レスポンス |
| 17 | `test_parse_reddit_api_error` | `{"success":false,"error":"Rate limited"}` | `Error` をthrow | APIエラー |

#### tiktokResponseParser

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 18 | `test_parse_tiktok_valid` | モックレスポンス（ハッシュタグ配列2件） | `NormalizedTrend[]` 長さ2、source='tiktok'、metrics.engagement=viewCount | 正常系 |
| 19 | `test_parse_tiktok_filter_promoted` | `isPromoted: true` のハッシュタグ含む | promotedを除外 | プロモ除外 |
| 20 | `test_parse_tiktok_empty` | `[]` | 空配列 | 空レスポンス |

#### viralityFilter

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 21 | `test_filter_above_threshold` | engagement=5000, threshold=1000 | 通過（配列に含む） | 閾値以上 |
| 22 | `test_filter_below_threshold` | engagement=500, threshold=1000 | 除外（配列に含まない） | 閾値未満 |
| 23 | `test_filter_exact_threshold` | engagement=1000, threshold=1000 | 通過（>=で判定） | 境界値 |
| 24 | `test_filter_mixed` | 5件中2件が閾値以上 | 長さ2の配列 | 混在 |
| 25 | `test_filter_source_specific_thresholds` | X=1000, Reddit=100, TikTok=10000 のソース別閾値 | 各ソースの閾値で判定 | ソース別閾値 |

#### textSimilarity

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 26 | `test_similarity_identical` | `("hello world", "hello world")` | `1.0` | 完全一致 |
| 27 | `test_similarity_different` | `("hello world", "goodbye moon")` | `< 0.3` | 完全不一致 |
| 28 | `test_similarity_partial` | `("夜更かし やめたい", "夜更かし やめられない つらい")` | `0.3 < x < 0.8` | 部分一致 |
| 29 | `test_similarity_empty_string` | `("", "hello")` | `0.0` | 空文字列 |
| 30 | `test_similarity_threshold_check` | 類似度 > 0.8 のペア | `isDuplicate = true` | 重複判定閾値 |

#### slackFormatter

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 31 | `test_format_normal` | tiktok:3, reddit:5, x:10, saved:4 | ソース別件数 + 保存件数を含むメッセージ | 正常系 |
| 32 | `test_format_all_zero` | 全ソース0件 | 「トレンド0件」を含むメッセージ | 空結果 |
| 33 | `test_format_source_failure` | reddit: error | 「Reddit: エラー」を含むメッセージ | 部分失敗 |

### Mockable Interfaces テスト（統合テスト）

| # | テスト名 | モック設定 | 期待動作 | カバー |
|---|---------|----------|---------|--------|
| 34 | `test_orchestrator_happy_path` | 全API正常レスポンス + LLM正常出力 | hook候補がRailway APIに保存される | E2Eハッピーパス |
| 35 | `test_orchestrator_twitter_down` | twitterApiClient → Error | TikTok+Redditの結果のみで続行、Slackに警告 | X障害時 |
| 36 | `test_orchestrator_all_sources_down` | 全ApiClient → Error | Slack #alertsに通知、DLQに記録、hookは0件 | 全障害 |
| 37 | `test_orchestrator_llm_fallback` | llmClient gpt-4o → Error, gpt-4o-mini → 正常 | フォールバックで正常完了 | LLMフォールバック |
| 38 | `test_orchestrator_duplicate_skip` | railwayApiClient.getHooks → 既存hookと類似度0.9 | 保存スキップ、ログに記録 | 重複チェック |
| 39 | `test_orchestrator_railway_save_fail` | railwayApiClient.saveHook → Error | DLQに書き込み、次回リトライ | 保存失敗 |
| 40 | `test_orchestrator_rotation` | executionCount=0, 1, 2 を順に実行 | 各グループの ProblemType で検索される | ローテーション |

---

## モックAPIレスポンス（P0-3）

### TwitterAPI.io — Advanced Search レスポンス

```json
{
  "tweets": [
    {
      "type": "tweet",
      "id": "1846987139428634858",
      "url": "https://x.com/testuser/status/1846987139428634858",
      "text": "毎日「今日は早く寝よう」って決めてるのに気づいたら2時半でスマホ握りしめてる人、いいねしてくれ",
      "source": "Twitter for iPhone",
      "retweetCount": 12000,
      "replyCount": 3400,
      "likeCount": 50000,
      "quoteCount": 890,
      "viewCount": 2500000,
      "bookmarkCount": 4500,
      "createdAt": "2026-02-07T18:30:00.000Z",
      "lang": "ja",
      "isReply": false,
      "isRetweet": false,
      "isQuote": false,
      "entities": {
        "hashtags": [
          { "text": "夜更かし" },
          { "text": "寝れない" }
        ],
        "urls": [],
        "mentions": []
      },
      "author": {
        "type": "user",
        "userName": "testuser",
        "name": "テストユーザー",
        "id": "123456789",
        "followers": 15000,
        "following": 500,
        "isBlueVerified": false,
        "profilePicture": "https://pbs.twimg.com/profile_images/xxx/photo.jpg"
      },
      "extendedEntities": {},
      "card": null,
      "place": null
    },
    {
      "type": "tweet",
      "id": "1846987139428634999",
      "url": "https://x.com/sleepexpert/status/1846987139428634999",
      "text": "How to fix your sleep schedule in 7 days: A thread based on neuroscience research 🧵\n\n1. Light exposure within 30 min of waking\n2. No screens 1hr before bed\n3. Same wake time every day (even weekends)",
      "source": "Twitter Web App",
      "retweetCount": 8000,
      "replyCount": 1200,
      "likeCount": 35000,
      "quoteCount": 2100,
      "viewCount": 5000000,
      "bookmarkCount": 12000,
      "createdAt": "2026-02-06T14:00:00.000Z",
      "lang": "en",
      "isReply": false,
      "isRetweet": false,
      "isQuote": false,
      "entities": {
        "hashtags": [],
        "urls": [],
        "mentions": []
      },
      "author": {
        "type": "user",
        "userName": "sleepexpert",
        "name": "Dr. Sleep",
        "id": "987654321",
        "followers": 250000,
        "following": 800,
        "isBlueVerified": true,
        "profilePicture": "https://pbs.twimg.com/profile_images/yyy/photo.jpg"
      },
      "extendedEntities": {},
      "card": null,
      "place": null
    }
  ],
  "has_next_page": true,
  "next_cursor": "DAACCgACGdy1XF2xbk8KAAIZw"
}
```

### reddapi.dev — Semantic Search レスポンス

```json
{
  "success": true,
  "data": {
    "query": "can't stop staying up late scrolling phone",
    "results": [
      {
        "id": "1a2b3c4d",
        "title": "I literally cannot stop staying up until 3am every single night",
        "content": "I've tried everything - setting alarms, putting my phone in another room, downloading sleep apps. Nothing works. I know it's destroying my health but every night I tell myself 'just 5 more minutes' and suddenly it's 3am. Anyone else dealing with this? It's been going on for 6 years now.",
        "subreddit": "r/selfimprovement",
        "upvotes": 4523,
        "comments": 342,
        "created": "2026-02-05T22:15:00Z",
        "relevance": 0.97,
        "sentiment": "negative",
        "url": "https://reddit.com/r/selfimprovement/comments/1a2b3c4d"
      },
      {
        "id": "5e6f7g8h",
        "title": "The real reason you can't sleep on time (it's not what you think)",
        "content": "Sleep psychologist here. The reason most people can't stick to a sleep schedule isn't willpower - it's revenge bedtime procrastination. Your brain feels it didn't get enough 'me time' during the day, so it steals it from your sleep. Here's what actually works...",
        "subreddit": "r/getdisciplined",
        "upvotes": 8901,
        "comments": 567,
        "created": "2026-02-04T15:30:00Z",
        "relevance": 0.92,
        "sentiment": "neutral",
        "url": "https://reddit.com/r/getdisciplined/comments/5e6f7g8h"
      },
      {
        "id": "9i0j1k2l",
        "title": "6 years of trying to fix my sleep schedule. Nothing worked until I did this one thing.",
        "content": "I'm not selling anything. I just finally figured out what was keeping me up. It wasn't the phone. It wasn't caffeine. It was anxiety about tomorrow. Once I started journaling my worries before bed, I started falling asleep in 20 minutes instead of 3 hours.",
        "subreddit": "r/DecidingToBeBetter",
        "upvotes": 2156,
        "comments": 189,
        "created": "2026-02-03T08:45:00Z",
        "relevance": 0.89,
        "sentiment": "positive",
        "url": "https://reddit.com/r/DecidingToBeBetter/comments/9i0j1k2l"
      }
    ],
    "total": 20,
    "processing_time_ms": 1245,
    "ai_summary": "Users commonly report chronic inability to maintain sleep schedules despite knowing the health consequences. Key themes: phone addiction before bed, revenge bedtime procrastination, and underlying anxiety driving late-night behavior."
  }
}
```

### reddapi.dev — Trends レスポンス

```json
{
  "success": true,
  "data": {
    "trends": [
      {
        "topic": "revenge bedtime procrastination",
        "post_count": 1247,
        "total_upvotes": 45632,
        "total_comments": 8934,
        "avg_sentiment": -0.35,
        "top_subreddits": ["r/selfimprovement", "r/getdisciplined", "r/sleep"],
        "trending_keywords": ["phone addiction", "doom scrolling", "sleep schedule", "3am"],
        "trend_score": 98.5,
        "growth_rate": 245.3,
        "sample_posts": [
          {
            "id": "abc123",
            "title": "Anyone else revenge scroll until 3am?",
            "subreddit": "r/selfimprovement",
            "upvotes": 5432
          }
        ]
      },
      {
        "topic": "dopamine detox failures",
        "post_count": 834,
        "total_upvotes": 28900,
        "total_comments": 5600,
        "avg_sentiment": -0.42,
        "top_subreddits": ["r/nosurf", "r/selfimprovement", "r/getdisciplined"],
        "trending_keywords": ["dopamine", "screen time", "addiction", "cold turkey"],
        "trend_score": 87.2,
        "growth_rate": 189.7,
        "sample_posts": [
          {
            "id": "def456",
            "title": "I tried dopamine detox for 30 days and here's what happened",
            "subreddit": "r/nosurf",
            "upvotes": 3210
          }
        ]
      }
    ]
  }
}
```

### Apify TikTok Trends Scraper — 出力レスポンス

```json
[
  {
    "id": "1686858772679682",
    "name": "#sleepschedule",
    "url": "https://www.tiktok.com/tag/sleepschedule",
    "countryCode": "JP",
    "rank": 12,
    "industryName": "Education",
    "videoCount": 4523,
    "viewCount": 15800000,
    "rankDiff": 8,
    "markedAsNew": true,
    "isPromoted": false
  },
  {
    "id": "1686858772679999",
    "name": "#夜更かし",
    "url": "https://www.tiktok.com/tag/夜更かし",
    "countryCode": "JP",
    "rank": 45,
    "industryName": "Life",
    "videoCount": 890,
    "viewCount": 3200000,
    "rankDiff": 15,
    "markedAsNew": false,
    "isPromoted": false
  },
  {
    "id": "1686858772680111",
    "name": "#promoted_wellness",
    "url": "https://www.tiktok.com/tag/promoted_wellness",
    "countryCode": "JP",
    "rank": 3,
    "industryName": "Life",
    "videoCount": 12000,
    "viewCount": 50000000,
    "rankDiff": 0,
    "markedAsNew": false,
    "isPromoted": true
  }
]
```

### Apify API 呼び出しパラメータ

```json
{
  "input": {
    "adsScrapeHashtags": true,
    "resultsPerPage": 100,
    "adsCountryCode": "JP",
    "adsTimeRange": "7",
    "adsHashtagIndustry": ""
  },
  "pricing_note": "$0.005/run + $3.00/1,000 results. 100 hashtags = ~$0.305/run.",
  "sync_endpoint": "https://api.apify.com/v2/acts/clockworks~tiktok-trends-scraper/run-sync-get-dataset-items?token=TOKEN"
}
```

### Railway API — GET /api/agent/hooks レスポンス（期待）

```json
{
  "hooks": [
    {
      "id": "hook_001",
      "content": "毎晩同じ約束を自分にして、毎晩破る。6年間ずっとこれ。",
      "problemType": "staying_up_late",
      "source": "trend-hunter",
      "metadata": {
        "contentType": "empathy",
        "trendSource": { "platform": "x", "url": "https://x.com/..." },
        "allProblemTypes": ["staying_up_late"],
        "platform": "x"
      },
      "createdAt": "2026-02-07T05:00:00Z",
      "stats": {
        "impressions": 0,
        "engagements": 0,
        "score": 0
      }
    }
  ]
}
```

> **注意**: Railway API `/api/agent/hooks` エンドポイントの実装状況は要確認（P1）。
> 存在しない場合、trend-hunter実装前にAPI側で作成が必要。

---

## LLM出力バリデーション（P1）

### フィルタ出力スキーマ

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["trend_id", "relevance_score", "virality", "content_type", "problemTypes", "angle"],
    "properties": {
      "trend_id": { "type": "string" },
      "relevance_score": { "type": "number", "minimum": 0, "maximum": 10 },
      "virality": { "enum": ["high", "medium", "low"] },
      "content_type": { "enum": ["empathy", "solution"] },
      "problemTypes": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
      "angle": { "type": "string", "minLength": 1 },
      "skip_reason": { "type": ["string", "null"] }
    }
  }
}
```

### hook生成出力スキーマ

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "maxItems": 5,
  "items": {
    "type": "object",
    "required": ["content", "contentType", "problemTypes", "platform", "trendSource", "angle"],
    "properties": {
      "content": { "type": "string", "maxLength": 500 },
      "contentType": { "enum": ["empathy", "solution"] },
      "problemTypes": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
      "platform": { "enum": ["x", "tiktok", "both"] },
      "trendSource": {
        "type": "object",
        "required": ["platform"],
        "properties": {
          "platform": { "type": "string" },
          "url": { "type": ["string", "null"] },
          "hashtags": { "type": "array", "items": { "type": "string" } },
          "metrics": { "type": "object" }
        }
      },
      "angle": { "type": "string" }
    }
  }
}
```

**LLM出力がスキーマに適合しない場合**: パースエラーとして処理 → 1回リトライ → 失敗なら当該バッチをスキップしてDLQに記録。

---

## 重複判定アルゴリズム（P1）

### 採用: Jaccard類似度（bi-gram）

LLM呼び出しなしで高速に重複チェックできる軽量アルゴリズム。

```javascript
function jaccardBigram(text1, text2) {
  const bigrams = (s) => {
    const normalized = s.replace(/\s+/g, ' ').trim().toLowerCase();
    const set = new Set();
    for (let i = 0; i < normalized.length - 1; i++) {
      set.add(normalized.substring(i, i + 2));
    }
    return set;
  };

  const a = bigrams(text1);
  const b = bigrams(text2);
  const intersection = new Set([...a].filter(x => b.has(x)));
  const union = new Set([...a, ...b]);

  return union.size === 0 ? 0 : intersection.size / union.size;
}

// 閾値: 0.7以上 = 重複とみなす
const SIMILARITY_THRESHOLD = 0.7;
```

**なぜJaccardか**:
| 手法 | 速度 | 精度 | LLM呼び出し | 適用 |
|------|------|------|------------|------|
| LLMに判定させる | 遅い（1-2秒/ペア） | 最高 | あり（コスト） | 不採用 |
| コサイン類似度（TF-IDF） | 中 | 高 | なし | 大規模向け |
| **Jaccard（bi-gram）** | **最速** | **十分** | **なし** | **採用**（hook数が少ない段階） |
| 完全一致 | 最速 | 低（言い換えを検出不可） | なし | 不採用 |

hook数が1000件超になったらコサイン類似度に移行を検討。

---

## 未解決項目（P1/P2）

| 優先度 | 項目 | 状態 | 対策 |
|--------|------|------|------|
| P1 | Railway API `/api/agent/hooks` の実装有無確認 | 未確認 | 実装前にcurlで確認。なければAPI作成が先行タスク |
| P1 | reddapi 500 calls/月で足りるか | ギリギリ（推定540） | モニタリング + Reddit公式APIフォールバック |
| P2 | `executionCount` の永続化 | 未設計 | OpenClaw memory ツールで保存 or ファイルベース |
| P2 | hook候補の有効期限管理 | 未設計 | `createdAt` + 30日で自動期限切れ（Railway API側） |
| P2 | Slack `#trends` チャンネル存在確認 | 未確認 | 実装前にSlack APIで確認。なければ作成 |

---

## 受け入れ条件（Acceptance Criteria）

> テスト可能な形式。全条件を満たすまで「完了」としない。

| # | 条件 | 検証方法 | テストケース |
|---|------|---------|------------|
| AC-1 | 4時間ごとのCron実行で、対象ProblemTypeグループのトレンドを3ソース（X, TikTok, Reddit）から収集できる | Cron手動実行 → Slack #trends にサマリーが投稿される | `test_orchestrator_happy_path` |
| AC-2 | 収集したトレンドをLLMフィルタで関連度判定し、relevance_score >= 5 かつ virality != 'low' のみ通過する | モックトレンド10件投入 → 通過件数がフィルタ条件と一致 | `test_filter_relevance_and_virality` |
| AC-3 | フィルタ通過トレンドから共感系・問題解決系のhook候補を最大5件/回生成する | LLMモック出力 → HookCandidate型に適合 + 5件以下 | `test_hook_generation_max5` |
| AC-4 | 生成hookがJaccard類似度0.7未満の場合のみRailway APIに保存される | 既存hookと類似度0.9のhook投入 → 保存スキップ | `test_orchestrator_duplicate_skip` |
| AC-5 | 13 ProblemTypeが3グループにローテーションされ、2日（6実行）で全Type網羅される | executionCount 0-5 を順に実行 → 全13 Typeが1回以上検索される | `test_rotation_full_coverage` |
| AC-6 | いずれかのデータソースが障害時、残りのソースで処理が続行される | twitterApiClient → Error設定 → TikTok+Redditで正常完了 | `test_orchestrator_twitter_down` |
| AC-7 | Railway API保存失敗時、DLQに書き込まれ次回実行でリトライされる | railwayApiClient.saveHook → Error → DLQファイルに記録される | `test_orchestrator_railway_save_fail` |
| AC-8 | 実行結果サマリーがSlack #trends に投稿される（ソース別件数、保存件数、共感系/問題解決系の内訳） | Slackモック → formatされたメッセージが送信される | `test_format_normal` |
| AC-9 | LLM出力がJSON Schemaに不適合の場合、1回リトライ後にDLQに記録される | 不正JSON出力モック → リトライ1回 → DLQ記録 | `test_llm_schema_validation_retry` |
| AC-10 | 月間コストが$30以下に収まる（TwitterAPI ~$9 + reddapi $9.90 + LLM ~$3） | 1週間運用後のAPI使用量レポートで確認 | 手動検証 |

---

## 境界（やらないこと）

| # | やらないこと | 理由 |
|---|------------|------|
| B-1 | **投稿の自動実行** | trend-hunterはhook候補を生成・保存するだけ。投稿はx-posterの責務 |
| B-2 | **X API v2 の直接利用** | $200/月。TwitterAPI.io($9/月)で十分 |
| B-3 | **TikTok動画のダウンロード・分析** | ハッシュタグトレンドのメタデータのみ。動画コンテンツは対象外 |
| B-4 | **Reddit投稿へのコメント・投票** | 読み取り専用。reddapi.devのセマンティック検索のみ |
| B-5 | **ユーザー個人情報の保存** | 投稿者のusername/profileは保存しない。hookテキストとメトリクスのみ |
| B-6 | **リアルタイムストリーミング** | 4時間間隔のバッチ処理。WebSocket/Streaming APIは使わない |
| B-7 | **画像・動画の生成** | テキストhookのみ。画像付き投稿はx-posterのスコープ |
| B-8 | **Paywall/課金ロジックへの影響** | iOSアプリ側の変更なし。バックエンドのhookテーブルに書くだけ |
| B-9 | **既存Cronジョブの変更** | daily-metrics-reporter, Lab Meeting Reminderには一切触らない |
| B-10 | **OpenClaw本体の設定変更** | `openclaw.json` のbindings/agents/policiesは変更しない。Cronジョブ追加のみ |

### 触るファイル

| ファイル | 操作 |
|---------|------|
| `/usr/lib/node_modules/openclaw/skills/trend-hunter/SKILL.md` | 新規作成 |
| `/usr/lib/node_modules/openclaw/skills/trend-hunter/index.js` | 新規作成 |
| `/usr/lib/node_modules/openclaw/skills/trend-hunter/_meta.json` | 新規作成 |
| `/home/anicca/.openclaw/cron/jobs.json` | 既存ファイルにジョブ追加 |
| `/home/anicca/.env` | `TWITTERAPI_KEY`, `REDDAPI_API_KEY` 追記（ユーザー作業） |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `/home/anicca/.openclaw/openclaw.json` | エージェント設定は変更不要 |
| `aniccaios/` 配下全て | iOSアプリ変更なし |
| `apps/api/` 配下全て | Railway API変更は別タスク（P1で確認後） |
| 既存Cronジョブのprompt | daily-metrics, Lab Meeting は変更しない |

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 新ボタン/操作 | なし |
| iOSアプリ変更 | なし |
| 結論 | **Maestro E2Eシナリオ: 不要** |

**理由**: trend-hunterはOpenClaw VPS上のバックエンドスキル。iOSアプリのUIには一切影響しない。検証はユニットテスト + 統合テスト + VPS上でのCron手動実行で完結する。

---

## スキルファイル構成

> OpenClaw調査結果（2026-02-08）: スキルは **SKILL.md のみで動作可能**。
> エージェントがSKILL.mdの指示に従い、内蔵ツール（exec, slack, memory等）で実行する。
> `index.js` / `_meta.json` はカスタムツール実装時のみ必要（今回は不要）。

### ディレクトリ構造

```
/home/anicca/.openclaw/skills/trend-hunter/
└── SKILL.md          ← これだけ。エージェントがexec等で全てを実行する
```

**なぜ `~/.openclaw/skills/` か**: 全エージェント共有。ワークスペース専用より汎用性が高い。

### SKILL.md の構成（YAML Frontmatter + 本文）

```yaml
---
name: trend-hunter
description: 13 ProblemType のバイラルコンテンツをマルチソースから検出し、hook候補を生成する
homepage: https://github.com/Daisuke134/anicca.ai
metadata:
  openclaw:
    emoji: "🔍"
    requires:
      env:
        - TWITTERAPI_KEY
        - REDDAPI_API_KEY
        - APIFY_API_TOKEN
        - ANICCA_AGENT_TOKEN
    primaryEnv: TWITTERAPI_KEY
---

# trend-hunter

（本文: 実行指示、クエリ辞書、処理フロー、エラーハンドリング等）
（この設計書の「1. SKILL.md（改訂案）」〜「Step 4」の内容をここに記載）
```

### 環境変数の渡し方

| 方法 | 設定場所 | スコープ |
|------|---------|---------|
| **VPS `.env`** + systemd EnvironmentFile | `/home/anicca/.env` | プロセス全体（推奨） |
| `openclaw.json` の `skills.entries.trend-hunter.env` | `~/.openclaw/openclaw.json` | ホスト実行のみ |

**採用**: VPS `.env` 方式。既に `APIFY_API_TOKEN`, `ANICCA_AGENT_TOKEN` がこの方式で動作中。

### スキルの自動リロード

| 設定 | デフォルト値 | 意味 |
|------|------------|------|
| `skills.load.watch` | `true` | SKILL.md変更を監視して自動リロード |
| `skills.load.watchDebounceMs` | `250` | 変更検出後250msでリロード |

**Gateway再起動は不要**。SKILL.md を編集・コピーすれば250ms後に自動反映。

### デプロイ手順

| # | ステップ | コマンド | 備考 |
|---|---------|---------|------|
| 1 | ディレクトリ作成 | `ssh anicca@46.225.70.241 "mkdir -p ~/.openclaw/skills/trend-hunter"` | 初回のみ |
| 2 | SKILL.md アップロード | `scp SKILL.md anicca@46.225.70.241:~/.openclaw/skills/trend-hunter/` | 変更時も同じ |
| 3 | 環境変数追加 | ユーザーGUI作業（上記「ユーザー事前作業」参照） | `TWITTERAPI_KEY`, `REDDAPI_API_KEY` |
| 4 | 動作確認 | `ssh anicca@46.225.70.241 "openclaw doctor"` | Skills loaded セクションで確認 |
| 5 | Cronジョブ追加 | `jobs.json` に trend-hunter エントリ追加 | Gateway再起動が必要 |
| 6 | Cron手動テスト | `openclaw agent --message "trend-hunterスキルを実行してください" --deliver` | Slack #trends で結果確認 |

### テスト手順

| # | テスト種別 | 方法 | 確認項目 |
|---|-----------|------|---------|
| 1 | **ロード確認** | `openclaw doctor` | trend-hunter が Skills loaded に表示 |
| 2 | **依存確認** | `openclaw doctor` | TWITTERAPI_KEY 等の警告なし |
| 3 | **単体実行** | `openclaw agent --message "..."` | 各APIへのcurl成功、Slack投稿成功 |
| 4 | **Cronテスト** | ジョブ追加後、次の4時間サイクルを待つ or 手動実行 | 自動実行 + Slack通知 |
| 5 | **障害テスト** | 一時的にTWITTERAPI_KEYを無効化して実行 | フォールバック動作確認 |

---

## Thompson Sampling v2 — 検索頻度の動的調整

> リサーチ結果（2026-02-08）: Beta分布 + jStatライブラリ。
> 参考: Eugene Yan (eugeneyan.com/writing/bandits/), VWO, Towards Data Science

### 概要

v1（現在の設計）: 13 ProblemTypeを3グループに固定ローテーション。
v2（将来拡張）: 各ProblemTypeのhookパフォーマンスに基づき、検索頻度を動的に調整。

```
v1: [グループ0] → [グループ1] → [グループ2] → [グループ0] → ...（固定）
v2: [staying_up_late, anxiety, procrastination, self_loathing] → 次回はスコアの高い4つを優先
```

### アルゴリズム

| 項目 | 値 |
|------|-----|
| 分布 | Beta(α, β) |
| 初期値 | Beta(1, 1) = 一様分布（全ProblemType平等） |
| 成功定義 | 投稿hookがエンゲージメント閾値を超えた |
| 失敗定義 | 投稿hookが表示されたがエンゲージメントなし |
| α更新 | 成功時: `α += 1` |
| β更新 | 失敗時: `β += 1` |
| 選択 | 各ProblemTypeのBeta分布からサンプリング → 上位4-5個を選択 |
| 減衰 | 月次で `α *= 0.9`, `β *= 0.9`（季節変動対応） |

### 実装（exec内で実行するJavaScript）

```javascript
// jStat は npm でインストール不要 — 簡易Beta分布サンプリング
// Box-Muller法ベースの近似実装

function betaSample(alpha, beta) {
  // Jöhnk's algorithm for Beta distribution sampling
  let x, y;
  do {
    x = Math.pow(Math.random(), 1 / alpha);
    y = Math.pow(Math.random(), 1 / beta);
  } while (x + y > 1);
  return x / (x + y);
}

// 各ProblemTypeのBandit状態（OpenClaw memory に永続化）
const banditState = {
  staying_up_late:    { alpha: 1, beta: 1 },
  cant_wake_up:       { alpha: 1, beta: 1 },
  self_loathing:      { alpha: 1, beta: 1 },
  rumination:         { alpha: 1, beta: 1 },
  procrastination:    { alpha: 1, beta: 1 },
  anxiety:            { alpha: 1, beta: 1 },
  lying:              { alpha: 1, beta: 1 },
  bad_mouthing:       { alpha: 1, beta: 1 },
  porn_addiction:     { alpha: 1, beta: 1 },
  alcohol_dependency: { alpha: 1, beta: 1 },
  anger:              { alpha: 1, beta: 1 },
  obsessive:          { alpha: 1, beta: 1 },
  loneliness:         { alpha: 1, beta: 1 },
};

// 上位N個のProblemTypeを選択
function selectTopN(banditState, n = 4) {
  const samples = Object.entries(banditState).map(([type, { alpha, beta }]) => ({
    type,
    sample: betaSample(alpha, beta),
    mean: alpha / (alpha + beta),
  }));

  return samples
    .sort((a, b) => b.sample - a.sample)
    .slice(0, n)
    .map(s => s.type);
}

// フィードバック更新（x-posterの投稿結果を受けて）
function updateBandit(banditState, problemType, engaged) {
  if (engaged) {
    banditState[problemType].alpha += 1;
  } else {
    banditState[problemType].beta += 1;
  }
}

// 月次減衰（季節変動対応）
function decayAll(banditState, factor = 0.9) {
  for (const state of Object.values(banditState)) {
    state.alpha = Math.max(1, Math.round(state.alpha * factor));
    state.beta = Math.max(1, Math.round(state.beta * factor));
  }
}
```

### フェーズ移行

| フェーズ | 期間 | 選択方式 | 条件 |
|---------|------|---------|------|
| **Phase 1: ウォームスタート** | 初回50投稿（約8日） | v1固定ローテーション | データ不足（各Type最低3-4回試行が必要） |
| **Phase 2: TS開始** | 51投稿目〜 | Thompson Sampling で上位4-5個選択 | 全ProblemTypeが3回以上投稿済み |
| **Phase 3: 定期減衰** | 月次 | α・βに0.9倍減衰 | 古いデータの重み低減 |

### 永続化

| 方式 | 場所 | 読み書き |
|------|------|---------|
| **OpenClaw memory ツール** | `~/.openclaw/memory/trend-hunter-bandit.json` | `memory.read("trend-hunter-bandit")` / `memory.write(...)` |

**なぜ memory か**: OpenClawのmemoryツールはセッション横断で永続化される。ファイルベースでagent turnごとに自動保存。DBアクセス不要。

### v1 → v2 切り替え判定

```javascript
// executionCount はOpenClaw memory に保存
const state = memory.read('trend-hunter-state');
const executionCount = state?.executionCount || 0;
const WARMUP_THRESHOLD = 50; // 50投稿 = 約8日（6回/日）

if (executionCount < WARMUP_THRESHOLD) {
  // v1: 固定ローテーション
  const groupIndex = executionCount % 3;
  targetTypes = ROTATION_GROUPS[groupIndex];
} else {
  // v2: Thompson Sampling
  const bandit = memory.read('trend-hunter-bandit') || DEFAULT_BANDIT;
  targetTypes = selectTopN(bandit, 4);
}
```

### Thompson Sampling テストケース（追加分）

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 41 | `test_betaSample_returns_0_to_1` | `betaSample(1, 1)` × 1000回 | 全て 0.0〜1.0 の範囲内 | 分布範囲 |
| 42 | `test_betaSample_high_alpha_biased` | `betaSample(100, 1)` × 1000回 | 平均 > 0.9 | α偏り |
| 43 | `test_selectTopN_returns_n` | banditState(13個), n=4 | 長さ4の配列 | 選択数 |
| 44 | `test_selectTopN_favors_high_alpha` | staying_up_late: α=50,β=1、他: α=1,β=50 | staying_up_lateが100回中95回以上選択 | 優先選択 |
| 45 | `test_updateBandit_increments_alpha` | `updateBandit(state, 'anxiety', true)` | anxiety.alpha が +1 | 成功更新 |
| 46 | `test_updateBandit_increments_beta` | `updateBandit(state, 'anxiety', false)` | anxiety.beta が +1 | 失敗更新 |
| 47 | `test_decayAll_reduces` | α=10, β=5 に decayAll(0.9) | α=9, β=5（四捨五入） | 減衰 |
| 48 | `test_decayAll_minimum_1` | α=1, β=1 に decayAll(0.9) | α=1, β=1（最低値1を維持） | 最低値保護 |
| 49 | `test_v1_v2_switch` | executionCount=49 → v1、executionCount=50 → v2 | ローテーション → TS切り替え | フェーズ切替 |

---

## DLQリトライロジック

> リサーチ結果（2026-02-08）: Bull Queue + async-retry + AWS SQS のベストプラクティスを統合。
> ファイルベースDLQ（JSON Lines形式）で実装。DBアクセス不要。

### DLQ構造

**形式**: JSON Lines（`.jsonl`） — 1行 = 1エントリ。追記専用でロック不要。

**パス**: `~/.openclaw/dlq/trend-hunter-hooks.jsonl`

```typescript
interface DLQEntry {
  jobId: string;           // 一意識別子（`hook-${timestamp}-${random}`）
  data: {                  // リトライ時に再実行するペイロード
    hook: HookCandidate;   // 保存するhook候補
    endpoint: string;      // Railway API URL
  };
  attemptsMade: number;    // 現在の試行回数
  maxAttempts: number;     // 最大リトライ回数（5）
  timestamp: number;       // 初回失敗時刻（Unix ms）
  nextRetry: number;       // 次回リトライ時刻（Unix ms）
  error: {                 // 最後のエラー情報
    message: string;
    code: string | null;   // HTTP status or error code
  };
  state: 'pending' | 'retrying' | 'exhausted' | 'resolved';
}
```

### リトライ戦略

**採用: 指数バックオフ + ジッター**

| パラメータ | 値 | 理由 |
|-----------|-----|------|
| **factor** | 2 | 業界標準（AWS, Bull Queue共通） |
| **minTimeout** | 60,000 ms (1分) | Railway APIの一時障害を吸収 |
| **maxTimeout** | 3,600,000 ms (1時間) | 長時間障害でも上限あり |
| **maxAttempts** | 5 | 外部API呼び出しの推奨値 |
| **jitter** | ±30秒ランダム | Thundering Herd 回避 |

**待機時間の計算:**

| 試行 | 計算 | 待機時間 |
|------|------|---------|
| 1回目 | 60s × 2^0 + random(-30s, +30s) | 30秒〜1.5分 |
| 2回目 | 60s × 2^1 + random(-30s, +30s) | 1.5分〜2.5分 |
| 3回目 | 60s × 2^2 + random(-30s, +30s) | 3.5分〜4.5分 |
| 4回目 | 60s × 2^3 + random(-30s, +30s) | 7.5分〜8.5分 |
| 5回目 | 60s × 2^4 + random(-30s, +30s) | 15.5分〜16.5分 |
| **合計最大** | | **約33分** |

### 実装

```javascript
const DLQ_PATH = '/home/anicca/.openclaw/dlq/trend-hunter-hooks.jsonl';
const MAX_ATTEMPTS = 5;
const BASE_DELAY_MS = 60000; // 1分
const JITTER_MS = 30000;     // ±30秒

// DLQに書き込み
function writeToDLQ(hook, endpoint, error, attemptsMade = 0) {
  const entry = {
    jobId: `hook-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    data: { hook, endpoint },
    attemptsMade: attemptsMade + 1,
    maxAttempts: MAX_ATTEMPTS,
    timestamp: Date.now(),
    nextRetry: Date.now() + calcDelay(attemptsMade + 1),
    error: { message: error.message, code: error.code || null },
    state: attemptsMade + 1 >= MAX_ATTEMPTS ? 'exhausted' : 'pending',
  };

  // exec でファイル追記（OpenClawのexecツール経由）
  exec(`echo '${JSON.stringify(entry)}' >> ${DLQ_PATH}`);

  return entry;
}

// 指数バックオフ + ジッター
function calcDelay(attempt) {
  const base = BASE_DELAY_MS * Math.pow(2, attempt - 1);
  const jitter = (Math.random() * 2 - 1) * JITTER_MS; // ±30秒
  return Math.min(base + jitter, 3600000); // 上限1時間
}

// DLQ読み込み + リトライ対象抽出
function readRetryable() {
  const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
  if (!raw.trim()) return [];

  return raw.trim().split('\n')
    .map(line => JSON.parse(line))
    .filter(entry =>
      entry.state === 'pending' &&
      entry.attemptsMade < entry.maxAttempts &&
      Date.now() >= entry.nextRetry
    );
}

// リトライ実行（trend-hunterのStep 4冒頭で呼ぶ）
async function retryDLQ() {
  const retryable = readRetryable();
  let resolved = 0;

  for (const entry of retryable) {
    try {
      await exec(`curl -s -X POST \
        -H "Authorization: Bearer ${ANICCA_AGENT_TOKEN}" \
        -H "Content-Type: application/json" \
        "${entry.data.endpoint}" \
        -d '${JSON.stringify(entry.data.hook)}'`);

      // 成功 → resolved に更新
      updateDLQEntry(entry.jobId, 'resolved');
      resolved++;
    } catch (retryError) {
      // 再失敗 → attempt++、nextRetry更新
      writeToDLQ(
        entry.data.hook,
        entry.data.endpoint,
        retryError,
        entry.attemptsMade
      );
    }
  }

  return { total: retryable.length, resolved };
}
```

### DLQクリーンアップ

| ルール | 値 | タイミング |
|--------|-----|---------|
| resolved エントリ | 24時間後に削除 | 各実行の末尾 |
| exhausted エントリ | 7日後に削除 | 各実行の末尾 |
| pending エントリ | 削除しない（リトライ対象） | - |

```javascript
// クリーンアップ（7日以上前のexhausted + 24時間以上前のresolved）
function cleanupDLQ() {
  const raw = exec(`cat ${DLQ_PATH} 2>/dev/null || echo ""`);
  if (!raw.trim()) return;

  const entries = raw.trim().split('\n').map(line => JSON.parse(line));
  const now = Date.now();
  const DAY_MS = 86400000;

  const kept = entries.filter(entry => {
    if (entry.state === 'resolved' && now - entry.timestamp > DAY_MS) return false;
    if (entry.state === 'exhausted' && now - entry.timestamp > 7 * DAY_MS) return false;
    return true;
  });

  // 全体を書き直し（クリーンアップ時のみ）
  exec(`echo '${kept.map(e => JSON.stringify(e)).join('\n')}' > ${DLQ_PATH}`);
}
```

### べき等性（重複保存防止）

| 対策 | 実装 |
|------|------|
| **hookのjobIdを送信** | Railway API POSTリクエストに `idempotencyKey: jobId` を含める |
| **Railway API側で重複チェック** | 同じ `idempotencyKey` の2回目以降はスキップ |
| **DLQ側でresolved確認** | リトライ前に既にresolvedでないか確認 |

### DLQ テストケース（追加分）

| # | テスト名 | 入力 | 期待出力 | カバー |
|---|---------|------|---------|--------|
| 50 | `test_writeToDLQ_creates_entry` | hook + error | DLQファイルに1行追記、state='pending' | 書き込み |
| 51 | `test_writeToDLQ_exhausted_on_max` | attemptsMade=4 (5回目) | state='exhausted' | 上限到達 |
| 52 | `test_calcDelay_exponential` | attempt=1,2,3 | 60s, 120s, 240s（±jitter） | 指数バックオフ |
| 53 | `test_calcDelay_max_cap` | attempt=20 | <= 3,600,000ms（1時間） | 上限キャップ |
| 54 | `test_readRetryable_filters` | pending×2 + exhausted×1 + resolved×1 | 長さ2（pendingのみ） | フィルタ |
| 55 | `test_readRetryable_respects_nextRetry` | nextRetry=未来 | 空配列（まだ早い） | 時刻判定 |
| 56 | `test_retryDLQ_success` | Railway APIモック成功 | resolved=1 | リトライ成功 |
| 57 | `test_retryDLQ_fail_again` | Railway APIモック再失敗 | 新DLQエントリ（attempt+1） | リトライ再失敗 |
| 58 | `test_cleanupDLQ_removes_old` | 8日前のexhausted | 削除される | クリーンアップ |
| 59 | `test_cleanupDLQ_keeps_pending` | 8日前のpending | 保持される | pending保護 |

---

## Spec完了チェックリスト

| # | セクション | 状態 | テスト数 |
|---|-----------|------|---------|
| 1 | 概要（What & Why） | ✅ | - |
| 2 | 受け入れ条件 | ✅ | AC-1〜AC-10 |
| 3 | As-Is / To-Be | ✅ | - |
| 4 | テストマトリックス | ✅ | 59テスト |
| 5 | 境界（やらないこと） | ✅ | B-1〜B-10 |
| 6 | 実行手順 | ✅ | デプロイ6ステップ + テスト5種 |
| 7 | E2E判定 | ✅ | 不要（バックエンドのみ） |
| 8 | ファイル構成 | ✅ | SKILL.mdのみ |
| 9 | DLQリトライロジック | ✅ | 10テスト (#50-59) |
| 10 | Thompson Sampling v2 | ✅ | 9テスト (#41-49) |
| 11 | モックAPIレスポンス | ✅ | 5ソース分 |
| 12 | LLM出力バリデーション | ✅ | JSON Schema 2種 |
| 13 | 重複判定アルゴリズム | ✅ | Jaccard bi-gram |
| **合計テスト数** | | | **59** |
