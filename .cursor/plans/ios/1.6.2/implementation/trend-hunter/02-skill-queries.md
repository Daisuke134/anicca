
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

## 状態管理（executionCount）

### 永続化方式: OpenClaw memory ツール

| 項目 | 値 |
|------|-----|
| **方式** | OpenClaw memory ツール（セッション横断で永続化） |
| **パス** | `~/.openclaw/memory/trend-hunter-state.json` |
| **読み書き** | `memory.read('trend-hunter-state')` / `memory.write('trend-hunter-state', data)` |
| **フォールバック** | ファイル不存在 or 破損時 → `{ executionCount: 0 }` で初期化 |

```typescript
// 状態管理インターフェース
interface TrendHunterState {
  executionCount: number;       // 累計実行回数（ローテーション + TS切替に使用）
  lastExecutedAt: string;       // ISO 8601 タイムスタンプ
  lastGroup: number;            // 最後に実行したグループインデックス (0|1|2)
}

// 読み込み（実行開始時）
const state: TrendHunterState = memory.read('trend-hunter-state') ?? {
  executionCount: 0,
  lastExecutedAt: new Date(0).toISOString(),
  lastGroup: -1,
};

// 書き込み（実行完了時）
memory.write('trend-hunter-state', {
  ...state,
  executionCount: state.executionCount + 1,
  lastExecutedAt: new Date().toISOString(),
  lastGroup: groupIndex,
});
```

**なぜ memory か（他の選択肢との比較）:**

| 方式 | ACID | セッション横断 | 追加依存 | 判定 |
|------|------|-------------|---------|------|
| **OpenClaw memory** | ファイルベース（非ACID） | ✅ | なし | **採用** |
| Railway DB | ✅ | ✅ | APIコール必要 | 不採用（オーバーヘッド） |
| ローカルファイル（fs） | ❌ | ✅ | なし | 不採用（memory と同等だがAPI不統一） |

---

## QUERY_DICT 型定義

```typescript
// 各ProblemTypeの検索クエリ構造
interface QueryEntry {
  empathy_ja: string;   // 日本語 共感系（当事者の叫び）
  empathy_en: string;   // 英語 共感系
  solution_ja: string;  // 日本語 問題解決系（対処法バズ）
  solution_en: string;  // 英語 問題解決系
}

// 13 ProblemType → クエリマッピング
type QueryDict = Record<ProblemType, QueryEntry>;

// ProblemType enum（iOSアプリと同一）
type ProblemType =
  | 'staying_up_late' | 'cant_wake_up' | 'self_loathing' | 'rumination'
  | 'procrastination' | 'anxiety' | 'lying' | 'bad_mouthing'
  | 'porn_addiction' | 'alcohol_dependency' | 'anger' | 'obsessive'
  | 'loneliness';
```

---

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

