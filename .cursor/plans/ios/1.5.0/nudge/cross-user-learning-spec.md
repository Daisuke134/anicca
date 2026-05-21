# 1.5.0 クロスユーザー学習・統合・実装計画

> **関連Spec**: [tiktok-agent-spec.md](./tiktok-agent-spec.md) | [db-schema-spec.md](./db-schema-spec.md)
>
> **最終更新**: 2026-01-28（Spec改善: Admin APIコントラクト追加、画像モデル変更、video_id照合戦略確定、agent_reasoning追加）
>
> **スコープ**: クロスユーザー学習、Hook候補ライブラリ、学習ループ統合、受け入れ条件、タスクリスト、並列実装計画、テストマトリックス

---

## 目次

1. [クロスユーザー学習](#1-クロスユーザー学習)
2. [Hook候補ライブラリ](#2-hook候補ライブラリ)
3. [学習ループ統合](#3-学習ループ統合)
4. [受け入れ条件](#4-受け入れ条件)
5. [タスクリスト](#5-タスクリスト)
6. [並列実装計画（Worktree）](#6-並列実装計画worktree)
7. [テストマトリックス](#7-テストマトリックス)
8. [iOS側変更](#8-ios側変更)
9. [ユーザーGUI作業](#9-ユーザーgui作業)
10. [実行手順](#10-実行手順)
11. [Track A 実装判断（2026-01-28 確定）](#11-track-a-実装判断2026-01-28-確定)

---

## 1. クロスユーザー学習

### 1.1 ユーザータイプ分類

| タイプID | タイプ名 | 特徴 |
|---------|---------|------|
| T1 | 完璧主義 | できない自分を許せない |
| T2 | 比較傾向 | 他人と比べて落ち込む |
| T3 | 衝動型 | 衝動を抑えられない |
| T4 | 不安型 | 将来を心配しすぎる |

### 1.2 タイプ分類アルゴリズム（確定）

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

### 1.3 タイプ別パターン

| タイプ | 効くトーン | 効くHookパターン | 効くContent長さ |
|--------|-----------|-----------------|----------------|
| T1（完璧主義） | strict | 短い命令形 | 短い（40字以下） |
| T2（比較傾向） | gentle | 共感形 | 中程度 |
| T3（衝動型） | provocative | 挑発形 | 短い |
| T4（不安型） | logical | 論理形 | 長い（説明付き） |

### 1.4 「効く」の閾値（確定）

| チャネル | 指標 | 閾値 | 必要サンプル数 |
|---------|------|------|---------------|
| アプリ | tap率 | > 50% | n >= 10 |
| アプリ | thumbsUp率 | > 60% | n >= 10 |
| TikTok | share率 | > 5% | n >= 5 |
| TikTok | like/view比 | > 10% | n >= 5 |
| wisdom判定 | アプリ+TikTok両方で効く | 上記全て満たす | - |

### 1.5 プロンプト変更

generateNudges.js のプロンプトに以下セクションを追加：

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

### 1.6 nudge_events.state スキーマ拡張

**generateNudgesで保存するstate構造**（計測用フィールド追加）:
```json
{
  "hook": "...",
  "content": "...",
  "tone": "strict",
  "hook_candidate_id": "uuid-of-hook-candidate",
  "user_type": "T1",
  "scheduledTime": "2026-02-01T09:00:00Z"
}
```

**保存トリガー**: generateNudges.js でNudgeを生成するタイミング

### 1.7 user_type_estimates 更新経路

| トリガー | 処理 | 備考 |
|---------|------|------|
| オンボーディング完了時 | 選択したProblemsから分類→UPSERT | 新規ユーザー |
| プロフィール更新時 | Problems変更があれば再分類→UPDATE | 既存ユーザー |
| バックフィルジョブ（1回） | 既存ユーザー全員を分類→INSERT | リリース時に実行 |

**実装場所**: `apps/api/src/services/userTypeService.js`

---

## 2. Hook候補ライブラリ

### 2.1 初期データ作成手順（確定）

```sql
-- 1.4.0のnudge_eventsからHook抽出クエリ
-- ※ tone正規化: CHECK制約(5種)に合わせて不正値は'logical'にフォールバック
SELECT
  ne.state->>'hook' as hook,
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
INSERT INTO hook_candidates (text, tone, target_problem_types, app_tap_rate, app_thumbs_up_rate, app_sample_size)
SELECT
  hook as text,
  tone,
  ARRAY_AGG(DISTINCT problem_type) as target_problem_types,
  COALESCE(SUM(tapped_count)::NUMERIC / NULLIF(SUM(sample_size), 0), 0) as app_tap_rate,
  COALESCE(SUM(thumbs_up_count)::NUMERIC / NULLIF(SUM(tapped_count), 0), 0) as app_thumbs_up_rate,
  SUM(sample_size) as app_sample_size
FROM (
  -- 上記SELECTクエリと同じサブクエリ
  SELECT
    ne.state->>'hook' as hook,
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

**データモデル前提（全集計クエリ共通）**:
- `nudge_events` と `nudge_outcomes` は **1:1** の関係（UNIQUE制約あり）
- **signals スキーマ**: `thumbsUp` は文字列 `"true"` / `"false"` で保存（既存実装）

### 2.2 Hook候補データモデル

```typescript
interface HookCandidate {
  id: string;
  text: string;
  tone: 'strict' | 'gentle' | 'logical' | 'provocative' | 'philosophical';
  targetProblemTypes: string[];
  targetUserTypes: string[];
  appPerformance: {
    tapRate: number;
    thumbsUpRate: number;
    sampleSize: number;
    lastUpdated: Date;
  };
  tiktokPerformance: {
    likeRate: number;
    shareRate: number;
    sampleSize: number;
    lastUpdated: Date;
  };
  isWisdom: boolean;
  explorationWeight: number;
  createdAt: Date;
  updatedAt: Date;
}
```

**エージェント連携**: Aniccaエージェント（`anicca_tiktok_agent.py`）が `get_hook_candidates` ツールでこのテーブルを読み、投稿内容の判断に使用する。高成績のHookを活用枠（80%）、新規Hookを探索枠（20%）でThompson Samplingにより選択。

---

## 3. 学習ループ統合

### 3.1 統合学習図

```
Anicca（1つの脳）
│
├── チャネル1: アプリ内 Nudge
│   └── tap/👍👎 → hook_candidates.app_* 更新
│
├── チャネル2: TikTok（ENから開始）
│   └── like/share/view → hook_candidates.tiktok_* 更新
│
└── 統合
    ├── type_stats: タイプ × tone の集計
    ├── hook_candidates: 両チャネルの成績統合
    └── wisdom_patterns: 両方で効く = wisdom
```

### 3.2 wisdom判定ロジック

Hook候補が以下を**全て**満たす場合 `is_wisdom = true`:

| チャネル | 条件 |
|---------|------|
| アプリ | tap率 > 50% AND サンプルサイズ >= 10 |
| アプリ | thumbsUp率 > 60% AND サンプルサイズ >= 10 |
| TikTok | like/view比 > 10% AND サンプルサイズ >= 5 |
| TikTok | share率 > 5% AND サンプルサイズ >= 5 |

### 3.3 wisdomのプロンプト注入

generateNudges.jsで、wisdom_patternsテーブルから取得したパターンをプロンプトに追加：

```markdown
## 🌟 Wisdom (Proven across app AND TikTok)

### Pattern: 挫折経験の直接指摘
- Works for: T1, T3
- Tone: strict / provocative
- Evidence: App tap率 72%, TikTok like率 11%, share率 7%
- Example hooks: "また3時まで起きてた？", "10個目の習慣アプリ、今度は何日もつ？"
```

### 3.4 TikTok高成績Hook → アプリ選定

`generateNudges.js` で hook_candidates を参照し、`tiktok_high_performer = true` のHookを候補として優先する。

**Hook選定アルゴリズム（hookSelector.js）**:
- 活用枠（80%）: 高成績Hook（アプリ + TikTok）から選択
- 探索枠（20%）: 新規 or 低サンプルのHookから選択
- 選択方法: Thompson Sampling

---

## 4. 受け入れ条件

| # | 条件 | 測定方法 |
|---|------|---------|
| 1 | 新規ユーザーのcold startが解消 | 下記4.1詳細参照 |
| 2 | タイプ別パターンが蓄積 | 最低3タイプ × 3パターン（4.2参照） |
| 3 | TikTok投稿が稼働 | 週5投稿以上（4.3参照） |
| 4 | TikTokの学びがアプリに反映 | TikTok高成績Hookがアプリで使用される（4.4参照） |

### 4.1 cold start改善の測定詳細（統計条件）

| 項目 | 条件 |
|------|------|
| **比較対象** | 同週の既存ユーザー（30日以上利用）のtap率 |
| **新規ユーザー定義** | 測定期間中にインストール（`profiles.created_at` ≒ インストール日） |
| **測定期間** | リリース後14日間 |
| **サンプルサイズ** | 各群最低30ユーザー |
| **成功基準** | 新規tap率 ≥ 既存tap率 × 0.9（非劣性マージンΔ=10%） |
| **ProblemType** | 同一ProblemType内で比較 |
| **統計的検証** | 差の95%CI下限 ≥ -Δ で非劣性確認 |

**計測クエリ**: `scripts/coldStartAnalysis.js` でBootstrap法（1000イテレーション）により95%CIを算出。

### 4.2 タイプ別パターン蓄積の測定詳細

| 項目 | 条件 |
|------|------|
| **「パターン」の定義** | タイプ × tone で、tap率 > 50% かつ サンプルサイズ >= 10 |
| **成功基準** | 3タイプ以上 × 各3tone以上 |
| **測定方法** | type_statsテーブルの有効レコード数カウント |

**計測クエリ**:
```sql
SELECT type_id, COUNT(*) as pattern_count
FROM type_stats
WHERE tap_rate > 0.50 AND sample_size >= 10
GROUP BY type_id
HAVING COUNT(*) >= 3;
-- 3行以上返れば条件達成
```

### 4.3 TikTok投稿稼働の測定詳細

| 項目 | 条件 |
|------|------|
| **定義** | 直近7日間で tiktok_posts に5件以上 |
| **測定頻度** | 週1回（月曜に前週分確認） |

### 4.4 TikTok高成績Hook使用の測定詳細

| 項目 | 条件 |
|------|------|
| **「高成績」定義** | like率 > 10% AND share率 > 5% AND サンプルサイズ >= 5 |
| **「使用」定義** | 直近7日間の生成Nudgeのうち、高成績Hook由来が10%以上 |

---

## 5. タスクリスト

### 5.1 Track A: クロスユーザー学習（Node.js バックエンド）

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| A1 | ユーザータイプ分類ロジック実装 | `apps/api/src/services/userTypeService.js` | 高 |
| A2 | タイプ推定APIエンドポイント | `apps/api/src/routes/mobile/userType.js` | 高 |
| A3 | タイプ別統計集計ジョブ | `apps/api/src/jobs/aggregateTypeStats.js` | 高 |
| A4 | generateNudgesにタイプ別パターン注入 + hook_candidate_id保存 | `apps/api/src/jobs/generateNudges.js` | 高 |
| A5 | DBマイグレーション（user_type_estimates, type_stats） | `apps/api/prisma/migrations/` | 高 |
| A6 | オンボーディング完了時の分類保存 | `apps/api/src/routes/mobile/onboarding.js` | 高 |
| A7 | プロフィール更新時の再分類 | `apps/api/src/routes/mobile/profile.js` | 中 |
| A8 | 既存ユーザーバックフィルスクリプト | `apps/api/src/scripts/backfill-user-types.js` | 高 |

**統合ポイント詳細**:

| 統合ポイント | ルート/イベント | 呼び出しサービス |
|-------------|----------------|-----------------|
| オンボーディング完了 | `POST /api/mobile/onboarding/complete` | `userTypeService.classifyAndSave(userId, problems)` |
| Problems更新（非空） | `PUT /api/mobile/profile/problems` | `userTypeService.reclassify(userId, newProblems)` |
| Problems更新（空） | `PUT /api/mobile/profile/problems` | `userTypeService.deleteEstimate(userId)` |
| バックフィル | `node scripts/backfill-user-types.js` | 全ユーザーに対して `classifyAndSave` を実行 |

### 5.2 Track B: Aniccaエージェント + TikTok自動投稿（Python + Node.js Admin API）

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| B0a | Admin APIルート作成（TikTok） | `apps/api/src/routes/admin/tiktok.js`（新規） | 高 |
| B0b | Admin APIルート作成（HookCandidates） | `apps/api/src/routes/admin/hookCandidates.js`（新規） | 高 |
| B0c | Admin APIルート登録 | `apps/api/src/routes/index.js`（修正） | 高 |
| B1 | Hook候補ライブラリ初期データ作成 | `apps/api/src/scripts/initHookLibrary.js` | 高 |
| B2 | Aniccaエージェント本体 | `scripts/anicca-agent/anicca_tiktok_agent.py` | 高 |
| B3 | ツール: search_trends（Exa API） | `scripts/anicca-agent/tools/search_trends.py` | 高 |
| B4 | ツール: hook_candidates（API経由DB読み取り） | `scripts/anicca-agent/tools/hook_candidates.py` | 高 |
| B5 | ツール: generate_image（Fal.ai **Ideogram v3**） | `scripts/anicca-agent/tools/generate_image.py` | 高 |
| B6 | ツール: evaluate_image（OpenAI Vision） | `scripts/anicca-agent/tools/evaluate_image.py` | 中 |
| B7 | ツール: post_to_tiktok（Blotato） | `scripts/anicca-agent/tools/post_to_tiktok.py` | 高 |
| B8 | ツール: save_record（API経由DB書き込み） | `scripts/anicca-agent/tools/save_record.py` | 高 |
| B9 | メトリクス取得ジョブ（Apify + video_id照合） | `scripts/anicca-agent/fetch_metrics.py` | 高 |
| B10 | GitHub Actions: daily-post | `.github/workflows/anicca-daily-post.yml` | 高 |
| B11 | GitHub Actions: fetch-metrics | `.github/workflows/fetch-metrics.yml` | 高 |
| B12 | DBマイグレーション（tiktok_posts.agent_reasoning追加） | `apps/api/prisma/migrations/` | 高 |
| B13 | Hook候補→指標反映ロジック | EP-6: refresh-tiktok-stats | 中 |

### 5.3 Track C: 学習ループ統合（A+B完了後）

| # | タスク | ファイル | 優先度 |
|---|--------|----------|--------|
| C1 | wisdom判定ロジック | `apps/api/src/services/wisdomExtractor.js` | 中 |
| C2 | wisdomをプロンプトに注入 | `apps/api/src/jobs/generateNudges.js` | 中 |
| C3 | DBマイグレーション（wisdom_patterns） | `apps/api/prisma/migrations/` | 中 |
| C4 | TikTok高成績Hook→アプリ選定ロジック | `apps/api/src/jobs/generateNudges.js` | 高 |
| C5 | Hook選定アルゴリズム（Thompson Sampling） | `apps/api/src/services/hookSelector.js` | 高 |

### 5.4 全タスクの依存関係

```
A5（DBマイグレーション）→ A1 → A6, A7, A8 → A3 → A4
                                                    ↓
B12（DBマイグレーション）→ B1 → B2-B8 → B9-B11 → B13
                                                    ↓
                                              C1-C5（統合）
```

---

## 6. 並列実装計画（Worktree）

### 6.1 並列可能性分析

| Track | 依存関係 | 並列実行 | 言語 |
|-------|---------|---------|------|
| Track A（クロスユーザー学習） | なし | ✅ 可能 | Node.js |
| Track B（Aniccaエージェント + TikTok） | なし | ✅ 可能 | Python + Node.js（DB） |
| Track C（学習ループ統合） | A + B 完了後 | ❌ 待機 | Node.js |

### 6.2 Worktree構成

```
~/Downloads/
├── anicca-project/                    ← メインリポジトリ（dev）
├── anicca-1.5.0-track-a/             ← Worktree（Track A: クロスユーザー学習）
└── anicca-1.5.0-track-b/             ← Worktree（Track B: Aniccaエージェント）
```

### 6.3 Worktree作成コマンド

```bash
# Track A: クロスユーザー学習
git worktree add ../anicca-1.5.0-track-a -b feature/1.5.0-cross-user-learning

# Track B: Aniccaエージェント
git worktree add ../anicca-1.5.0-track-b -b feature/1.5.0-tiktok-agent
```

### 6.4 担当範囲（触るファイル）

| Worktree | 触るファイル | 触らないファイル |
|----------|------------|----------------|
| Track A | `apps/api/src/services/userTypeService.js`（新規）<br>`apps/api/src/routes/mobile/userType.js`（新規）<br>`apps/api/src/jobs/aggregateTypeStats.js`（新規）<br>`apps/api/src/jobs/generateNudges.js`（タイプ別パターン追加のみ）<br>`apps/api/src/routes/mobile/onboarding.js`（分類呼び出し追加）<br>`apps/api/src/routes/mobile/profile.js`（再分類追加）<br>`apps/api/src/scripts/backfill-user-types.js`（新規）<br>`apps/api/prisma/schema.prisma`（UserTypeEstimate, TypeStats追加） | `scripts/anicca-agent/**` |
| Track B | `scripts/anicca-agent/**`（全て新規）<br>`.github/workflows/anicca-daily-post.yml`（新規）<br>`.github/workflows/fetch-metrics.yml`（新規）<br>`apps/api/prisma/schema.prisma`（HookCandidate, TiktokPost追加）<br>`apps/api/src/scripts/initHookLibrary.js`（新規） | `apps/api/src/services/userTypeService.js`<br>`apps/api/src/routes/mobile/userType.js` |

**共有ファイル（コンフリクト注意）**:
- `apps/api/prisma/schema.prisma` — Track AとBで別モデルを追加。マージ時にモデル追加が衝突しないよう、Aが先にマージ。
- `apps/api/src/jobs/generateNudges.js` — Track Aのみ修正。Track Cで追加修正。

### 6.5 マージ順序

```
1. Track A と Track B を並列実行
2. Track A を dev にマージ（DBマイグレーション + schema.prisma が先）
3. Track B を dev にマージ（schema.prisma のコンフリクトを解決）
4. Track C を dev で実行（A+B のコードが揃った状態で）
5. 全完了後、main にマージ → release/1.5.0
```

---

## 7. テストマトリックス

### 7.1 Track A テスト（クロスユーザー学習）

| # | 機能 | テスト名 | 種別 |
|---|------|----------|------|
| 1 | タイプ分類 | `test_classifyUserType_returnsCorrectType` | Unit |
| 2 | タイプ分類 | `test_classifyUserType_confidence_calculation` | Unit |
| 3 | タイプ分類 | `test_classifyUserType_empty_problems_returns_default` | Unit |
| 4 | タイプ分類 | `test_clearProblems_deletes_user_type_estimate` | Integration |
| 5 | タイプ別集計 | `test_aggregateTypeStats_updates_correctly` | Integration |
| 6 | タイプ推定API | `test_userTypeEndpoint_returns_estimate` | Integration |
| 7 | プロンプト注入 | `test_generateNudges_includes_cross_user_patterns` | Integration |

### 7.2 Track B テスト（Aniccaエージェント + TikTok）

| # | 機能 | テスト名 | 種別 |
|---|------|----------|------|
| 8 | Hook候補初期化 | `test_initHookLibrary_extracts_from_events` | Integration |
| 9 | エージェント投稿 | `test_anicca_agent_completes_posting_flow` | Integration |
| 10 | トレンド検索 | `test_search_trends_returns_valid_data` | Unit |
| 11 | 画像生成 | `test_generate_image_returns_url` | Unit |
| 12 | 画像評価 | `test_evaluate_image_rejects_low_quality` | Unit |
| 13 | エージェント再試行 | `test_agent_retries_image_on_rejection` | Integration |
| 14 | メトリクス取得 | `test_fetchMetrics_apify_updates_hook_candidates` | Integration |

### 7.3 Track C テスト（学習ループ統合）

| # | 機能 | テスト名 | 種別 |
|---|------|----------|------|
| 15 | wisdom判定 | `test_wisdomExtractor_identifies_cross_channel_patterns` | Unit |
| 16 | Hook選定 | `test_hookSelector_prioritizes_tiktok_high_performers` | Unit |
| 17 | Hook選定 | `test_hookSelector_thompson_sampling_balance` | Unit |
| 18 | cold start | `test_coldStart_newUser_tapRate_within_threshold` | Integration |

---

## 8. iOS側変更

### 8.1 1.5.0でのiOS変更（なし）

1.5.0はバックエンド + Python中心の変更。iOS側の変更は不要。

| 項目 | 変更 | 理由 |
|------|------|------|
| UIの変更 | なし | バックエンドでタイプ別パターンを処理 |
| 新規APIコール | なし | 既存の `/api/mobile/nudge/today` で十分 |
| Feature Flag | なし | バックエンドで制御 |

### 8.2 後方互換性

| バージョン | 対応 |
|-----------|------|
| 1.3.0以前 | 既存API維持、新フィールドは無視 |
| 1.4.0 | `scheduledTime` 対応済み |
| 1.5.0 | iOS変更なし（バックエンドのみ） |

---

## 9. ユーザーGUI作業

### 9.1 実装前（必須）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | TikTok新アカウント作成（EN） | TikTokアプリで新規アカウント作成 | アカウントID |
| 2 | Blotato接続 | Blotato Dashboard → Add Account → TikTok | Blotato Account ID |
| 3 | Apify Actor設定 | apify.com → Actors → clockworks/tiktok-scraper | Actor ID |
| 4 | GitHub Secrets設定 | repo Settings → Secrets → 7つ追加 | - |
| 5 | Exa API Key取得 | exa.ai → Dashboard → API Keys | EXA_API_KEY |
| 6 | Fal.ai API Key確認 | fal.ai → Dashboard → API Keys | FAL_API_KEY |
| 7 | OpenAI API Key確認 | platform.openai.com → API Keys | OPENAI_API_KEY |
| 8 | Blotato API Key確認 | blotato.com → Settings → API | BLOTATO_API_KEY |

**GitHub Secrets 一覧**:

| Secret名 | 取得元 |
|----------|--------|
| `OPENAI_API_KEY` | OpenAI Dashboard |
| `BLOTATO_API_KEY` | Blotato Settings |
| `FAL_API_KEY` | Fal.ai Dashboard |
| `EXA_API_KEY` | Exa Dashboard |
| `APIFY_API_TOKEN` | Apify Settings |
| `API_BASE_URL` | Railway Staging URL |
| `API_AUTH_TOKEN` | バックエンド管理用トークン |

### 9.2 実装後（確認）

| # | タイミング | タスク | 確認項目 |
|---|-----------|--------|---------|
| 1 | Track A完了後 | Staging APIでタイプ推定確認 | `GET /api/mobile/user-type` が正しいタイプを返す |
| 2 | Track B完了後 | GitHub Actions手動実行 | TikTokに画像1枚が投稿される |
| 3 | Track B完了後 | 24時間後にメトリクス確認 | tiktok_postsにメトリクスが入っている |
| 4 | Track C完了後 | wisdom判定確認 | hook_candidatesに `is_wisdom = true` が出る |

---

## 10. 実行手順

### 10.1 環境変数設定

```bash
# バックエンド（Railway）
DATABASE_URL=xxx
OPENAI_API_KEY=xxx

# GitHub Actions（Secrets）
OPENAI_API_KEY=xxx
BLOTATO_API_KEY=xxx
FAL_API_KEY=xxx
EXA_API_KEY=xxx
APIFY_API_TOKEN=xxx
API_BASE_URL=xxx
API_AUTH_TOKEN=xxx
```

### 10.2 DBマイグレーション順序

```bash
# 1. Track A のテーブル作成
cd apps/api
npx prisma migrate dev --create-only --name 1_5_0_user_type_and_type_stats
# → 生成されたSQLにCHECK制約、GENERATED ALWAYS ASを手動追記（db-schema-spec.md参照）
npx prisma migrate dev

# 2. Track B のテーブル作成
npx prisma migrate dev --create-only --name 1_5_0_hook_candidates_and_tiktok_posts
# → 生成されたSQLにCHECK制約、GIN Index、Partial Indexを手動追記
npx prisma migrate dev

# 3. Track C のテーブル作成
npx prisma migrate dev --create-only --name 1_5_0_wisdom_patterns
# → 生成されたSQLにCHECK制約、GIN Indexを手動追記
npx prisma migrate dev

# 4. 制約確認
npx prisma db execute --stdin <<< "SELECT conname FROM pg_constraint WHERE conname LIKE 'chk_%';"
```

### 10.3 Cronジョブ設定

| ジョブ | 場所 | スケジュール | 説明 |
|--------|------|------------|------|
| aggregateTypeStats | Railway Cron | `0 21 * * *` | 毎日6:00 JST |
| Anicca Daily Post | GitHub Actions | `0 0 * * *` | 毎日9:00 JST |
| Fetch Metrics | GitHub Actions | `0 1 * * *` | 毎日10:00 JST |
| extractWisdom | Railway Cron | `0 22 * * 0` | 毎週日曜7:00 JST |

### 10.4 テスト実行

```bash
# Track A テスト（Node.js）
cd apps/api && npm test -- --grep "userType|typeStats|crossUser"

# Track B テスト（Python）
cd scripts/anicca-agent && python -m pytest tests/

# エージェント手動テスト（dry-run）
cd scripts/anicca-agent && python anicca_tiktok_agent.py --dry-run
```

### 10.5 段階的ロールアウト

| フェーズ | 対象 | 確認項目 |
|---------|------|---------|
| 1 | Staging環境 | 全テストPASS |
| 2 | GitHub Actions dry-run | エージェントがツールを使って画像生成まで完了 |
| 3 | TikTok初回投稿 | 実際に投稿が表示される |
| 4 | Production（new users 10%） | cold start改善の初期兆候 |
| 5 | Production（全ユーザー） | 受け入れ条件4項目を達成 |

---

## 11. Track A 実装判断（2026-01-28 確定）

Specとコードベースの不整合を調査し、ベストプラクティス検索に基づき以下を確定した。

### 11.1 オンボーディングルート統合

| 項目 | 決定 |
|------|------|
| **方針** | `PUT /mobile/profile`（既存）に分類トリガーを追加。新規エンドポイント不要 |
| **根拠** | iOS変更なし制約（Spec Section 8）、REST原則（リソース更新時の副作用）、A6+A7を1箇所で実装可能 |
| **影響** | Spec Section 5.1 の「A6: オンボーディング完了時」と「A7: プロフィール更新時」を `profile.js` の PUT ハンドラ内に統合 |

**実装箇所**: `apps/api/src/routes/mobile/profile.js` の `PUT /` ハンドラ末尾

```javascript
// upsertProfile() の後に追加
const struggles = profileData.struggles || profileData.problems || [];
if (struggles.length > 0) {
  await userTypeService.classifyAndSave(userId, struggles);
} else {
  await userTypeService.deleteEstimate(userId);
}
```

**Spec Section 5.1 タスクへの影響**:

| タスク | 変更 |
|--------|------|
| A6 (オンボーディング完了時) | `profile.js` PUT ハンドラに統合（独立ファイルは作らない） |
| A7 (プロフィール更新時) | 同上（A6と同じコードパスで処理） |

### 11.2 Problems データソース

| 項目 | 決定 |
|------|------|
| **方針** | `mobile_profiles.profile->'struggles'` / `profile->'problems'` を使用 |
| **根拠** | `generateNudges.js` と同一パターン（`COALESCE(struggles, problems)`）で一貫性確保 |
| **注意** | `PUT /mobile/profile` のコンテキストでは `profileData.struggles || profileData.problems` で取得可能（DBクエリ不要） |

### 11.3 Prisma vs Raw SQL（ハイブリッド）

| 項目 | 決定 |
|------|------|
| **方針** | CRUD操作 = Prisma、集計/Generated Column読み取り = Raw SQL |
| **根拠** | コードベースで既に混在（新規ルート=Prisma、generateNudges=raw SQL）。Prisma Issue #6368: GENERATED ALWAYS AS未サポート |

| 操作 | 方式 | 理由 |
|------|------|------|
| `userTypeService` UPSERT/DELETE | Prisma | 単純CRUD、型安全 |
| `GET /api/mobile/user-type` findUnique | Prisma | 単純読み取り |
| `aggregateTypeStats.js` 集計 | Raw SQL (`query()`) | 複雑なJOIN+GROUP BY、パフォーマンス重要 |
| `type_stats` の `tap_rate`/`thumbs_up_rate` 読み取り | `prisma.$queryRaw` | GENERATED COLUMNはPrismaモデルに定義不可 |
| `generateNudges.js` タイプ別パターン取得 | Raw SQL | 既存パターンとの一貫性 |

**Railway vs Supabase**: この複雑さはPrismaのORM制限が原因であり、PostgreSQLホスティングプロバイダ（Railway/Supabase）に依存しない。CHECK制約、GENERATED ALWAYS AS、Partial Index、GIN IndexはいずれもPrisma未サポートであり、どのプロバイダでも手動DDL追記が必要。DB移行は1.5.0スコープ外。

### 11.4 Profile モデル relation 追加

| 項目 | 決定 |
|------|------|
| **方針** | `schema.prisma` の `Profile` モデルに `userTypeEstimate UserTypeEstimate?` を追加 |
| **根拠** | Prismaの双方向relation定義要件。`UserTypeEstimate` が `@relation(fields: [userId], references: [id])` を持つため必須 |

### 11.5 A8 バックフィルスクリプト

| 項目 | 決定 |
|------|------|
| **方針** | Track A に含める。実装順序は最後（A7の後） |
| **根拠** | バックフィルなしだと `aggregateTypeStats` ジョブの集計データがゼロのまま |
| **実行タイミング** | リリース後に1回 `node scripts/backfill-user-types.js` を手動実行 |
| **バッチ処理** | 200件ずつカーソルベースでバッチ UPSERT（1件ずつは禁止、10-50倍遅い） |
| **並行実行防止** | `pg_try_advisory_lock(150002)` で排他制御 |

### 11.6 データ空時の generateNudges.js 挙動

| 項目 | 決定 |
|------|------|
| **方針** | `type_stats` にデータがない場合、Cross-User Patternsプロンプトセクションを完全省略 |
| **根拠** | Google Context Engineering: 「コンテキストウィンドウは不動産。無意味な情報で埋めるな」。空統計を渡すとLLMが誤解釈するリスク |

```javascript
// generateNudges.js 内の実装パターン
const typeStats = await getTypeStatsForUser(userType);
if (typeStats && typeStats.length > 0) {
  prompt += buildCrossUserPatternsSection(userType, typeStats);
}
// typeStats が空なら従来通りのプロンプト（グレースフルデグラデーション）
```

### 11.7 aggregateTypeStats 集計対象

| 項目 | 決定 |
|------|------|
| **方針** | `nudge_events.state->>'user_type'` が記録済みのイベントのみ集計。初期ゼロスタート |
| **根拠** | 旧イベントには `user_type` がないため帰属タイプ不明。遡及推定は統計の信頼性を下げる |

**想定タイムライン**:

| 時点 | type_stats の状態 | Cross-User Patterns |
|------|-------------------|---------------------|
| リリース直後 | 空 | プロンプト省略（11.6適用） |
| 1日後 | aggregateTypeStats初回実行 → 初期データ | サンプルサイズ < 10 → まだ省略 |
| 1-2週間後 | 有効パターン蓄積 | プロンプト注入開始 |

### 11.8 Track A 確定タスク順序

Section 5.1 のタスクを11.1〜11.7の決定に基づき更新:

| # | タスク | ファイル | 変更点 |
|---|--------|----------|--------|
| A5 | DBマイグレーション | `prisma/migrations/` | db-schema-spec Section 2 + **Section 6 のレビュー指摘を反映**（下記参照） |
| A1 | userTypeService.js | `services/userTypeService.js`（新規） | Prisma使用（Section 11.3） |
| A2 | GET /api/mobile/user-type | `routes/mobile/userType.js`（新規） | db-schema-spec Section 4 の4ケース実装 |
| A6+A7 | 分類トリガー（統合） | `routes/mobile/profile.js`（修正） | PUT ハンドラに統合（Section 11.1） |
| A3 | aggregateTypeStats.js | `jobs/aggregateTypeStats.js`（新規） | Raw SQL + **advisory lock**（db-schema-spec Section 6.1）、user_type記録済みのみ（Section 11.7） |
| A4 | generateNudgesにパターン注入 | `jobs/generateNudges.js`（修正） | データ空時は省略（Section 11.6） |
| A8 | バックフィルスクリプト | `scripts/backfill-user-types.js`（新規） | **バッチ200件 + advisory lock**（Section 11.5） |

#### A5 マイグレーションに含めるレビュー指摘事項

db-schema-spec Section 6（PostgreSQLベストプラクティスレビュー）の指摘を A5 マイグレーションに反映する:

| # | 指摘 | 重要度 | 対応 |
|---|------|--------|------|
| 1 | `nudge_events` JSONB パスのインデックス追加 | CRITICAL | マイグレーションSQLに `idx_nudge_events_domain_user_type`, `idx_nudge_events_domain_hook` を追加 |
| 2 | `nudge_outcomes.nudge_event_id` の FK インデックス追加 | HIGH | マイグレーションSQLに `idx_nudge_outcomes_event_id` を追加 |
| 3 | `type_stats` カウントカラムを BIGINT に変更 | MEDIUM | DDL定義で INT → BIGINT に変更 |
| 4 | `hook_candidates.target_problem_types` GIN インデックス追加 | MEDIUM | マイグレーションSQLに追加（Track B のマイグレーション時） |
| 5 | Raw SQL UPDATE に `updated_at = NOW()` を明示 | MEDIUM | aggregateTypeStats, バックフィル の全 UPDATE に適用 |
