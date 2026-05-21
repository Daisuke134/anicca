# Phase 9-10: Aniccaの汎用化（Generalization）

> **バージョン**: 1.5.0 / 1.6.0 / 1.7.0
>
> **最終更新**: 2026-01-26
>
> **目的**: Aniccaが「人間の行動変容」を汎用的に理解し、毎日賢くなる

---

## 目次

1. [概要](#1-概要)
2. [As-Is（1.4.0完了後）](#2-as-is140完了後)
3. [汎用化の進化](#3-汎用化の進化)
4. [To-Be（1.5.0）](#4-to-be150)
5. [To-Be（1.6.0）](#5-to-be160)
6. [To-Be（1.7.0）](#6-to-be170)
7. [DBスキーマ](#7-dbスキーマ)
8. [タスクリスト](#8-タスクリスト)
9. [並列実装計画（Worktree）](#9-並列実装計画worktree)
10. [TikTok Bridge詳細](#10-tiktok-bridge詳細)
11. [シミュレーション詳細](#11-シミュレーション詳細)
12. [テストマトリックス](#12-テストマトリックス)
13. [境界（やらないこと）](#13-境界やらないこと)
14. [レビューチェックリスト](#14-レビューチェックリスト)
15. [Skills/Sub-agents使用マップ](#15-skillssub-agents使用マップ)
16. [iOS側変更](#16-ios側変更)
17. [実行手順](#17-実行手順)

---

## 1. 概要

### 1.1 Aniccaの進化の方向性

**方向B（抽象化）を選択**

| 方向 | 説明 | 採用 |
|------|------|------|
| A: リアルタイム | 1秒1秒モニタリング、データで反応 | ❌ |
| B: 抽象化 | 人間の心理を理解、普遍的wisdomを獲得 | ✅ |

**Buddhaの例え**:
> Buddhaは一人一人をリアルタイムでモニタリングしていない。
> 人間の心理を根本的に理解しているから、誰にでも効く説法ができた。

### 1.2 計画ホライズン = 成熟度

| 成熟度 | 計画ホライズン | 状態 |
|--------|---------------|------|
| 初心者 | 1日をデザイン | 1.4.0（完了） |
| 中級者 | 1週間をデザイン | 将来 |
| 上級者 | 1ヶ月をデザイン | 将来 |
| マスター | 1年をデザイン | 将来 |
| Buddha | 一生をデザイン | 究極目標 |

### 1.3 バージョン別目標

| バージョン | 内容 | 目的 |
|-----------|------|------|
| **1.5.0** | クロスユーザー学習 + TikTok投稿 | 汎用化の土台 |
| **1.6.0** | シミュレーション | 汎用化の加速 |
| **1.7.0** | Contextual Bandit（オプション） | 統計的補強 |

---

## 2. As-Is（1.4.0完了後）

### 2.1 実装済み機能

| 項目 | 状態 | 詳細 |
|------|------|------|
| 計画 | ✅ | LLMが1日をデザイン |
| 判断 | ✅ | ストーリー（過去7日）を見て判断 |
| 察する | ✅ | 根本原因を推測（rootCauseHypothesis） |
| 学習 | ✅ | reasoning保存、次回に渡す |
| フィードバック | ✅ | Hook/Content分離（tap率 vs 👍率） |
| タイミング | ✅ | LLMがscheduledTimeを決定 |

### 2.2 未実装（1.5.0以降）

| 項目 | 状態 | 詳細 |
|------|------|------|
| 汎用化 | ❌ | まだユーザー単位の学習のみ |
| クロスユーザー学習 | ❌ | タイプ別パターンなし |
| TikTok連携 | ❌ | アプリ内のみ |
| シミュレーション | ❌ | 実データのみで学習 |

### 2.3 コード状態

| ファイル | 状態 |
|---------|------|
| `apps/api/src/jobs/generateNudges.js` | ユーザー別フィードバック取得、パーソナライズプロンプト |
| `apps/api/src/routes/mobile/nudge.js` | フィードバックAPI |
| `apps/api/prisma/schema.prisma` | NudgeEvent, NudgeOutcome（**1:1関係、UNIQUE制約あり**）, UserTrait 定義済み |
| `scripts/sns-poster/` | Blotato + Fal.ai 連携済み |

---

## 3. 汎用化の進化

### 3.1 レベル定義

| Level | 説明 | 例 | バージョン |
|-------|------|-----|-----------|
| **1** | ユーザー単位 | 「Aさんにはstrictが効く」 | 1.4.0（完了） |
| **2** | タイプ単位 | 「完璧主義の人にはstrictが効く」 | 1.5.0 |
| **3** | 普遍的wisdom | 「自己批判的な人には、批判を認めてから方向転換が効く」 | 1.6.0+ |

### 3.2 汎用化のメカニズム

```
Level 1（1.4.0）:
ユーザーA → 介入 → 結果 → Aのパターン学習

Level 2（1.5.0）:
ユーザーA,B,C（同タイプ）→ 介入 → 結果 → タイプのパターン学習
新規ユーザーD（同タイプ）→ 既存パターン適用 → cold start解消

Level 3（1.6.0）:
シミュレーション（1000ペルソナ）→ 介入 → 結果 → 普遍パターン抽出
実データで検証 → 両方で効く = wisdom
```

---

## 4. To-Be（1.5.0）

### 4.1 目標

**クロスユーザー学習 + TikTok投稿**

| 目標 | 詳細 |
|------|------|
| タイプ別学習 | 「完璧主義タイプにはstrictが効く」を学習 |
| cold start解消 | 新規ユーザーに最初から効くNudgeを出す |
| TikTok投稿 | アプリ外でも学習チャネルを持つ |
| 汎用パターン抽出 | アプリ+TikTokで効くもの = wisdom |

### 4.2 クロスユーザー学習

#### 4.2.1 ユーザータイプ分類

| タイプID | タイプ名 | 特徴 |
|---------|---------|------|
| T1 | 完璧主義 | できない自分を許せない |
| T2 | 比較傾向 | 他人と比べて落ち込む |
| T3 | 衝動型 | 衝動を抑えられない |
| T4 | 不安型 | 将来を心配しすぎる |

#### 4.2.2 タイプ分類アルゴリズム（確定）

**スコアベース分類を採用**

```javascript
// 重みマトリックス（ProblemType × UserType）
const WEIGHT_MATRIX = {
  self_loathing:     { T1: 3, T2: 2, T3: 0, T4: 1 },
  procrastination:   { T1: 3, T2: 0, T3: 1, T4: 1 },
  rumination:        { T1: 1, T2: 3, T3: 0, T4: 3 },
  staying_up_late:   { T1: 0, T2: 0, T3: 3, T4: 1 },
  porn_addiction:    { T1: 0, T2: 0, T3: 3, T4: 0 },
  anxiety:           { T1: 1, T2: 1, T3: 0, T4: 3 },
  cant_wake_up:      { T1: 1, T2: 0, T3: 2, T4: 1 },
  lying:             { T1: 0, T2: 1, T3: 2, T4: 1 },
  bad_mouthing:      { T1: 0, T2: 2, T3: 2, T4: 0 },
  alcohol_dependency:{ T1: 0, T2: 1, T3: 3, T4: 1 },
  anger:             { T1: 1, T2: 1, T3: 3, T4: 0 },
  obsessive:         { T1: 2, T2: 0, T3: 0, T4: 2 },
  loneliness:        { T1: 0, T2: 2, T3: 0, T4: 2 }
};

function classifyUserType(selectedProblems) {
  // Empty problems → default T4 with confidence 0
  if (!selectedProblems || selectedProblems.length === 0) {
    return { primaryType: 'T4', scores: { T1: 0, T2: 0, T3: 0, T4: 0 }, confidence: 0 };
  }

  const scores = { T1: 0, T2: 0, T3: 0, T4: 0 };

  for (const problem of selectedProblems) {
    const weights = WEIGHT_MATRIX[problem] || {};
    for (const type of Object.keys(scores)) {
      scores[type] += weights[type] || 0;
    }
  }

  const totalScore = Object.values(scores).reduce((a, b) => a + b, 0);
  const primaryType = Object.entries(scores)
    .sort((a, b) => b[1] - a[1])[0][0];
  const confidence = totalScore > 0 ? scores[primaryType] / totalScore : 0;

  return { primaryType, scores, confidence };
}
```

**重みマトリックスの根拠**:
- 3: 強い関連（このProblemTypeを選ぶ人は高確率でこのタイプ）
- 2: 中程度の関連
- 1: 弱い関連
- 0: 関連なし

**1.6.0以降の改善**: データが溜まったらK-meansクラスタリングでタイプを再定義

#### 4.2.3 タイプ別パターン

| タイプ | 効くトーン | 効くHookパターン | 効くContent長さ |
|--------|-----------|-----------------|----------------|
| T1（完璧主義） | strict | 短い命令形 | 短い（40字以下） |
| T2（比較傾向） | gentle | 共感形 | 中程度 |
| T3（衝動型） | provocative | 挑発形 | 短い |
| T4（不安型） | logical | 論理形 | 長い（説明付き） |

#### 4.2.4 「効く」の閾値（確定）

| チャネル | 指標 | 閾値 | 必要サンプル数 |
|---------|------|------|---------------|
| アプリ | tap率 | > 50% | n >= 10 |
| アプリ | thumbsUp率 | > 60% | n >= 10 |
| TikTok | share率 | > 5% | n >= 5 |
| TikTok | like/view比 | > 10% | n >= 5 |
| wisdom判定 | アプリ+TikTok両方で効く | 上記全て満たす | - |

#### 4.2.5 プロンプト変更

```markdown
## 📊 Cross-User Patterns (What works for similar users)

This user is estimated to be Type: **完璧主義 (T1)** (confidence: 75%)

### What works for T1 users:
- Tone: strict (tap率 78%, 👍率 82%)
- Hook: 短い命令形 (tap率 80%)
- Content: 40字以下 (👍率 85%)

### What doesn't work for T1 users:
- Tone: gentle (tap率 35%) ❌
- Hook: 長い説明形 (tap率 25%) ❌
```

#### 4.2.6 nudge_events.state スキーマ拡張

**generateNudgesで保存するstate構造**（計測用フィールド追加）:
```json
{
  "hook": "...",
  "content": "...",
  "tone": "strict",
  "hook_candidate_id": "uuid-of-hook-candidate",  // NEW: 計測用
  "user_type": "T1",                              // NEW: 計測用
  "scheduledTime": "2026-02-01T09:00:00Z"
}
```

**保存トリガー**: generateNudges.js でNudgeを生成するタイミング

#### 4.2.7 user_type_estimates 更新経路

| トリガー | 処理 | 備考 |
|---------|------|------|
| オンボーディング完了時 | 選択したProblemsから分類→UPSERT | 新規ユーザー |
| プロフィール更新時 | Problems変更があれば再分類→UPDATE | 既存ユーザー |
| バックフィルジョブ（1回） | 既存ユーザー全員を分類→INSERT | リリース時に実行 |

**実装場所**: `apps/api/src/services/userTypeService.js`

### 4.3 TikTok投稿

#### 4.3.1 位置づけ

**Aniccaの学習チャネルの1つ（独立ではない）**

```
Anicca（1つの知性）
├── アプリ内: Nudge → tap/👍👎 で学習
└── TikTok: 投稿 → view/like/share で学習
     ↓
両方の学習が hook_candidates に統合
     ↓
Aniccaがどんどん賢くなる
```

#### 4.3.2 アーキテクチャ（Aniccaエージェント）

**Aniccaは「ツールを持ったAIエージェント」としてTikTokに投稿する。**

パイプライン（スクリプトが順番に実行される）ではなく、**LLMがツールを使って自律的に判断・生成・評価・投稿する**エージェントループ。

```
GitHub Actions cron (00:00 UTC = 09:00 JST)
    │
    ▼
anicca_tiktok_agent.py を起動（= Aniccaが目を覚ます）
    │
    └── Aniccaが自分でツールを使って思考・生成・評価・投稿
        └── OpenAI Function Calling エージェントループ
            └── finish_reason == "stop" まで繰り返し

═══════════════════════════════════════════════

fetch_metrics.py（別cron、投稿24時間後）
    │
    └── Apify TikTok Scraperでメトリクス自動取得（機械的ジョブ）
```

| 部分 | Aniccaの判断（エージェント） | 機械的（cron） |
|------|---------------------------|---------------|
| 何を投稿するか | ✅ Aniccaが考える | |
| 画像生成・評価・やり直し | ✅ Aniccaが判断 | |
| 投稿する/しない | ✅ Aniccaが判断（品質低ければ投稿しない選択も可） | |
| メトリクス取得 | | ✅ 機械的（Apifyで数字を取るだけ） |
| hook_candidates更新 | | ✅ 機械的（取得した数字をDBに書くだけ） |

#### 4.3.3 ツール定義

Aniccaエージェントが使用するツール一覧：

| ツール名 | 内部実装 | 入力 | 出力 | 用途 |
|---------|---------|------|------|------|
| `get_yesterday_performance` | DB読み取り（API経由） | なし | 昨日の投稿メトリクス（view/like/share/comment） | 振り返り |
| `get_hook_candidates` | DB読み取り（API経由） | フィルタ条件（任意） | hook_candidatesの成績データ（アプリ+TikTok） | 分析 |
| `search_trends` | Exa API | 検索クエリ（string） | トレンド記事・パターン | トレンド調査 |
| `generate_image` | Fal.ai FLUX Schnell | プロンプト（string） | 画像URL | コンテンツ生成 |
| `evaluate_image` | OpenAI Vision API | 画像URL | 品質評価（OK/NG + 理由） | 自己評価 |
| `post_to_tiktok` | Blotato API (Account ID: 28152) | 画像URL + キャプション | 投稿結果（post_id） | 投稿実行 |
| `save_post_record` | DB書き込み（API経由） | 投稿データ | 保存結果 | 記録 |

**ツール実装**: 既存の `blotato.py`、`fal_ai.py` をツール関数としてラップ。

**DB接続方式**: GitHub ActionsからSupabase DBへの直接接続ではなく、**API経由**（`apps/api/` のエンドポイントを叩く）。セキュリティリスク軽減のため。

#### 4.3.4 エージェントフロー

```
Aniccaが目を覚ます（GitHub Actions cron起動）

Aniccaの思考ループ:
│
├── 1. get_yesterday_performance() → 昨日の成績を確認
│      「like率7%か。Hookが弱かった」
│
├── 2. get_hook_candidates() → 何が効いているか分析
│      「strictトーンの命令形がtap率72%で最高」
│
├── 3. search_trends() → 今日のトレンドを調べる
│      「"I tried quitting..." 形式がバズってる」
│
├── 4. LLMの思考 → 今日の投稿内容を決定
│      Hook: "6年間、毎晩『今日こそ早く寝る』って言ってた"
│      キャプション: "..."
│
├── 5. generate_image() → Fal.aiで画像生成
│
├── 6. evaluate_image() → 画像を自己評価
│      「テキストが読みにくい。作り直し」
│      → generate_image() を再度呼ぶ（最大3回）
│
├── 7. evaluate_image() → OK
│      「これなら良い」
│
├── 8. post_to_tiktok() → Blotato経由で投稿
│
└── 9. save_post_record() → tiktok_postsに記録

finish_reason: "stop"（Aniccaが完了と判断）
```

**安全制限**:
- ツール呼び出し上限: 20回/セッション（無限ループ防止）
- 画像生成リトライ上限: 3回
- エラー時: ログ記録 → Slack/Discord webhook通知 → 投稿スキップ（翌日リトライ）

#### 4.3.5 投稿スケジュール（確定）

| 項目 | 設定 |
|------|------|
| 頻度 | 1日1投稿（毎日） |
| 時間 | 09:00 JST（GitHub Actions cron: 00:00 UTC） |
| 形式 | Phase 1: 画像1枚のみ（スライド・動画は後） |
| 言語 | 英語中心 |
| アカウント | @anicca.self（Blotato Account ID: 28152）のみ |

#### 4.3.6 メトリクス取得（自動）

**Apify TikTok Scraperで全メトリクスを自動取得。手動入力なし。**

| 項目 | 内容 |
|------|------|
| **Actor** | `clockworks/tiktok-scraper`（Apify公式、119Kユーザー） |
| **実行タイミング** | 投稿24時間後（GitHub Actions cron） |
| **取得指標** | playCount(view), diggCount(like), shareCount, commentCount |
| **保存先** | `tiktok_posts` テーブル → `hook_candidates` テーブル更新 |

```
fetch_metrics.py（機械的ジョブ、エージェント不要）
│
├── 1. Apify API呼び出し（@anicca.self の動画一覧取得）
├── 2. metrics_fetched_at が NULL の投稿を照合
├── 3. tiktok_posts のメトリクス更新
├── 4. hook_candidates の tiktok_* カラム更新（加重平均）
└── 5. tiktok_high_performer フラグ再計算
```

**メトリクス整合性ルール**: 全指標（view/like/comment/share）は常にセットで保存。部分的な指標取得・保存は不可。

#### 4.3.7 指標マッピング

| TikTok指標 | Anicca指標 | 計算式 | 用途 |
|-----------|-----------|--------|------|
| diggCount / playCount | Hook効果 | like率 > 10% = 効く | Hookの「掴み」評価 |
| shareCount / playCount | Content「刺さり」 | share率 > 5% = 刺さる | 保存の代替指標 |
| commentCount（質的分析） | 安全性 | ネガティブ < 10% | ガードレール |

#### 4.3.8 学習フェーズ

| Phase | 期間 | データソース | Aniccaの判断材料 |
|-------|------|-------------|-----------------|
| 1（コールドスタート） | Day 1-14 | hook_candidatesのアプリ内データ + Exaトレンド | past_performance = なし |
| 2（混合） | Day 15-30 | 自分のTikTokデータ + アプリ内データ + トレンド | トップ成績パターン強化、ワースト回避 |
| 3（自己最適化） | Day 31+ | 自分のデータが主 | 完全フィードバックループ |

#### 4.3.9 制限・禁止事項

| 制限（Phase 1） | 理由 |
|----------------|------|
| 画像1枚のみ（動画・スライドは後） | 制限 = 革新。テキスト+画像で学びを最大化 |
| TikTok EN 1アカウントのみ（@anicca.self） | 1つのチャネルで学習ループを確立してから拡張 |

| 禁止 | 理由 |
|------|------|
| ビュー最大化に寄せる | 煽りに走る危険 |
| 罪悪感を煽る表現 | 「苦しみを減らす」の反対 |
| 「簡単に習慣化！」「たったN日で！」系のHook | ペルソナが警戒する嘘Hook |
| 自動スクロール/自動いいね | 規約違反リスク |

### 4.4 Hook候補ライブラリ

#### 4.4.1 初期データ作成手順（確定）

```sql
-- 1.4.0のnudge_eventsからHook抽出クエリ
-- ※ hook_candidates.tone は NOT NULL のため、tone未保存/不正値はデフォルト'logical'で補完
-- ※ GROUP BY は式をそのまま書く（PostgreSQLではエイリアス不可）
-- ※ subtypeはCHECK制約許可リストに限定（NULL/未知値は除外）
-- ⚠️ tone正規化: CHECK制約(5種)に合わせて不正値は'logical'にフォールバック
SELECT
  ne.state->>'hook' as hook,
  -- tone正規化: 許可リスト外はデフォルト'logical'にフォールバック
  CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
       THEN ne.state->>'tone'
       ELSE 'logical'
  END as tone,
  ne.subtype as problem_type,
  COUNT(*) as sample_size,
  SUM(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1 ELSE 0 END) as tapped_count,
  SUM(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'true' THEN 1 ELSE 0 END) as thumbs_up_count
FROM nudge_events ne
LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
WHERE ne.domain = 'problem_nudge'
  AND ne.created_at >= NOW() - INTERVAL '60 days'
  AND ne.state->>'hook' IS NOT NULL
  AND ne.subtype IS NOT NULL
  AND ne.subtype IN ('self_loathing','procrastination','rumination','staying_up_late','porn_addiction','anxiety','cant_wake_up','lying','bad_mouthing','alcohol_dependency','anger','obsessive','loneliness')
GROUP BY ne.state->>'hook',
         CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
              THEN ne.state->>'tone'
              ELSE 'logical'
         END,
         ne.subtype
HAVING COUNT(*) >= 5;
```

**hook_candidates への INSERT 仕様**:

```sql
-- 初期投入は 1行 = hook + tone（problem_types は配列で集約）
-- ※ tap_rate/thumbs_up_rate は加重平均（sample_size/tapped_countで重み付け）
-- ※ subtypeはCHECK制約許可リストに限定（NULL/未知値は除外）
-- ※ 再実行時は ON CONFLICT で UPSERT（重複防止）
-- ⚠️ tone正規化: CHECK制約(5種)に合わせて不正値は'logical'にフォールバック
INSERT INTO hook_candidates (text, tone, target_problem_types, app_tap_rate, app_thumbs_up_rate, app_sample_size)
SELECT
  hook as text,
  tone,
  ARRAY_AGG(DISTINCT problem_type) as target_problem_types,
  -- 加重平均: tap_rate = Σtapped_count / Σsample_size（除算失敗時は0）
  COALESCE(SUM(tapped_count)::NUMERIC / NULLIF(SUM(sample_size), 0), 0) as app_tap_rate,
  -- 加重平均: thumbs_up_rate = Σthumbs_up_count / Σtapped_count（除算失敗時は0）
  COALESCE(SUM(thumbs_up_count)::NUMERIC / NULLIF(SUM(tapped_count), 0), 0) as app_thumbs_up_rate,
  SUM(sample_size) as app_sample_size
FROM (
  SELECT
    ne.state->>'hook' as hook,
    -- tone正規化: 許可リスト外はデフォルト'logical'にフォールバック
    CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
         THEN ne.state->>'tone'
         ELSE 'logical'
    END as tone,
    ne.subtype as problem_type,
    COUNT(*) as sample_size,
    SUM(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1 ELSE 0 END) as tapped_count,
    SUM(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'true' THEN 1 ELSE 0 END) as thumbs_up_count
  FROM nudge_events ne
  LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
  WHERE ne.domain = 'problem_nudge'
    AND ne.created_at >= NOW() - INTERVAL '60 days'
    AND ne.state->>'hook' IS NOT NULL
    AND ne.subtype IS NOT NULL
    AND ne.subtype IN ('self_loathing','procrastination','rumination','staying_up_late','porn_addiction','anxiety','cant_wake_up','lying','bad_mouthing','alcohol_dependency','anger','obsessive','loneliness')
  GROUP BY ne.state->>'hook',
           CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
                THEN ne.state->>'tone'
                ELSE 'logical'
           END,
           ne.subtype
  HAVING COUNT(*) >= 5
) sub
GROUP BY hook, tone
ON CONFLICT (text, tone) DO UPDATE SET
  target_problem_types = EXCLUDED.target_problem_types,
  app_tap_rate = EXCLUDED.app_tap_rate,
  app_thumbs_up_rate = EXCLUDED.app_thumbs_up_rate,
  app_sample_size = EXCLUDED.app_sample_size,
  updated_at = NOW();
```

**投入方針**:
- 1行 = hook + tone の組み合わせ（ProblemType は `target_problem_types` 配列に集約）
- `app_tap_rate`: 加重平均（Σtapped_count / Σsample_size）
- `app_thumbs_up_rate`: 加重平均（Σthumbs_up_count / Σtapped_count）
- `app_sample_size`: 全 ProblemType のサンプル数合計

**注意**: 過去イベント（1.4.0以前）でtoneが未保存の場合、デフォルト値 `'logical'` を適用。

**データモデル前提（全集計クエリ共通）**:
- `nudge_events` と `nudge_outcomes` は **1:1** の関係
- `nudge_outcomes.nudge_event_id` は UNIQUE 制約あり（既存スキーマで定義済み）
- 1つのNudgeイベントに対して、最大1つのOutcome（tap/ignore + thumbsUp/thumbsDown）が記録される
- この前提により、LEFT JOIN での COUNT(*) や AVG 計算が正確に動作する

**signals スキーマ（正規形式）**:
```json
{
  "outcome": "tapped",           // タップ時のみ "tapped"、無視時は null または未設定
  "thumbsUp": "true" | "false"   // 👍="true", 👎="false", 未回答=null
}
```
- **重要**: `thumbsUp` は Boolean ではなく文字列 `"true"` / `"false"` で保存（既存実装）
- `thumbsDown` キーは使用しない（`thumbsUp: "false"` で👎を表現）
- 全 SQL クエリはこの形式を前提とする

#### 4.4.2 Hook候補データモデル

```typescript
interface HookCandidate {
  id: string;
  text: string;
  tone: 'strict' | 'gentle' | 'logical' | 'provocative' | 'philosophical';
  targetProblemTypes: string[];
  targetUserTypes: string[];
  appPerformance: {
    tapRate: number;           // tapped_count / sample_size
    thumbsUpRate: number;      // thumbs_up_count / tapped_count（タップした人のうち👍した割合）
    sampleSize: number;        // 総イベント数（tapped + ignored）
    lastUpdated: Date;         // → DB: updated_at（チャネル別なし、全体の最終更新）
  };
  tiktokPerformance: {
    likeRate: number;          // like_count / view_count
    shareRate: number;         // share_count / view_count
    sampleSize: number;        // 投稿数
    lastUpdated: Date;         // → DB: updated_at（チャネル別なし、全体の最終更新）
  };
  isWisdom: boolean;           // 両方で効く = true
  explorationWeight: number;   // 探索優先度（新規は高い）
  createdAt: Date;
  updatedAt: Date;
}
```

**DB⇔Interface マッピング注記**:
- `lastUpdated`は両チャネルで共通の`updated_at`を使用（チャネル別更新時刻は持たない）
- `sampleSize`の定義: アプリ = 総Nudgeイベント数（tapped+ignored）、TikTok = 投稿数

**エージェント連携**: Aniccaエージェント（`anicca_tiktok_agent.py`）が `get_hook_candidates` ツールでこのテーブルを読み、投稿内容の判断に使用する。高成績のHookを活用枠（80%）、新規Hookを探索枠（20%）でThompson Samplingにより選択。

### 4.5 学習ループ

```
┌─────────────────────────────────────────────────────────────┐
│                        Anicca                              │
│                                                             │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │   アプリ    │         │   TikTok    │                   │
│  │  Nudge送信  │         │  投稿配信   │                   │
│  └──────┬──────┘         └──────┬──────┘                   │
│         │                       │                          │
│         ▼                       ▼                          │
│  ┌─────────────┐         ┌─────────────┐                   │
│  │ tap/👍👎   │         │ like/share  │                   │
│  └──────┬──────┘         └──────┬──────┘                   │
│         │                       │                          │
│         └───────────┬───────────┘                          │
│                     │                                      │
│                     ▼                                      │
│           ┌─────────────────┐                              │
│           │   統合学習      │                              │
│           │  タイプ別集計   │                              │
│           └────────┬────────┘                              │
│                    │                                       │
│                    ▼                                       │
│           ┌─────────────────┐                              │
│           │  汎用パターン   │                              │
│           │  （wisdom）     │                              │
│           └─────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.6 受け入れ条件

| # | 条件 | 測定方法 |
|---|------|---------|
| 1 | 新規ユーザーのcold startが解消 | 下記詳細参照 |
| 2 | タイプ別パターンが蓄積 | 最低3タイプ × 3パターン |
| 3 | TikTok投稿が稼働 | 週5投稿以上（下記詳細参照） |
| 4 | TikTokの学びがアプリに反映 | TikTok高成績Hookがアプリで使用される |

#### 4.6.1 cold start改善の測定詳細（統計条件）

| 項目 | 条件 |
|------|------|
| **比較対象** | 同週の既存ユーザー（30日以上利用）のtap率 |
| **新規ユーザー定義** | 測定期間中にアプリインストールしたユーザー（※`profiles.created_at` = 初回サインアップ日時 ≒ インストール日） |
| **測定期間** | リリース後14日間 |
| **サンプルサイズ** | 各群最低30ユーザー |
| **成功基準** | 新規ユーザーtap率 ≥ 既存ユーザーtap率 × 0.9（非劣性マージンΔ=10%） |
| **ProblemType** | 同一ProblemType内で比較（異なるProblemType間では比較しない） |
| **統計的検証** | 新規群tap率 - 既存群tap率 の95%信頼区間下限 ≥ -Δ で非劣性確認 |

**非劣性検定の解釈**:
- 帰無仮説 H0: 新規群tap率 < 既存群tap率 - Δ（新規が劣る）
- 対立仮説 H1: 新規群tap率 ≥ 既存群tap率 - Δ（新規が非劣性）
- 判定: 差の95%CI下限が -Δ（-10%）以上なら非劣性を確認

**計測クエリ例**:
```sql
-- 新規 vs 既存のtap率比較（同一ProblemType）
-- 測定期間: リリース後14日間のイベントのみ対象
-- 新規ユーザー: 測定期間中にインストール（created_at >= リリース日）
-- 既存ユーザー: リリース日の30日以上前からの利用者
-- ※ tap率の定義: signals->>'outcome' = 'tapped'（全Specで統一）
WITH release_date AS (
  SELECT '2026-02-01'::date as dt  -- リリース日を設定
),
new_users AS (
  SELECT id as user_id FROM profiles, release_date  -- profiles.idがuser_id
  WHERE created_at >= release_date.dt
    AND created_at < release_date.dt + INTERVAL '14 days'
),
existing_users AS (
  SELECT id as user_id FROM profiles, release_date  -- profiles.idがuser_id
  WHERE created_at < release_date.dt - INTERVAL '30 days'
),
-- ユーザー単位でtap率を計算（イベント単位ではない）
-- LEFT JOIN を使用: ignored（outcome未記録）も分母に含める
-- domain = 'problem_nudge' に限定してProblemType単位の比較を担保
user_tap_rates AS (
  SELECT
    ne.user_id,
    ne.subtype,
    CASE WHEN ne.user_id IN (SELECT user_id FROM new_users) THEN 'new' ELSE 'existing' END as cohort,
    AVG(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1.0 ELSE 0.0 END) as user_tap_rate
  FROM nudge_events ne
  LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
  CROSS JOIN release_date
  WHERE (ne.user_id IN (SELECT user_id FROM new_users) OR ne.user_id IN (SELECT user_id FROM existing_users))
    AND ne.domain = 'problem_nudge'
    AND ne.subtype IS NOT NULL
    AND ne.created_at >= release_date.dt
    AND ne.created_at < release_date.dt + INTERVAL '14 days'
  GROUP BY ne.user_id, ne.subtype, CASE WHEN ne.user_id IN (SELECT user_id FROM new_users) THEN 'new' ELSE 'existing' END
)
SELECT
  cohort,
  subtype,
  AVG(user_tap_rate) as tap_rate,
  COUNT(DISTINCT user_id) as user_count  -- ユニークユーザー数
FROM user_tap_rates
GROUP BY cohort, subtype  -- user_tap_rates CTEで既に cohort 列として実体化済み
HAVING COUNT(DISTINCT user_id) >= 30;  -- 各群最低30ユーザー条件
```

**Bootstrap用クエリ（ユーザーごとのtap率リスト取得）**:
```sql
-- scripts/coldStartAnalysis.js で使用
-- Bootstrap CI計算用に、ユーザーごとのtap率リストを返す
WITH release_date AS (
  SELECT '2026-02-01'::date as dt
),
new_users AS (
  SELECT id as user_id FROM profiles, release_date
  WHERE created_at >= release_date.dt
    AND created_at < release_date.dt + INTERVAL '14 days'
),
existing_users AS (
  SELECT id as user_id FROM profiles, release_date
  WHERE created_at < release_date.dt - INTERVAL '30 days'
)
SELECT
  CASE WHEN ne.user_id IN (SELECT user_id FROM new_users) THEN 'new' ELSE 'existing' END as cohort,
  ne.subtype,
  ne.user_id,
  AVG(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1.0 ELSE 0.0 END) as user_tap_rate
FROM nudge_events ne
LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
CROSS JOIN release_date
WHERE (ne.user_id IN (SELECT user_id FROM new_users) OR ne.user_id IN (SELECT user_id FROM existing_users))
  AND ne.domain = 'problem_nudge'
  AND ne.subtype IS NOT NULL
  AND ne.created_at >= release_date.dt
  AND ne.created_at < release_date.dt + INTERVAL '14 days'
GROUP BY CASE WHEN ne.user_id IN (SELECT user_id FROM new_users) THEN 'new' ELSE 'existing' END, ne.subtype, ne.user_id;

-- 結果例:
-- cohort   | subtype        | user_id | user_tap_rate
-- new      | staying_up_late| uuid-1  | 0.67
-- new      | staying_up_late| uuid-2  | 0.50
-- existing | staying_up_late| uuid-3  | 0.75
-- ...
```

**Bootstrap実行手順**:
1. 上記クエリで cohort × subtype ごとのユーザー tap率リストを取得
2. subtype ごとに new/existing のリストを分離
3. `bootstrapCI(newRates, existingRates)` で差の95%CIを算出
4. CI下限 ≥ -10% なら非劣性確認

**95%信頼区間の算出方法（Bootstrap）**:
```javascript
// scripts/coldStartAnalysis.js
const BOOTSTRAP_ITERATIONS = 1000;
const ALPHA = 0.05; // 95% CI

function bootstrapCI(newRates, existingRates) {
  const differences = [];

  for (let i = 0; i < BOOTSTRAP_ITERATIONS; i++) {
    // リサンプリング（復元抽出）
    const newSample = resampleWithReplacement(newRates);
    const existingSample = resampleWithReplacement(existingRates);

    // 差の計算
    const diff = mean(newSample) - mean(existingSample);
    differences.push(diff);
  }

  // 差の分布をソートしてパーセンタイル算出
  differences.sort((a, b) => a - b);
  const lowerIdx = Math.floor(ALPHA / 2 * BOOTSTRAP_ITERATIONS);
  const upperIdx = Math.floor((1 - ALPHA / 2) * BOOTSTRAP_ITERATIONS);

  return {
    lowerBound: differences[lowerIdx],  // 2.5パーセンタイル
    upperBound: differences[upperIdx],  // 97.5パーセンタイル
    isNonInferior: differences[lowerIdx] >= -0.10  // Δ=10%
  };
}
```

**実行手順**:
1. 上記SQLクエリでcohort別のユーザーtap率リストを取得
2. Bootstrap法で差の95%CIを算出
3. CI下限 ≥ -10% なら非劣性確認

#### 4.6.2 タイプ別パターン蓄積の測定詳細

| 項目 | 条件 |
|------|------|
| **「パターン」の定義** | タイプ × tone の組み合わせで、閾値を超える成績を記録したもの |
| **属性の種類** | tone（5種: strict/gentle/logical/provocative/philosophical） |
| **成功閾値** | tap率 > 50% かつ サンプルサイズ >= 10 |
| **測定方法** | type_statsテーブル（PK: type_id, tone）の有効レコード数をカウント |

**注記**: hook形式・content長は1.5.0スコープ外。1.6.0以降でhook_candidatesと連携して拡張予定。

**計測クエリ**:
```sql
-- 有効パターン数のカウント（3タイプ × 3パターン = 9以上で達成）
SELECT
  type_id,
  COUNT(*) as pattern_count
FROM type_stats
WHERE tap_rate > 0.50
  AND sample_size >= 10
GROUP BY type_id
HAVING COUNT(*) >= 3;  -- 各タイプで3tone以上

-- 達成判定: 上記クエリで3行以上（3タイプ以上）返れば条件達成
```

**type_stats 集計クエリ（aggregateTypeStats.js で使用）**:
```sql
-- 日次でtype_statsを更新するクエリ
-- tapped_count/ignored_countの計算方法を明示
-- ※ event時点の user_type を使用（state->>'user_type' に記録されたイベントのみ集計）
-- 旧イベント（state に user_type 未保存）は集計対象外
-- ⚠️ user_type/toneはCHECK制約許可リストに限定（不正値はジョブ失敗を防ぐため除外）
WITH event_counts AS (
  SELECT
    ne.state->>'user_type' as type_id,  -- event時点のタイプ（必須）
    -- tone正規化: 許可リスト外はデフォルト'logical'にフォールバック
    CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
         THEN ne.state->>'tone'
         ELSE 'logical'
    END as tone,
    COUNT(*) as total_events,
    COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' THEN 1 END) as tapped,
    COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'true' THEN 1 END) as thumbs_up,
    COUNT(CASE WHEN no.signals->>'outcome' = 'tapped' AND no.signals->>'thumbsUp' = 'false' THEN 1 END) as thumbs_down
  FROM nudge_events ne
  LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
  WHERE ne.domain = 'problem_nudge'
    AND ne.created_at >= NOW() - INTERVAL '60 days'
    AND ne.state->>'user_type' IS NOT NULL  -- user_type記録済みイベントのみ
    AND ne.state->>'user_type' IN ('T1', 'T2', 'T3', 'T4')  -- CHECK制約許可リストと一致
  GROUP BY ne.state->>'user_type',
           CASE WHEN ne.state->>'tone' IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')
                THEN ne.state->>'tone'
                ELSE 'logical'
           END
)
INSERT INTO type_stats (type_id, tone, tapped_count, ignored_count, thumbs_up_count, thumbs_down_count, sample_size, updated_at)
SELECT
  type_id,
  tone,
  tapped as tapped_count,
  total_events - tapped as ignored_count,  -- ignored = 総イベント - tapped
  thumbs_up as thumbs_up_count,
  thumbs_down as thumbs_down_count,
  total_events as sample_size,
  NOW() as updated_at
FROM event_counts
ON CONFLICT (type_id, tone) DO UPDATE SET
  tapped_count = EXCLUDED.tapped_count,
  ignored_count = EXCLUDED.ignored_count,
  thumbs_up_count = EXCLUDED.thumbs_up_count,
  thumbs_down_count = EXCLUDED.thumbs_down_count,
  sample_size = EXCLUDED.sample_size,
  updated_at = NOW();
```

**データソース**: `type_stats`テーブル
```
type_id | tone       | tap_rate | sample_size
--------|------------|----------|-------------
T1      | strict     | 0.78     | 45          ✓
T1      | logical    | 0.55     | 32          ✓
T1      | gentle     | 0.35     | 28          ✗（閾値未満）
T2      | gentle     | 0.62     | 51          ✓
...
```

#### 4.6.3 TikTok高成績Hook使用の測定詳細

| 項目 | 条件 |
|------|------|
| **「高成績」の定義** | like率 > 10% AND share率 > 5% AND サンプルサイズ >= 5（4.2.4の閾値準拠） |
| **「使用される」の定義** | 生成されたNudgeのhook_candidateがtiktok_high_performerフラグ=true |
| **測定方法** | 直近7日間の生成Nudgeのうち、高成績Hook由来の割合 |
| **成功閾値** | 高成績Hook由来のNudgeが全体の10%以上 |

**計測クエリ**:
```sql
-- TikTok高成績Hookの使用状況
WITH recent_nudges AS (
  SELECT
    ne.id,
    ne.state->>'hook_candidate_id' as hook_candidate_id
  FROM nudge_events ne
  WHERE ne.created_at >= NOW() - INTERVAL '7 days'
    AND ne.domain = 'problem_nudge'
),
high_performer_hooks AS (
  SELECT id
  FROM hook_candidates
  WHERE tiktok_like_rate > 0.10
    AND tiktok_share_rate > 0.05
    AND tiktok_sample_size >= 5
)
SELECT
  COUNT(*) as total_nudges,
  COUNT(CASE WHEN rn.hook_candidate_id IN (SELECT id::text FROM high_performer_hooks) THEN 1 END) as high_performer_nudges,
  ROUND(
    COUNT(CASE WHEN rn.hook_candidate_id IN (SELECT id::text FROM high_performer_hooks) THEN 1 END)::numeric
    / NULLIF(COUNT(*), 0) * 100, 2
  ) as high_performer_percentage
FROM recent_nudges rn;

-- 達成判定: high_performer_percentage >= 10.00
```

**hook_candidatesテーブルのフラグ更新ロジック**:
```javascript
// fetchTiktokMetrics.jsで実行
const isHighPerformer = likeRate > 0.10 && shareRate > 0.05 && sampleSize >= 5;
await prisma.hookCandidate.update({
  where: { id: hookId },
  data: { tiktok_high_performer: isHighPerformer }
});
```

#### 4.6.4 TikTok投稿稼働の測定詳細

| 項目 | 条件 |
|------|------|
| **「週5投稿以上」の定義** | 直近7日間でtiktok_postsに5件以上のレコードがある |
| **測定期間** | 常時（リリース後1週間経過から測定開始） |
| **測定頻度** | 週1回（月曜日に前週分を確認） |

**計測クエリ**:
```sql
-- 直近7日間の投稿数確認
SELECT
  COUNT(*) as post_count,
  CASE WHEN COUNT(*) >= 5 THEN '達成' ELSE '未達成' END as status
FROM tiktok_posts
WHERE posted_at >= NOW() - INTERVAL '7 days';
```

---

## 5. To-Be（1.6.0）

### 5.1 目標

**シミュレーションで汎用化を加速**

| 目標 | 詳細 |
|------|------|
| ペルソナ生成 | 実データから「完璧主義×夜更かし」等を抽出 |
| 高速テスト | 1000パターンの介入をシミュ内でテスト |
| パターン発見 | 実データを待たずに汎用パターンを発見 |
| 検証ループ | シミュ→実データ検証→wisdom確定 |

### 5.2 シミュレーションの役割

| 役割 | OK | NG |
|------|----|----|
| 汎用パターン発見 | ✅ | |
| 候補生成/多様化 | ✅ | |
| 危険表現の除外 | ✅ | |
| **本番の最終意思決定** | | ❌ |

### 5.3 シミュ開始タイミング（確定）

**1.5.0リリース後2-4週間で開始**

| 条件 | 理由 |
|------|------|
| タイプ別統計が安定 | シミュの精度がタイプ定義に依存 |
| 最低100ユーザーのフィードバック | ペルソナの代表性確保 |
| Hook候補ライブラリが50件以上 | シミュでテストする候補が必要 |

### 5.4 受け入れ条件

| # | 条件 | 測定方法 |
|---|------|---------|
| 1 | ペルソナ生成が稼働 | 最低10ペルソナ生成 |
| 2 | シミュ精度が閾値以上 | Offline replay評価で70%以上の再現性 |
| 3 | シミュ発見パターンが実データで検証 | 最低3パターンが実データでも効く |

---

## 6. To-Be（1.7.0）

### 6.1 目標

**Contextual Banditで統計的補強（オプション）**

| 目標 | 詳細 |
|------|------|
| 統計的最適化 | LLMの判断を統計的に補強 |
| 非定常対応 | 忘却（直近N日重視）で変化に追随 |

### 6.2 位置づけ

**必須ではない。Aniccaが自分で学習できれば不要かもしれない。**

| コンポーネント | 役割 |
|---------------|------|
| Anicca（LLM） | 脳・判断・reasoning |
| Contextual Bandit | 記憶の統計処理（補助ツール） |

### 6.3 実装判断

1.6.0完了後に判断:
- Aniccaの学習が十分 → Bandit不要
- Aniccaの学習が不十分 → Bandit追加

---

## 7. DBスキーマ

### 7.0 前提条件

**pgcrypto拡張が必要**（`gen_random_uuid()` 関数を使用）:
```sql
-- マイグレーション実行前に確認/有効化
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

※ Supabaseでは既にデフォルトで有効化済み。新規環境構築時は要確認。

### 7.0.1 マイグレーション実施手順

**Prismaの制約**: Prismaは以下をネイティブサポートしない:
- CHECK制約
- GENERATED ALWAYS AS（計算列）
- Partial Index / GIN Index

**運用方針**: SQL DDLを正とし、Prismaマイグレーションを手動拡張する。

```bash
# Step 1: Prismaマイグレーションを生成（適用しない）
cd apps/api && npx prisma migrate dev --create-only --name 1_5_0_cross_user_learning

# Step 2: 生成されたSQLファイルを編集
# 場所: prisma/migrations/<timestamp>_1_5_0_cross_user_learning/migration.sql
# 以下を手動追記:
#   - 全CHECK制約（本Spec Section 7.1のSQL定義を参照）
#   - type_stats の GENERATED ALWAYS AS カラム（tap_rate, thumbs_up_rate）
#   - Partial Index（hook_candidates.is_wisdom）
#   - GIN Index（hook_candidates.target_user_types, wisdom_patterns.target_user_types）
#   - 降順インデックス（tiktok_posts.posted_at DESC）

# Step 3: マイグレーションを適用
npx prisma migrate dev

# Step 4: 制約が正しく作成されたことを確認
npx prisma db execute --stdin <<< "SELECT conname FROM pg_constraint WHERE conname LIKE 'chk_%';"
```

**追記必須項目一覧**:

| テーブル | 追記項目 | 種別 |
|---------|----------|------|
| user_type_estimates | `REFERENCES profiles(id) ON DELETE CASCADE` FK、`CHECK (primary_type IN (...))`, `CHECK (confidence >= 0 AND confidence <= 1)` | FK, CHECK |
| type_stats | `CHECK (type_id IN (...))`, `CHECK (tone IN (...))`, `chk_sample_size_consistency`, `chk_thumbs_*` | CHECK |
| type_stats | `tap_rate GENERATED ALWAYS AS`, `thumbs_up_rate GENERATED ALWAYS AS` | 計算列 |
| hook_candidates | 全CHECK制約、`chk_hook_candidates_user_types`、`chk_hook_candidates_problem_types`、`UNIQUE(text, tone)`、`WHERE is_wisdom = true` Partial Index、`USING GIN(target_user_types)` | CHECK, Index, UNIQUE |
| tiktok_posts | `chk_metrics_consistency` | CHECK |
| wisdom_patterns | `CHECK (confidence ...)`、`chk_wisdom_patterns_user_types`、`USING GIN(target_user_types)` | CHECK, Index |

**注意**: Prismaモデルには計算列（tap_rate, thumbs_up_rate）を定義しない。読み取りは`prisma.$queryRaw`で直接SQLを実行する。

### 7.1 新規テーブル（1.5.0）

#### user_type_estimates

```sql
CREATE TABLE user_type_estimates (
  user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  primary_type VARCHAR(10) NOT NULL
    CHECK (primary_type IN ('T1', 'T2', 'T3', 'T4')),  -- 有効なタイプのみ
  type_scores JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),  -- 0..1制約
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_type_estimates_primary ON user_type_estimates(primary_type);
```

#### type_stats

```sql
CREATE TABLE type_stats (
  type_id VARCHAR(10) NOT NULL
    CHECK (type_id IN ('T1', 'T2', 'T3', 'T4')),  -- 有効なタイプのみ
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),  -- 5種のトーン
  tapped_count INT NOT NULL DEFAULT 0 CHECK (tapped_count >= 0),
  ignored_count INT NOT NULL DEFAULT 0 CHECK (ignored_count >= 0),
  thumbs_up_count INT NOT NULL DEFAULT 0 CHECK (thumbs_up_count >= 0),
  thumbs_down_count INT NOT NULL DEFAULT 0 CHECK (thumbs_down_count >= 0),
  sample_size INT NOT NULL DEFAULT 0 CHECK (sample_size >= 0),  -- 総Nudgeイベント数 = tapped_count + ignored_count
  tap_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN sample_size > 0 THEN tapped_count::NUMERIC / sample_size ELSE 0 END
  ) STORED,  -- 自動計算のため0..1制約は不要（式で保証）
  thumbs_up_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN tapped_count > 0 THEN thumbs_up_count::NUMERIC / tapped_count ELSE 0 END
  ) STORED,  -- 自動計算のため0..1制約は不要（式で保証）
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (type_id, tone),
  -- 集計整合性制約
  CONSTRAINT chk_sample_size_consistency CHECK (sample_size = tapped_count + ignored_count),
  CONSTRAINT chk_thumbs_up_le_tapped CHECK (thumbs_up_count <= tapped_count),
  CONSTRAINT chk_thumbs_down_le_tapped CHECK (thumbs_down_count <= tapped_count),
  CONSTRAINT chk_thumbs_total_le_tapped CHECK (thumbs_up_count + thumbs_down_count <= tapped_count)
);
-- 集計ルール: sample_size = tapped_count + ignored_count（イベント単位）
-- aggregateTypeStats.js で日次集計時に更新
--
-- ※ 集計対象: nudge_events.state->>'user_type' が保存されているイベントのみ
--   旧イベント（user_type未記録）は集計対象外
--
-- データソース定義（nudge_events LEFT JOIN nudge_outcomes で集計）:
--   tapped_count: nudge_outcomes.signals->>'outcome' = 'tapped' のイベント数
--   ignored_count: nudge_outcomes が NULL または outcome が 'tapped' 以外のイベント数
--   計算式: ignored_count = (全nudge_events数) - tapped_count
--   thumbs_up_count: tapped かつ nudge_outcomes.signals->>'thumbsUp' = 'true' のイベント数
--   thumbs_up_rate: thumbs_up_count / tapped_count（タップした人のうち👍した割合）
```

#### hook_candidates

```sql
CREATE TABLE hook_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  text TEXT NOT NULL,
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),  -- 5種のトーン
  UNIQUE (text, tone),  -- 同一Hook+Toneの重複防止
  target_problem_types TEXT[] NOT NULL DEFAULT '{}',
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  -- 配列要素の妥当性制約（許可リストのみ、NULLは型レベルで防止）
  -- ※ PostgreSQL TEXT[] は NOT NULL 制約で要素レベルのNULL禁止不可だが、
  --    アプリケーション層（API入力バリデーション）でNULL要素を拒否する
  -- ※ 空配列は許容（"全ProblemType/全UserType対象"を意味する。初期投入後に集計で更新される）
  CONSTRAINT chk_hook_candidates_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  CONSTRAINT chk_hook_candidates_problem_types CHECK (
    target_problem_types <@ ARRAY['self_loathing','procrastination','rumination','staying_up_late','porn_addiction','anxiety','cant_wake_up','lying','bad_mouthing','alcohol_dependency','anger','obsessive','loneliness']::text[]
  ),
  app_tap_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_tap_rate >= 0 AND app_tap_rate <= 1),
  app_thumbs_up_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_thumbs_up_rate >= 0 AND app_thumbs_up_rate <= 1),
  app_sample_size INT NOT NULL DEFAULT 0 CHECK (app_sample_size >= 0),
  tiktok_like_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_like_rate >= 0 AND tiktok_like_rate <= 1),
  tiktok_share_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_share_rate >= 0 AND tiktok_share_rate <= 1),
  tiktok_sample_size INT NOT NULL DEFAULT 0 CHECK (tiktok_sample_size >= 0),
  tiktok_high_performer BOOLEAN NOT NULL DEFAULT FALSE,  -- like率>10% AND share率>5%
  is_wisdom BOOLEAN NOT NULL DEFAULT FALSE,
  exploration_weight NUMERIC(3,2) NOT NULL DEFAULT 1.0 CHECK (exploration_weight >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hook_candidates_wisdom ON hook_candidates(is_wisdom) WHERE is_wisdom = TRUE;
CREATE INDEX idx_hook_candidates_high_performer ON hook_candidates(tiktok_high_performer) WHERE tiktok_high_performer = TRUE;
CREATE INDEX idx_hook_candidates_target_types ON hook_candidates USING GIN(target_user_types);
```

#### tiktok_posts

```sql
CREATE TABLE tiktok_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- hook_candidate_id は NULL 許容（理由: テスト投稿や分類未確定の投稿を許可）
  -- ただし retention_rate_manual 更新時は hook_candidate_id 必須（集計更新のため）
  hook_candidate_id UUID REFERENCES hook_candidates(id),
  tiktok_video_id VARCHAR(100) UNIQUE,  -- 重複投稿防止
  blotato_post_id VARCHAR(100),
  caption TEXT,
  posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metrics_fetched_at TIMESTAMPTZ,
  view_count BIGINT CHECK (view_count IS NULL OR view_count >= 0),  -- BIGINTで将来の大規模カウント対応
  like_count BIGINT CHECK (like_count IS NULL OR like_count >= 0),
  comment_count BIGINT CHECK (comment_count IS NULL OR comment_count >= 0),
  share_count BIGINT CHECK (share_count IS NULL OR share_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- メトリクス整合性制約: 未取得時は全てNULL、取得後は全て非NULL
  CONSTRAINT chk_metrics_consistency CHECK (
    (metrics_fetched_at IS NULL AND view_count IS NULL AND like_count IS NULL AND comment_count IS NULL AND share_count IS NULL)
    OR (
      metrics_fetched_at IS NOT NULL AND view_count IS NOT NULL AND like_count IS NOT NULL AND comment_count IS NOT NULL AND share_count IS NOT NULL
    )
  )
);

CREATE INDEX idx_tiktok_posts_hook ON tiktok_posts(hook_candidate_id);
CREATE INDEX idx_tiktok_posts_posted_at ON tiktok_posts(posted_at DESC);
```

#### wisdom_patterns

```sql
CREATE TABLE wisdom_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name VARCHAR(100) NOT NULL,
  description TEXT,
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  -- 配列要素の妥当性制約（許可リストのみ、NULLは型レベルで防止）
  -- ※ PostgreSQL TEXT[] は NOT NULL 制約で要素レベルのNULL禁止不可だが、
  --    アプリケーション層（API入力バリデーション）でNULL要素を拒否する
  -- ※ 空配列は許容（"全UserType対象"を意味する）
  CONSTRAINT chk_wisdom_patterns_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  effective_tone VARCHAR(20)
    CHECK (effective_tone IS NULL OR effective_tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),
  effective_hook_pattern TEXT,
  effective_content_length VARCHAR(20)
    CHECK (effective_content_length IS NULL OR effective_content_length IN ('short', 'medium', 'long')),
  app_evidence JSONB NOT NULL DEFAULT '{}',
  tiktok_evidence JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),  -- 0..1制約
  verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wisdom_patterns_types ON wisdom_patterns USING GIN(target_user_types);
```

### 7.2 Prisma schema追加

```prisma
model UserTypeEstimate {
  userId      String   @id @db.Uuid @map("user_id")
  primaryType String   @db.VarChar(10) @map("primary_type")
  typeScores  Json     @db.JsonB @default("{}") @map("type_scores")
  confidence  Decimal  @db.Decimal(5,4) @default(0)
  createdAt   DateTime @default(now()) @db.Timestamptz @map("created_at")
  updatedAt   DateTime @default(now()) @db.Timestamptz @map("updated_at")

  // FK: profiles(id) - 手動DDLで追加済み
  profile     Profile  @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([primaryType])  // idx_user_type_estimates_primary
  @@map("user_type_estimates")
}

model TypeStats {
  typeId         String   @db.VarChar(10) @map("type_id")
  tone           String   @db.VarChar(20)
  tappedCount    Int      @default(0) @map("tapped_count")
  ignoredCount   Int      @default(0) @map("ignored_count")
  thumbsUpCount  Int      @default(0) @map("thumbs_up_count")
  thumbsDownCount Int     @default(0) @map("thumbs_down_count")
  sampleSize     Int      @default(0) @map("sample_size")
  updatedAt      DateTime @default(now()) @db.Timestamptz @map("updated_at")
  // NOTE: tap_rate, thumbs_up_rate はSQLの GENERATED ALWAYS AS カラム
  // Prismaでは @ignore 相当で定義せず、クエリ時に直接SQL参照する
  // 読み取りは prisma.$queryRaw で実行

  @@id([typeId, tone])
  @@map("type_stats")
}

// === Generated Columns 整合性方針 ===
// type_stats.tap_rate と thumbs_up_rate は PostgreSQL の GENERATED ALWAYS AS で定義
// Prisma はこれらを直接サポートしないため、以下の方針を採用:
// 1. Prismaモデルには計算カラムを定義しない
// 2. 読み取りは prisma.$queryRaw で直接SQLを実行
// 3. 書き込みは通常のPrisma updateで（計算カラム以外）
// 参照: https://github.com/prisma/prisma/issues/6368

model HookCandidate {
  id                 String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  text               String    @db.Text
  tone               String    @db.VarChar(20)
  targetProblemTypes String[]  @default([]) @map("target_problem_types")
  targetUserTypes    String[]  @default([]) @map("target_user_types")
  appTapRate         Decimal   @db.Decimal(5,4) @default(0) @map("app_tap_rate")
  appThumbsUpRate    Decimal   @db.Decimal(5,4) @default(0) @map("app_thumbs_up_rate")
  appSampleSize      Int       @default(0) @map("app_sample_size")
  tiktokLikeRate     Decimal   @db.Decimal(5,4) @default(0) @map("tiktok_like_rate")
  tiktokShareRate    Decimal   @db.Decimal(5,4) @default(0) @map("tiktok_share_rate")
  tiktokSampleSize   Int       @default(0) @map("tiktok_sample_size")
  tiktokHighPerformer Boolean  @default(false) @map("tiktok_high_performer")
  isWisdom           Boolean   @default(false) @map("is_wisdom")
  explorationWeight  Decimal   @db.Decimal(3,2) @default(1.0) @map("exploration_weight")
  createdAt          DateTime  @default(now()) @db.Timestamptz @map("created_at")
  updatedAt          DateTime  @default(now()) @db.Timestamptz @map("updated_at")

  tiktokPosts TiktokPost[]

  @@unique([text, tone])  // 同一Hook+Toneの重複防止
  @@index([tone])  // Prisma対応インデックス
  // NOTE: GIN Index (target_user_types), Partial Index (is_wisdom) は手動SQLで追加
  @@map("hook_candidates")
}

model TiktokPost {
  id                String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  // hookCandidateId は NULL 許容（テスト投稿や分類未確定の投稿を許可）
  hookCandidateId   String?   @db.Uuid @map("hook_candidate_id")
  tiktokVideoId     String?   @db.VarChar(100) @unique @map("tiktok_video_id")  // 重複投稿防止
  blotatoPostId     String?   @db.VarChar(100) @map("blotato_post_id")
  caption           String?   @db.Text
  postedAt          DateTime  @default(now()) @db.Timestamptz @map("posted_at")
  metricsFetchedAt  DateTime? @db.Timestamptz @map("metrics_fetched_at")
  viewCount         BigInt?   @map("view_count")  // BIGINTで将来の大規模カウント対応
  likeCount         BigInt?   @map("like_count")
  commentCount      BigInt?   @map("comment_count")
  shareCount        BigInt?   @map("share_count")
  createdAt         DateTime  @default(now()) @db.Timestamptz @map("created_at")

  hookCandidate HookCandidate? @relation(fields: [hookCandidateId], references: [id])

  @@index([hookCandidateId])
  @@index([postedAt(sort: Desc)])  // 最新投稿検索用
  @@map("tiktok_posts")
}

model WisdomPattern {
  id                   String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  patternName          String    @db.VarChar(100) @map("pattern_name")
  description          String?   @db.Text
  targetUserTypes      String[]  @default([]) @map("target_user_types")
  effectiveTone        String?   @db.VarChar(20) @map("effective_tone")
  effectiveHookPattern String?   @db.Text @map("effective_hook_pattern")
  effectiveContentLength String? @db.VarChar(20) @map("effective_content_length")
  appEvidence          Json      @db.JsonB @default("{}") @map("app_evidence")
  tiktokEvidence       Json      @db.JsonB @default("{}") @map("tiktok_evidence")
  confidence           Decimal   @db.Decimal(5,4) @default(0)
  verifiedAt           DateTime? @db.Timestamptz @map("verified_at")
  createdAt            DateTime  @default(now()) @db.Timestamptz @map("created_at")
  updatedAt            DateTime  @default(now()) @db.Timestamptz @map("updated_at")

  // NOTE: GIN Index (target_user_types) は手動SQLで追加
  @@map("wisdom_patterns")
}
```

### 7.5 APIコントラクト

#### 共通バリデーション要件

**配列フィールドのNULL要素禁止**（DB CHECK制約の補完）:

PostgreSQL CHECK制約では配列要素のNULL検知が困難なため、以下のフィールドは**API層で入力バリデーション**を行う:

| テーブル | フィールド | バリデーション |
|---------|-----------|---------------|
| hook_candidates | target_user_types | `arr.every(x => x !== null && ['T1','T2','T3','T4'].includes(x))` |
| hook_candidates | target_problem_types | `arr.every(x => x !== null && PROBLEM_TYPES.includes(x))` |
| wisdom_patterns | target_user_types | `arr.every(x => x !== null && ['T1','T2','T3','T4'].includes(x))` |

**実装箇所**: 各Admin API のリクエストボディバリデーション（Zod/Joi等）

---

#### GET /api/mobile/user-type

**概要**: ユーザーのタイプ推定結果を取得

| 項目 | 内容 |
|------|------|
| **認証** | Bearer Token（Authorization header） |
| **レート制限** | 100 req/min/user |

**レスポンス（200 OK）**:
```json
{
  "success": true,
  "data": {
    "primaryType": "T1",
    "typeName": "完璧主義",
    "confidence": 0.75,
    "scores": {
      "T1": 8,
      "T2": 3,
      "T3": 1,
      "T4": 2
    },
    "lastUpdated": "2026-01-26T10:00:00Z"
  }
}
```

**エラーレスポンス**:
| コード | 条件 | レスポンス |
|--------|------|-----------|
| 401 | 認証なし/無効 | `{"success": false, "error": "Unauthorized"}` |
| 404 | プロフィール不存在 | `{"success": false, "error": "Profile not found"}` |
| 500 | 内部エラー | `{"success": false, "error": "Internal server error"}` |

**ログ方針**:
- 404: `warn`レベル、user_id含む（デバッグ用、通常発生しない）
- 500: `error`レベル、スタックトレース含む、アラート対象

**欠損時の挙動（エッジケース処理）**:

| ケース | Profile | user_type_estimates | Problems | 処理 | lastUpdated |
|--------|---------|---------------------|----------|------|-------------|
| 0. 不存在 | NULL | - | - | **404返却** | - |
| 1. 正常 | 存在 | 存在 | 任意 | DBから返却 | saved `updated_at` |
| 2. 未計算 | 存在 | 欠損 | 非空 | 即時計算→UPSERT→返却 | NOW() |
| 3. 空問題 | 存在 | 任意 | 空配列 | T4/0を返却（保存しない） | NOW() |

**ケース2の詳細（user_type_estimatesが存在しないがProblemsが非空）**:
- バックフィル未実行、オンボーディング後の初回アクセス等で発生
- Problems から `classifyUserType()` を即時計算
- confidence > 0 の場合のみ user_type_estimates に UPSERT
- `lastUpdated` は計算時刻（NOW()）を返却

```javascript
// 実装ロジック（userTypeService.js）

// タイプ名マッピング（API仕様用）
const TYPE_NAMES = {
  T1: '完璧主義',
  T2: '比較傾向',
  T3: '衝動型',
  T4: '不安型'
};

// DBフォーマット → API仕様フォーマット変換
function formatApiResponse(data, updatedAt) {
  return {
    primaryType: data.primaryType,
    typeName: TYPE_NAMES[data.primaryType],
    confidence: data.confidence,
    scores: data.typeScores || data.scores,  // DB: typeScores, 計算結果: scores
    lastUpdated: updatedAt
  };
}

async function getUserType(userId) {
  // 1. 既存データ確認
  const existing = await db.userTypeEstimates.findUnique({ where: { userId } });
  if (existing) {
    return formatApiResponse(existing, existing.updatedAt);
  }

  // 2. プロフィール確認
  const profile = await db.profiles.findUnique({ where: { id: userId } });

  // ケース0: プロフィール不存在 → 404
  if (!profile) {
    throw new NotFoundError('Profile not found');
  }

  const problems = profile.problems || [];

  if (problems.length === 0) {
    // ケース3: 空問題（プロフィール存在、problems空）→ 保存しない（デフォルト T4 を返却）
    const defaultData = { primaryType: 'T4', confidence: 0, scores: { T1: 0, T2: 0, T3: 0, T4: 0 } };
    return formatApiResponse(defaultData, new Date());
  }

  // ケース2: 即時計算→UPSERT
  const result = classifyUserType(problems);
  if (result.confidence > 0) {
    await db.userTypeEstimates.upsert({
      where: { userId },
      create: {
        userId,
        primaryType: result.primaryType,
        typeScores: result.scores,  // classifyUserType returns 'scores', Prisma model uses 'typeScores'
        confidence: result.confidence
      },
      update: {
        primaryType: result.primaryType,
        typeScores: result.scores,
        confidence: result.confidence
      }
    });
  }
  return formatApiResponse(result, new Date());
}
```

**Problem未設定時の挙動**:
- Problems が空配列の場合、デフォルトタイプ **T4（不安型）** を `confidence: 0` で返す
- **新規ユーザー**: user_type_estimates には保存しない（confidence > 0 の場合のみ保存）
- **既存ユーザーがProblemsをクリアした場合**: user_type_estimates の該当レコードを **DELETE** する
  - 理由: 古い推定値が残ると、タイプ別学習・Nudge生成で誤ったタイプが使われる
  - 実装場所: `apps/api/src/routes/mobile/profile.js` の Problems 更新ハンドラ
- テスト: `test_classifyUserType_empty_problems_returns_default`, `test_clearProblems_deletes_user_type_estimate`, `test_getUserType_calculates_on_missing` で検証

#### ※ 削除済み: POST /admin/tiktok/retention, POST /admin/tiktok/metrics

**理由**: メトリクス取得は Apify TikTok Scraper (`clockworks/tiktok-scraper`) で完全自動化。手動入力API不要。
`fetch_metrics.py` が24時間後に自動取得し、`tiktok_posts` と `hook_candidates` を更新する。

---

## 8. タスクリスト

### 8.1 1.5.0タスク

#### Track A: クロスユーザー学習

| # | タスク | ファイル | 詳細 | 優先度 |
|---|--------|----------|------|--------|
| A1 | ユーザータイプ分類ロジック実装 | `apps/api/src/services/userTypeService.js` | 上記アルゴリズムを実装 | 高 |
| A2 | タイプ推定APIエンドポイント | `apps/api/src/routes/mobile/userType.js` | GET /api/mobile/user-type | 高 |
| A3 | タイプ別統計集計ジョブ | `apps/api/src/jobs/aggregateTypeStats.js` | 日次でtype_statsを更新 | 高 |
| A4 | generateNudgesにタイプ別パターン注入 | `apps/api/src/jobs/generateNudges.js` | プロンプトにCross-Userセクション追加 + **hook_candidate_idをnudge_events.stateに保存**（計測用） | 高 |
| A5 | DBマイグレーション（user_type_estimates, type_stats） | `apps/api/prisma/migrations/` | 新テーブル作成 | 高 |
| A6 | **オンボーディング完了時の分類保存** | `apps/api/src/routes/mobile/onboarding.js` | オンボーディング完了API呼び出し時に`userTypeService.classifyAndSave()`を呼び出しuser_type_estimatesにUPSERT | 高 |
| A7 | **プロフィール更新時の再分類** | `apps/api/src/routes/mobile/profile.js` | Problems更新時に`userTypeService.reclassify()`を呼び出し。**Problems空の場合はuser_type_estimatesをDELETE** | 中 |
| A8 | **既存ユーザーバックフィルスクリプト** | `apps/api/src/scripts/backfill-user-types.js` | リリース時1回のみ実行（one-shot）、全既存ユーザーを分類→INSERT | 高 |

**A6/A7/A8 統合ポイント詳細**:
| 統合ポイント | ルート/イベント | 呼び出しサービス |
|-------------|----------------|-----------------|
| オンボーディング完了 | `POST /api/mobile/onboarding/complete` | `userTypeService.classifyAndSave(userId, problems)` |
| Problems更新（非空） | `PUT /api/mobile/profile/problems` | `userTypeService.reclassify(userId, newProblems)` |
| **Problems更新（空）** | `PUT /api/mobile/profile/problems` | `userTypeService.deleteEstimate(userId)` |
| バックフィル | `node scripts/backfill-user-types.js` | 全ユーザーに対して`classifyAndSave`を実行 |

#### Track B: TikTok投稿

| # | タスク | ファイル | 詳細 | 優先度 |
|---|--------|----------|------|--------|
| B1 | Hook候補ライブラリ初期データ作成 | `apps/api/src/scripts/initHookLibrary.js` | 上記SQLクエリで抽出 | 高 |
| B2 | TikTok投稿スケジューラー | `apps/api/src/jobs/postToTiktok.js` | 毎日12:00 JSTに実行 | 高 |
| B3 | TikTok指標取得ジョブ | `apps/api/src/jobs/fetchTiktokMetrics.js` | Research APIで取得 | 中 |
| B4 | Hook候補→指標反映ロジック | `apps/api/src/services/hookEvaluator.js` | 指標をhook_candidatesに反映 | 中 |
| B5 | DBマイグレーション（hook_candidates, tiktok_posts） | `apps/api/prisma/migrations/` | 新テーブル作成 | 高 |
| B6 | **retention_rate手動入力スクリプト** | `apps/api/src/scripts/input-retention-rate.js` | CLIで手動入力、バリデーション付き | 中 |
| B7 | retention_rate管理APIエンドポイント | `apps/api/src/routes/admin/tiktok.js` | POST /admin/tiktok/retention（認証必須） | 中 |
| B8 | retention_rate入力監査ログ | `apps/api/src/services/auditLogger.js` | 誰がいつ入力したか記録 | 低 |

#### Track C: 学習ループ統合（A+B完了後）

| # | タスク | ファイル | 詳細 | 優先度 |
|---|--------|----------|------|--------|
| C1 | wisdom判定ロジック | `apps/api/src/services/wisdomExtractor.js` | 両チャネルで効くHookを抽出 | 中 |
| C2 | wisdomをプロンプトに注入 | `apps/api/src/jobs/generateNudges.js` | wisdom_patternsをプロンプトに追加 | 中 |
| C3 | DBマイグレーション（wisdom_patterns） | `apps/api/prisma/migrations/` | 新テーブル作成 | 中 |
| C4 | **TikTok高成績Hook→アプリ選定ロジック** | `apps/api/src/jobs/generateNudges.js` | hook_candidates参照し、TikTok高成績Hookを候補として優先 | 高 |
| C5 | Hook選定アルゴリズム | `apps/api/src/services/hookSelector.js` | Thompson Sampling（探索20% + 活用80%）でHook候補を選択 | 高 |

### 8.2 1.6.0タスク

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| D1 | ペルソナ生成（実データから） | `apps/api/src/services/personaGenerator.js` | 高 |
| D2 | LLMでペルソナシミュレート | `apps/api/src/services/userSimulator.js` | 高 |
| D3 | 大量介入テスト | `apps/api/src/jobs/simulationTest.js` | 中 |
| D4 | パターン抽出 | `apps/api/src/services/patternExtractor.js` | 中 |
| D5 | 実データ検証ループ | `apps/api/src/services/patternValidator.js` | 中 |

### 8.3 1.7.0タスク（オプション）

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| E1 | Contextual Bandit実装 | `aniccaios/Services/ContextualBandit.swift` | 低 |
| E2 | 非定常対応（忘却） | 同上 | 低 |
| E3 | LLM×Bandit統合 | 同上 | 低 |

---

## 9. 並列実装計画（Worktree）

### 9.1 並列可能性分析

| Track | 依存関係 | 並列実行 | 担当ディレクトリ |
|-------|---------|---------|----------------|
| Track A（クロスユーザー学習） | なし | ✅ 可能 | `apps/api/src/services/`, `apps/api/src/routes/` |
| Track B（TikTok投稿） | なし | ✅ 可能 | `apps/api/src/jobs/`, `apps/api/src/services/hookEvaluator.js` |
| Track C（学習ループ統合） | A + B 完了後 | ❌ 待機 | `apps/api/src/jobs/generateNudges.js` |
| **SNS Poster（別 Spec）** | **なし** | **✅ 可能** | **`.cursor/plans/ios/sns-poster/*.py`, `.github/workflows/`** |

**注**: SNS Poster は別エージェントが `sns-full-automation-spec.md` に基づき並列実装。Python スクリプトのため Node.js バックエンドとコンフリクトなし。

### 9.2 Worktree構成

```
~/Downloads/
├── anicca-project/                    ← メインリポジトリ（dev）
├── anicca-1.5.0-track-a/             ← Worktree（Track A: クロスユーザー学習）
├── anicca-1.5.0-track-b/             ← Worktree（Track B: TikTok投稿）
└── anicca-sns-poster/                ← Worktree（SNS Poster: 別エージェント）
```

### 9.3 Worktree作成コマンド

```bash
# Track A: クロスユーザー学習
git worktree add ../anicca-1.5.0-track-a -b feature/1.5.0-cross-user-learning

# Track B: TikTok投稿
git worktree add ../anicca-1.5.0-track-b -b feature/1.5.0-tiktok-bridge

# SNS Poster（別エージェントが実行）
git worktree add ../anicca-sns-poster -b feature/sns-poster
```

### 9.4 担当範囲（触るファイル）

| Worktree | 触るファイル | 触らないファイル |
|----------|------------|----------------|
| Track A | `apps/api/src/services/userTypeService.js`<br>`apps/api/src/routes/mobile/userType.js`<br>`apps/api/src/jobs/aggregateTypeStats.js`<br>`apps/api/src/jobs/generateNudges.js`（タイプ別パターンセクション追加のみ） | `scripts/sns-poster/**`, `.cursor/plans/ios/sns-poster/**` |
| Track B | `apps/api/src/jobs/postToTiktok.js`<br>`apps/api/src/jobs/fetchTiktokMetrics.js`<br>`apps/api/src/services/hookEvaluator.js` | `apps/api/src/services/userTypeService.js`, `.cursor/plans/ios/sns-poster/**` |
| SNS Poster | `.cursor/plans/ios/sns-poster/*.py`<br>`.github/workflows/sns-daily.yml` | `apps/api/**`（一切触らない） |

### 9.5 マージ順序

```
1. Track A と Track B と SNS Poster を並列実行
2. Track A + B 完了後、dev にマージ（A → B の順）
3. Track C を dev で実行
4. SNS Poster は独立してマージ可能（Track A/B/C と依存関係なし）
5. 全完了後、main にマージ → リリース
```

---

## 10. TikTok Bridge詳細

### 10.1 投稿コンテンツ形式

| フェーズ | 形式 | 目的 |
|---------|------|------|
| 初期（1.5.0） | 静止画（Hook + ビジュアル） | 最小ループ確立 |
| 中期（1.6.0+） | スライド（3-5枚） | Content評価 |
| 将来 | 動画 | 完全なNudge体験 |

### 10.2 投稿生成パイプライン

```
1. Hook候補選択（探索20% + 活用80%）
   └── Thompson Sampling でバランス
2. Fal.ai FLUX で画像生成
   └── プロンプト: "Minimalist illustration about {hook_theme}, modern app style, light background"
3. Blotato API で投稿
   └── Account ID: 27339
   └── isAiGenerated: true
4. tiktok_posts テーブルに記録
```

### 10.3 指標取得パイプライン

```
1. 24時間後にTikTok Research APIで取得
   └── GET /v2/research/video/query/
   └── fields: view_count, like_count, comment_count, share_count
2. tiktok_posts.metrics_fetched_at を更新
3. hook_candidates のtiktok_*カラムを更新
4. 週1でretention_rateを手動入力（管理画面 or スクリプト）
```

### 10.4 禁止事項

| 禁止 | 理由 |
|------|------|
| ビュー最大化に寄せる | 煽りに走る危険 |
| 罪悪感を煽る表現 | "苦しみを減らす"の反対 |
| 自動スクロール/自動いいね | 規約違反リスク |

---

## 11. シミュレーション詳細

### 11.1 ペルソナ定義

```typescript
interface SimulatedPersona {
  id: string;
  attributes: {
    type: string;            // T1, T2, etc.
    problemTypes: string[];  // 選択した問題
    age: string;             // "20s", "30s", etc.
    lifestyle: string;       // "office_worker", "student", etc.
  };
  behavior: {
    preferredTone: string;
    activeHours: number[];
    responsePattern: string; // "quick_responder", "slow_responder"
  };
  history: SimulatedInteraction[];
}
```

### 11.2 シミュレーション精度評価

| 指標 | 合格条件 |
|------|---------|
| Offline replay再現率 | 70%以上 |
| タイプ別誤差 | 各タイプで60%以上 |
| 極端な乖離 | 30%以下の再現率のセグメントがないこと |

### 11.3 校正プロトコル

```
1. 過去ログ（context, arm, reward）を固定
2. シミュレータに同じcontextを与えて予測
3. 予測 vs 実際のrewardを比較
4. 再現率を計算
5. 閾値未満 → シミュ調整 → 再評価
6. 閾値以上 → 候補ふるいに使用可能
```

---

## 12. テストマトリックス

### 12.1 1.5.0テスト

| # | 機能 | テスト名 | 種別 | カバー |
|---|------|----------|------|--------|
| 1 | タイプ分類 | `test_classifyUserType_returnsCorrectType` | Unit | ✅ |
| 2 | タイプ分類 | `test_classifyUserType_confidence_calculation` | Unit | ✅ |
| 3 | タイプ分類 | `test_classifyUserType_empty_problems_returns_default` | Unit | ✅ |
| 3b | タイプ分類 | `test_clearProblems_deletes_user_type_estimate` | Integration | ✅ |
| 4 | タイプ別集計 | `test_aggregateTypeStats_updates_correctly` | Integration | ✅ |
| 5 | タイプ推定API | `test_userTypeEndpoint_returns_estimate` | Integration | ✅ |
| 6 | Hook候補ライブラリ | `test_initHookLibrary_extracts_from_events` | Integration | ✅ |
| 7 | TikTok投稿 | `test_postToTiktok_creates_post_record` | Integration | ✅ |
| 8 | TikTok指標取得 | `test_fetchTiktokMetrics_updates_hook_candidates` | Integration | ✅ |
| 9 | wisdom判定 | `test_wisdomExtractor_identifies_cross_channel_patterns` | Unit | ✅ |
| 10 | プロンプト注入 | `test_generateNudges_includes_cross_user_patterns` | Integration | ✅ |
| 11 | Hook選定 | `test_hookSelector_prioritizes_tiktok_high_performers` | Unit | ✅ |
| 12 | Hook選定 | `test_hookSelector_thompson_sampling_balance` | Unit | ✅ |
| 13 | retention手動入力 | `test_inputRetentionRate_validates_range` | Unit | ✅ |
| 14 | retention手動入力 | `test_inputRetentionRate_creates_audit_log` | Integration | ✅ |
| 15 | retention管理API | `test_retentionEndpoint_requires_auth` | Integration | ✅ |
| 16 | cold start | `test_coldStart_newUser_tapRate_within_threshold` | Integration | ✅ |
| 17 | APIフォールバック | `test_tiktokMetrics_fallback_on_api_error` | Integration | ✅ |

### 12.2 1.6.0テスト

| # | 機能 | テスト名 | 種別 |
|---|------|----------|------|
| 11 | ペルソナ生成 | `test_personaGeneration_creates_valid_personas` | Unit |
| 12 | シミュ精度 | `test_simulatorAccuracy_meets_threshold` | Integration |
| 13 | パターン検証 | `test_patternValidation_confirms_with_real_data` | Integration |

---

## 13. 境界（やらないこと）

### 13.1 1.5.0でやらないこと

| やらないこと | 理由 |
|-------------|------|
| Rolling Plan（イベント駆動リプラン） | 1日計画でOK。抽象化が優先 |
| リアルタイム最適化 | 方向Bを選択。Buddhaの道 |
| オンボーディング追加質問 | Proactiveの核。推定で勝つ |
| TikTok retention_rate API取得 | 取得不可。手動入力で代替 |
| TikTok save_count API取得 | 取得不可。share_countで代替 |

### 13.2 全バージョン共通で禁止

| 禁止 | 理由 |
|------|------|
| 本番決定にシミュを使う | 実データで検証するまで使わない |
| TikTokの自動操作 | 規約違反リスク |
| 選んでないProblemTypeへのジャンプ | 安全に深掘りが優先 |

---

## 14. レビューチェックリスト

### 14.1 Specレビュー

- [x] 汎用化の目的が明確か
- [x] Level 1→2→3の進化が定義されているか
- [x] 各バージョンの受け入れ条件が測定可能か
- [x] TikTokが「Anicca統合」として位置づけられているか
- [x] シミュレーションの役割が限定されているか
- [x] TikTok APIの制約が反映されているか
- [x] タイプ分類アルゴリズムが具体的か
- [x] DBスキーマが定義されているか
- [x] 並列実装計画が明確か

### 14.2 実装レビュー

- [ ] タイプ分類ロジックがテスト済みか
- [ ] Hook候補ライブラリがアプリ+TikTok両方から更新されるか
- [ ] 汎用パターンがプロンプトに注入されているか
- [ ] 後方互換性が保たれているか

---

## ローカライズ

| 項目 | 方針 |
|------|------|
| Spec言語 | 日本語 |
| 実装文字列 | 原則なし（ロジック中心） |
| TikTok投稿 | 英語中心（日本語は後追い） |

---

## 後方互換性

| 項目 | 方針 |
|------|------|
| 通知userInfo形式 | 既存形式を維持 |
| Stats保存形式 | 変更時は移行期間を設ける |
| ルールベース | 安全網として維持 |
| generateNudges.js | 既存処理に追加的変更のみ |
| nudge_events.state拡張 | 新フィールド（hook_candidate_id, user_type）追加は後方互換 |

**ETL/分析クエリへの影響確認項目**:
- [ ] Mixpanel/BigQuery連携で `state` を解析している場合、新フィールドの追加を許容するか確認
- [ ] 既存ダッシュボード/レポートで `state` 構造の変更による影響なしを確認
- [ ] バッチ分析ジョブが新フィールドを無視しても問題ないことを確認

---

## 運用・監視

### ジョブ監視

| ジョブ | 失敗時アラート条件 | 手動対応 |
|--------|------------------|---------|
| postToTiktok | 2連続失敗 | Blotato接続確認、手動投稿 |
| fetchTiktokMetrics | 3連続失敗 | Research API認証確認、手動入力に切替 |
| aggregateTypeStats | 1回失敗 | ログ確認、手動再実行 |

### SLA

| 項目 | SLA |
|------|-----|
| tiktok_high_performer フラグ更新 → generateNudges反映 | 48時間以内 |
| TikTok投稿後 → 指標取得 | 24時間以内 |
| オンボーディング完了 → user_type_estimates保存 | リアルタイム（API内同期処理） |

### 運用KPI

| KPI | 目標 | 測定方法 |
|-----|------|---------|
| ジョブ成功率 | 95%以上 | Railway Logs / Sentry |
| メトリクス取得遅延 | 24h以内 | tiktok_posts.metrics_fetched_at - posted_at |

---

## ユーザー作業（実装前/中/後）

### 実装前

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | TikTok Research API申請 | [TikTok Developer Portal](https://developers.tiktok.com/) → Research API申請 | Client Key, Client Secret |
| 2 | Blotato接続確認 | [Blotato Dashboard](https://my.blotato.com/) → TikTok Account ID: 27339 確認 | 接続ステータス |

### 実装中

| # | タイミング | タスク | 理由 |
|---|-----------|--------|------|
| 1 | TikTok API接続後 | 取得可能指標の最終確認 | APIレスポンスで実際に取れる指標を確認 |

### 実装後

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | 週1でCreator Center確認 | retention_rate手動入力 |
| 2 | 1週間後にcold start効果測定 | 新規ユーザーのtap率比較 |

---

## 15. Skills/Sub-agents使用マップ

### 15.1 1.5.0での使用

| タスク | スキル/サブエージェント | 責務 |
|--------|----------------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd-workflow` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |
| TikTok API調査 | `tech-spec-researcher` | APIドキュメント調査 |
| DBマイグレーション | `Bash` | prisma migrate dev 実行 |
| 並列実装（Track A/B） | `Task` + Worktree | 独立した作業空間で並列実行 |

### 15.2 タスク別詳細

| Track | タスク | 推奨サブエージェント | 理由 |
|-------|--------|-------------------|------|
| Track A | ユーザータイプ分類ロジック | `tdd-guide` | アルゴリズムはTDDで実装 |
| Track A | タイプ推定API | `code-quality-reviewer` | API設計レビュー |
| Track B | TikTok投稿スケジューラー | `test-automation-engineer` | cron + 外部API連携テスト |
| Track B | Hook候補ライブラリ | `architect` | データモデル設計 |
| Track C | wisdom判定ロジック | `tdd-guide` | 閾値ベースロジックはTDD |

---

## 16. iOS側変更

### 16.1 1.5.0でのiOS変更（なし）

1.5.0はバックエンド中心の変更。iOS側の変更は不要。

| 項目 | 変更 | 理由 |
|------|------|------|
| UIの変更 | なし | バックエンドでタイプ別パターンを処理 |
| 新規APIコール | なし | 既存の `/api/mobile/nudge/today` で十分 |
| Feature Flag | なし | バックエンドで制御 |

### 16.2 1.7.0でのiOS変更

| 項目 | ファイル | 変更内容 |
|------|---------|---------|
| Contextual Bandit | `aniccaios/Services/ContextualBandit.swift` | 新規作成（オプション） |
| データ同期 | `aniccaios/Services/NudgeService.swift` | Bandit用の追加パラメータ |
| Feature Flag | `AppConfig.swift` | `isBanditEnabled` フラグ追加 |

### 16.3 後方互換性

| バージョン | 対応 |
|-----------|------|
| 1.3.0以前 | 既存API維持、新フィールドは無視 |
| 1.4.0 | `scheduledTime` 対応済み |
| 1.5.0 | iOS変更なし（バックエンドのみ） |
| 1.6.0 | iOS変更なし（シミュレーションはバックエンドのみ） |
| 1.7.0 | Bandit実装時はFeature Flagで段階的ロールアウト |

---

## 17. 実行手順

### 17.1 環境変数設定

```bash
# 必須（TikTok連携）
TIKTOK_CLIENT_KEY=xxx
TIKTOK_CLIENT_SECRET=xxx
BLOTATO_API_KEY=xxx

# 既存（変更なし）
OPENAI_API_KEY=xxx
DATABASE_URL=xxx
```

### 17.2 DBマイグレーション順序

```bash
# 1. Track A のテーブル作成
cd apps/api
npx prisma migrate dev --name add_user_type_estimates
npx prisma migrate dev --name add_type_stats

# 2. Track B のテーブル作成
npx prisma migrate dev --name add_hook_candidates
npx prisma migrate dev --name add_tiktok_posts

# 3. Track C のテーブル作成（A+B完了後）
npx prisma migrate dev --name add_wisdom_patterns
```

### 17.3 Cronジョブ設定（Railway）

| ジョブ | スケジュール | 説明 |
|--------|------------|------|
| aggregateTypeStats | 0 21 * * * | 毎日6:00 JST（UTC 21:00） |
| postToTiktok | 0 3 * * 1-5 | 平日12:00 JST（UTC 03:00） |
| fetchTiktokMetrics | 0 3 * * 2-6 | **翌平日12:00 JST**（UTC 03:00、火-土） |
| extractWisdom | 0 22 * * 0 | 毎週日曜7:00 JST（UTC 22:00） |

**fetchTiktokMetricsの24h経過フィルタ条件**:
```javascript
// 投稿から24時間以上経過した投稿のみ取得対象
const targetPosts = await prisma.tiktokPost.findMany({
  where: {
    metricsFetchedAt: null,
    postedAt: {
      lte: new Date(Date.now() - 24 * 60 * 60 * 1000) // 24h前以前
    }
  }
});
```

### 17.4 retention_rate手動入力手順

```bash
# 週1でCreator Centerから取得し、以下のスクリプトで入力
cd apps/api
node scripts/input-retention-rate.js --post-id=xxx --rate=0.42

# または管理用エンドポイント（認証必須）
curl -X POST https://api.anicca.ai/admin/tiktok/retention \
  -H "X-Admin-Key: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"postId": "xxx", "retentionRate": 0.42}'
```

### 17.5 ロールバック手順

```bash
# DBマイグレーションのロールバック
cd apps/api
npx prisma migrate reset --skip-seed  # 注意: データ削除

# 特定のマイグレーションのみ戻す場合
# 1. Prismaスキーマから該当モデルを削除
# 2. npx prisma migrate dev --name rollback_xxx
# 3. 手動でDROPを実行（または新しいマイグレーションで）
```

### 17.6 段階的ロールアウト

| フェーズ | 対象 | 確認項目 |
|---------|------|---------|
| 1 | 開発環境のみ | 全テストPASS |
| 2 | Staging + 内部ユーザー | cold start改善の初期兆候 |
| 3 | 新規ユーザー10% | tap率の差異確認 |
| 4 | 新規ユーザー100% | 全体への展開 |

---

## 参考

| 種別 | リンク |
|------|--------|
| TikTok Research API | https://developers.tiktok.com/doc/research-api-specs-query-videos/ |
| TikTok Analytics Guide | https://agencyanalytics.com/blog/tiktok-analytics |
| User Segmentation Best Practices | https://neptune.ai/blog/customer-segmentation-using-machine-learning |
| 既存SNS自動化 | `.cursor/plans/ios/marketing/sns-automation-spec.md` |
| Meta-Learning研究 | https://research.aimultiple.com/meta-learning/ |
| User Simulation研究 | https://arxiv.org/abs/2501.04410 |

---

*このSpecは1.5.0/1.6.0/1.7.0の実装を定義する。*
*Track A と Track B は並列実行可能。*
