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
| 成功定義 | 投稿hookの `engagementRate > 0.05`（0-1 ratio; 5% = 0.05。closed-loop-ops `executeAnalyzeEngagement` の `isHighEngagement` 判定と同一） |
| 失敗定義 | 投稿hookが表示されたが `engagementRate <= 0.05` |
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

### フィードバック経路（x-poster → trend-hunter）

> **P0 #16 解消**: trend-hunter の Bandit 状態を更新するデータソースと経路を定義

```
x-poster が hook を投稿
    ↓
closed-loop-ops: executeAnalyzeEngagement()
    ↓ engagementRate > 0.05 → isHighEngagement = true  (0-1 ratio; 0.05 = 5%)
    ↓ hookCandidate.xEngagements += 1 (or tiktokEngagements)
    ↓
Railway DB: hook_candidates テーブル更新
    ↓
trend-hunter: 次回実行時に Railway API GET /api/agent/hooks で取得
    ↓ 各 hook の targetProblemTypes（配列）をイテレート
    ↓ engaged = hook.xEngagementRate > 0.05（0-1 ratio; DB stores ratio, not percentage）
    ↓
updateBandit(banditState, problemType, engaged)
```

**ProblemType レベル集計ロジック:**

```javascript
// trend-hunter が v2 実行時に Railway DB から Bandit 状態を再計算
// HookFromAPI 型（06-test-matrix.md 定義）を使用
async function syncBanditFromDB(banditState) {
  const hooks = await railwayApiClient.getHooks();
  // 各 ProblemType ごとに成功/失敗をカウント
  // hooks.hooks は HookFromAPI[] — フラットフィールド構造
  for (const hook of hooks.hooks) {
    // hook.targetProblemTypes は配列 — 各 ProblemType に対して bandit 更新
    for (const pt of hook.targetProblemTypes) {
      if (!banditState[pt]) continue;
      // xSampleSize > 0 = 投稿実績あり（未投稿 hook はスキップ）
      const totalSamples = (hook.xSampleSize || 0) + (hook.tiktokSampleSize || 0);
      if (totalSamples > 0) {
        // エンゲージメント率の加重平均で判定（5.0% 閾値は executeAnalyzeEngagement と同一）
        const weightedRate = hook.xSampleSize > 0
          ? hook.xEngagementRate  // X のエンゲージメント率を優先
          : hook.tiktokLikeRate;
        const engaged = weightedRate > 0.05;  // 0-1 ratio (0.05 = 5%); DB stores ratio, not percentage
        updateBandit(banditState, pt, engaged);
      }
    }
  }
  return banditState;
}
```

**実行タイミング**: v2 モード時、トレンド収集の前に `syncBanditFromDB()` を呼ぶ。

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

