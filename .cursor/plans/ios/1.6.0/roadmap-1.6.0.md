# 1.6.0 ロードマップ — One Buddha 統合

## ビジョン

**TikTok Agent と App Nudge を「One Buddha」として統合する。**

苦しんでいる人がどこにいても — TikTok、アプリ内、X — 同じ「仏陀」が最適なメッセージを届ける。プラットフォームは手段に過ぎない。

## ユーザー体験への影響

| 変更 | Before | After |
|------|--------|-------|
| TikTokで効いたフック | TikTokでのみ学習 | アプリNudgeにも反映 |
| アプリで効いたメッセージ | アプリでのみ学習 | TikTok投稿にも活用 |
| Nudge頻度 | 固定5回/日/問題 | **Aniccaが動的に決定** |
| X (Twitter) | なし | テキストフックの高速検証 |

## 優先度付きタスクリスト

### P0: 必須（1.6.0の核心）

| # | タスク | 内容 | UX影響 |
|---|--------|------|--------|
| 1 | **データ統合層** | TikTok metrics + App tap_rate を統合する共通スキーマ | 全プラットフォームで学習が加速 |
| 2 | **Commander Agent設計** | 統合エージェントのアーキテクチャ。サブエージェント(TikTok/App/X)への指令 | - |
| 3 | **Thompson Sampling + LLM併用** | TSが「何が効く」、LLMが「なぜ効く」を担当する設計 | より精度の高いフック選択 |
| 4 | **新フック生成→DB保存** | エージェントが作った新フックをDBに保存してTSループに入れる | 学習が止まらない |

### P1: 高優先度

| # | タスク | 内容 | UX影響 |
|---|--------|------|--------|
| 5 | **X (Twitter) Agent** | テキストのみ投稿。Apify不要、API直接。1日10投稿可能 | フック検証速度10倍 |
| 6 | **動的Nudge頻度** | Aniccaが「今日は10回」「今日は2回」を判断 | ユーザーごとの最適化 |
| 7 | **Cross-Platform Learning** | Xで効いたフック→TikTok昇格、TikTokで効いた→App Nudge適用 | プラットフォーム横断学習 |

### P2: 中優先度

| # | タスク | 内容 | UX影響 |
|---|--------|------|--------|
| 8 | **LLMフック分析** | 「なぜこのフックが効いたか」を推論して新フック案を生成 | フックの質が向上 |
| 9 | **時間帯学習** | 曜日×時間帯別の効果を学習 | 最適タイミング精度向上 |
| 10 | **ペルソナ別学習** | 問題タイプだけでなく、年齢・性別・行動パターン別に学習 | パーソナライズ精度向上 |

---

## アーキテクチャ案

```
┌──────────────────────────────────────────────────┐
│            ANICCA COMMANDER                       │
│                                                   │
│  統合データレイヤー                                │
│  - TikTok metrics (view/like/share/comment)       │
│  - App metrics (tap_rate/feedback/session)        │
│  - X metrics (impression/like/retweet/reply)      │
│                                                   │
│  統合学習エンジン                                  │
│  - Thompson Sampling (何が効くか - 数学的)         │
│  - LLM Analysis (なぜ効くか - 推論)               │
│                                                   │
│  判断: 何を、誰に、いつ、どのプラットフォームで     │
├──────────┬───────────┬──────────┬─────────────────┤
│ TikTok   │ App Nudge │ X        │ (将来: Voice等)  │
│ Sub-agent│ Sub-agent │ Sub-agent│                  │
└──────────┴───────────┴──────────┴─────────────────┘
```

---

## X Agent 仕様案

### なぜXか

| 比較項目 | TikTok | X |
|---------|--------|---|
| コンテンツ形式 | 画像+キャプション（Fal.ai必要） | テキストのみ（即座に投稿可能） |
| データ取得 | Apify経由（25時間遅延） | API直接（リアルタイム） |
| 投稿頻度 | 1日1投稿（コスト・品質管理） | **1日10-20投稿可能** |
| 学習速度 | 遅い | **10倍速** |

### X→TikTok昇格パイプライン

```
1. Xでフックをテキスト投稿（1日10個）
2. 数時間後にimpression/like取得
3. 上位フックをTikTok用に画像化
4. TikTokに投稿
5. 翌日メトリクス取得
6. Thompson Sampling更新
```

---

## 動的Nudge頻度 仕様案

### 現状の問題

`ProblemType.swift` に **5回/日/問題** がハードコード。Aniccaに判断権がない。

### 理想

```swift
// Before (ハードコード)
var notificationSchedule: [(Int, Int)] {
    return [(20, 30), (21, 30), (22, 30), (23, 30), (7, 30)]  // 固定5回
}

// After (Aniccaが決定)
// サーバーから /api/nudge/schedule を取得
// Aniccaが「今日は8回」「今日は3回」を判断
```

### 判断ロジック案

| 入力 | 判断 |
|------|------|
| 昨日のタップ率低い | 回数増やす or トーン変える |
| 連続3日無視 | 一時停止して次の日リセット |
| 高タップ率 | 現状維持 or 少し減らす |
| 曜日・時間帯 | 効果が高い時間に集中 |

---

## 新フック生成→DB保存 仕様案

### 現状の問題

エージェントが新フックを作っても:
- 保存するツールがない
- `hook_candidate_id` がないのでThompson Samplingに入らない
- → 学習されない、一度きりで消える

### 解決案

1. **新ツール追加**: `create_hook_candidate`
2. **DBに保存**: 新しい `hook_candidate` レコードを作成
3. **IDを返す**: 投稿時に `hook_candidate_id` としてリンク
4. **Thompson Samplingに入る**: 翌日のメトリクスで学習

```python
# tools.py に追加
def create_hook_candidate(text: str, tone: str, problem_types: list) -> dict:
    """
    エージェントが考えた新しいフックをDBに保存。
    Thompson Samplingのフィードバックループに入る。
    """
    result = api.create_hook_candidate(text, tone, problem_types)
    return {"success": True, "hook_candidate_id": result["id"]}
```

---

## 1.7.0 以降との接続

| バージョン | 追加要素 | 1.6.0との関係 |
|-----------|---------|--------------|
| **1.7.0** | 合成ユーザーシミュレーション | Cold Start解決。新フックを実投稿前に仮想テスト |
| **1.8.0** | 音声Nudge | Commander Agentに Voice Sub-agent を追加 |
| **1.9.0** | Deep Dive統合 | 根本原因分析をフック生成に活用 |

---

## 実装順序（推奨）

```
Week 1-2: データ統合層 + Thompson Sampling + LLM併用設計
    ↓
Week 3-4: X Agent実装（高速フック検証開始）
    ↓
Week 5-6: 新フック生成→DB保存ツール
    ↓
Week 7-8: Commander Agent + Cross-Platform Learning
    ↓
Week 9-10: 動的Nudge頻度（iOS側変更必要）
```

---

## 成功指標

| 指標 | 1.5.0 | 1.6.0目標 |
|------|-------|----------|
| フック検証速度 | 1/日 | **10/日** (X併用) |
| 学習データソース | 2 (TikTok, App) | **3** (+ X) |
| Nudge頻度決定 | 固定 | **動的** |
| 新フック学習 | なし | **自動** |
| プラットフォーム横断学習 | なし | **統合** |
