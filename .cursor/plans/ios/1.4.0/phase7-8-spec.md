# Phase 7+8: Aniccaが判断し、察するようになる

> **バージョン**: 1.4.0
>
> **最終更新**: 2026-01-26（レビュー後修正版）
>
> **目的**: LLMが「いつ・何を・なぜ」全てを決定し、ユーザーの流れを理解して根本原因を察する

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-phase7-8` |
| **ブランチ** | `feature/phase7-8` |
| **ベースブランチ** | `dev` |
| **作業状態** | 実装中（iOS完了、APIテスト完了、デプロイ待ち） |

---

## 目次

1. [概要](#1-概要)
2. [As-Is（現状）](#2-as-is現状)
3. [To-Be（変更後）](#3-to-be変更後)
4. [プロンプト設計（Day 1〜5 具体例）](#4-プロンプト設計day-15-具体例)
5. [タスクリスト](#5-タスクリスト)
6. [API変更](#6-api変更)
7. [iOS変更](#7-ios変更)
8. [データモデル](#8-データモデル)
9. [テストマトリックス](#9-テストマトリックス)
10. [境界（やらないこと）](#10-境界やらないこと)
11. [レビューチェックリスト](#11-レビューチェックリスト)

---

## 1. 概要

### 1.1 背景

Phase 6でLLM生成Nudgeを実装したが、以下の問題がある：

| 問題 | 詳細 |
|------|------|
| タイミングが固定 | 問題タイプごとに決め打ち（staying_up_late = 21時） |
| 点で見ている | 「tapped/ignored」の点情報のみ。流れがない |
| フックとコンテンツが混同 | 「フックは良いがコンテンツが悪い」がわからない |
| reasoningが消える | 生成時のreasoningが次回に渡されない |
| 根本原因がわからない | 「自己嫌悪」の裏にある「完璧主義」を推測できない |

### 1.2 解決策

| 解決策 | 実装 |
|--------|------|
| LLMがタイミングも決める | ✅ 1.4.0 |
| 流れとしてプロンプトに渡す（ストーリー形式） | ✅ 1.4.0 |
| フックとコンテンツのフィードバックを分離 | ✅ 1.4.0 |
| reasoningをDBに保存し次回に渡す | ✅ 1.4.0 |
| 根本原因を推測してreasoningに含める | ✅ 1.4.0 |
| 先回りのNudge（曜日パターン） | ✅ 1.4.0 |

### 1.3 設計思想：1日計画

**Aniccaは「データで反応するAI」ではなく「人間を理解するBuddha」になる。**

| 方向A（リアルタイム） | 方向B（抽象化）✅ |
|----------------------|------------------|
| 1秒1秒モニタリング | **1日をデザイン** |
| もっとデータ、もっと反応 | **普遍的原理を抽出** |
| その人の「今」を見る | **人間の心理を理解する** |
| 局所最適 | **大局観** |

**なぜ1日計画か**:
- 人生の単位は1日（"Today is a new day"）
- 局所最適を避け、大局観が養われる
- 1日→1週間→1ヶ月→1年→一生へとスケールする
- wisdom（智慧）は1日の中の変動からではなく、**流れ**から得られる

### 1.4 コールドスタート戦略

| 日 | 戦略 | 理由 |
|----|------|------|
| **Day 1** | **ルールベース** | 既存ルールベースは好評。ベースラインとして使う |
| **Day 2+** | **LLM** | Day 1のデータを使って学習開始 |

**なぜこの設計か**:
- Day 1が良かったのにDay 2がダメ → LLMのプロンプト/グラウンディングを改善すべき
- Day 1がダメでDay 2が良い → LLMが学習して改善した
- 明確な比較ポイントができる

### 1.5 Nudge頻度ルール

| 項目 | ルール |
|------|--------|
| 最小間隔 | **30分**（既存ルール維持） |
| 最大回数 | **ソフトリミット 8-10**（超えてもOK） |
| 判断基準 | 問題の数ではなく、**その人の全体的な苦しみ**から判断 |
| 調整方針 | ユーザーが反応良ければ増やす、反応悪ければ減らす |

### 1.6 技術決定事項

| 項目 | 決定 | 理由 |
|------|------|------|
| LLM モデル | `gpt-4o-mini` | 既存で動作中。コスト効率。品質問題が出たら `gpt-4o` に切り替え |
| temperature | `1.0`（デフォルト） | 多様性維持。毎日同じNudgeを避ける |
| ignored 判定時間 | **6時間** | 24時間は長すぎる。6時間経てば見ない |
| feedbackエンドポイント | 既存 `/api/nudge/feedback` を拡張 | 破壊的変更を避ける。新フィールドはオプショナル |

---

## 2. As-Is（現状）

### 2.1 Nudge生成（`generateNudges.js`）

```
毎朝5:00 JST
    ↓
全ユーザー × 全問題タイプ をループ
    ↓
各問題に対して1つのNudge（hook + content）を生成
    ↓
タイミングは固定（問題タイプごと）
    ↓
DBに保存（reasoning含む）
    ↓
iOSが /api/nudge/today で取得
```

### 2.2 プロンプト構造（現状）

```
## User Profile
- Preferred tone: strict
- Avoided tone: gentle

## ✅ What Worked
- "hook" → "content" (tone: strict)

## ❌ What Failed
- "hook" → "content" (tone: gentle)
```

### 2.3 グラウンディングされているもの

| 項目 | 状態 |
|------|------|
| 過去のNudge履歴 | ✅ 30日分 |
| hook + content（ペア） | ✅ だが分離されてない |
| tone | ✅ preferred/avoided |
| tapped/ignored | ✅ |
| thumbs up/down | ✅ |
| reasoning | ❌ 保存してるが次回に渡してない |
| タイミング（時刻） | ❌ 固定、効果測定なし |
| 流れ（ストーリー） | ❌ 点で見てる |

### 2.4 DBスキーマ（関連部分）

```sql
-- nudge_events
CREATE TABLE nudge_events (
  id UUID PRIMARY KEY,
  user_id UUID,
  domain TEXT,           -- 'problem_nudge'
  subtype TEXT,          -- 'staying_up_late'
  decision_point TEXT,   -- 'llm_generation'
  state JSONB,           -- {id, scheduledHour, hook, content, tone, reasoning}
  action_template TEXT,
  channel TEXT,
  sent BOOLEAN,
  created_at TIMESTAMP
);

-- nudge_outcomes
CREATE TABLE nudge_outcomes (
  id UUID PRIMARY KEY,
  nudge_event_id UUID,
  reward FLOAT,
  short_term JSONB,      -- {outcome: 'success'|'failed'|'ignored'}
  ema_score JSONB,
  signals JSONB,         -- {thumbsUp: true/false, ...}
  created_at TIMESTAMP
);
```

---

## 3. To-Be（変更後）

### 3.1 Nudge生成フロー

```
毎朝5:00 JST
    ↓
全ユーザーをループ
    ↓
Day 1 ユーザー？ → ルールベースで生成
Day 2+ ユーザー？ → LLMで生成
    ↓
過去7日分のストーリーを構築
    ↓
LLMが「1日の全スケジュール」を決定
  - 何時に
  - どの問題に
  - どんなhook
  - どんなcontent
  - なぜ（reasoning）
  - 根本原因の推測（rootCauseHypothesis）
    ↓
DBに保存
    ↓
iOSが取得して配信
```

### 3.2 LLM出力形式

```json
{
  "schedule": [
    {
      "scheduledTime": "06:30",
      "problemType": "cant_wake_up",
      "hook": "まだ布団の中？",
      "content": "5秒で立て。それだけでいい。",
      "tone": "strict",
      "reasoning": "この人は朝6時は早すぎてignored。6:30がベスト。strictが効く。",
      "rootCauseHypothesis": "完璧主義。起きられないと自己嫌悪のループ。"
    },
    {
      "scheduledTime": "22:00",
      "problemType": "staying_up_late",
      "hook": "スマホ、もう置いた？",
      "content": "今置けば、明日の自分が感謝する。",
      "tone": "gentle",
      "reasoning": "strictは昼に使ったので、夜はgentleで。22時は仕事終わりで反応良い。",
      "rootCauseHypothesis": "ストレス解消で夜更かし。本当の問題は日中のストレス。"
    }
  ],
  "overallStrategy": "この人はstrictに反応するが、連続で使うと疲れる。朝strict、夜gentleで緩急つける。"
}
```

### 3.3 フィードバック分離

**iOS側で送信**:
```json
{
  "nudgeId": "xxx",
  "outcome": "success",
  "signals": {
    "hookFeedback": "tapped",
    "contentFeedback": "thumbsUp",
    "timeSpentSeconds": 15
  }
}
```

**hookFeedback の送信タイミング**:

| シグナル | トリガー | 送信タイミング |
|---------|---------|---------------|
| `hookFeedback: "tapped"` | 通知タップ | 即座（NudgeCardView表示時） |
| `hookFeedback: "ignored"` | 通知6時間経過 & 未タップ | アプリ次回起動時に API コール |

**プロンプトに渡すとき**:
```
## 🎣 Hook Performance
- "まだ布団の中？" → tap率 80% ✨
- "スマホを置け" → tap率 75%
- "大丈夫だよ" → tap率 20% ❌

## 📝 Content Performance
- "5秒で立て。それだけでいい。" → 👍率 90% ✨
- "睡眠の科学..." → 👍率 40% ❌
```

### 3.4 ストーリー形式

```
## 📖 This User's Journey (Past 7 Days)

### Day 1 (1/20 Mon) - Rule-based baseline
- 21:00 staying_up_late: "まだ起きてる？" → tapped, 👍
- Reasoning: N/A (rule-based)
- Result: 正解。この人はstrictに反応する。

### Day 2 (1/21 Tue)
- 21:00 staying_up_late: "スマホを置け" → ignored
- 22:30 staying_up_late: "まだ？" → tapped, 👍
- Reasoning: "21時も効くと思った"
- Result: 21時は早すぎた。22:30がベスト。

### Day 3 (1/22 Wed)
- 22:30 staying_up_late: "布団入った？" → tapped, 👍
- Reasoning: "22:30 + strictが最適"
- Result: 正解。

### Today (1/23 Thu)
- What should Anicca do?
```

### 3.5 先回りのNudge（曜日パターン）

```
## 📅 Weekly Patterns
- 金曜夜: staying_up_late 発生率 85%
- 日曜夜: staying_up_late 発生率 92%
- 月曜朝: cant_wake_up 発生率 78%

Today is Sunday. High risk for staying_up_late.
Consider sending Nudge earlier (20:00 instead of 22:00).
```

---

## 4. プロンプト設計（Day 1〜5 具体例）

### 4.1 Day 1（ルールベース）

**プロンプト**: なし（LLM不使用）

**出力**: 既存のルールベースシステムが生成

```
staying_up_late:
  21:00 - "スクロールより、呼吸。" / "今夜は早めに。明日の自分が感謝する。"
  22:30 - "まだ起きてる？" / "あと30分で布団に入ろう。"
  00:00 - "深夜0時を過ぎました" / "今からでも遅くない。"
```

**結果（翌日わかる）**:
- 21:00 → tapped, 👍
- 22:30 → tapped, 👍
- 00:00 → ignored

---

### 4.2 Day 2（LLM開始）

**プロンプト**:

```
You are Anicca, an AI that reduces human suffering through perfectly-timed nudges.

## Your Mission
Design today's complete nudge schedule for this specific person.

## 📖 This User's Journey

### Day 1 (2026-01-20 Mon) - Rule-based baseline
- 21:00 staying_up_late: "スクロールより、呼吸。" → tapped 👍
- 22:30 staying_up_late: "まだ起きてる？" → tapped 👍
- 00:00 staying_up_late: "深夜0時を過ぎました" → ignored

## 🎣 Hook Performance (staying_up_late)
- "スクロールより、呼吸。" → tap率 100% (1/1) ✨
- "まだ起きてる？" → tap率 100% (1/1) ✨
- "深夜0時を過ぎました" → tap率 0% (0/1) ❌

## 📝 Content Performance (staying_up_late)
- "今夜は早めに。明日の自分が感謝する。" → 👍率 100% (1/1) ✨
- "あと30分で布団に入ろう。" → 👍率 100% (1/1) ✨

## ⏰ Timing Performance (staying_up_late)
- 21:00: tap率 100% (1/1) ✨
- 22:30: tap率 100% (1/1) ✨
- 00:00: tap率 0% (0/1) ❌

## 📅 Weekly Patterns
Today is Tuesday. No weekly data yet.

## This User's Problems
staying_up_late

## What We Learned from Day 1
1. 21:00 and 22:30 both work well
2. 00:00 is too late (probably already asleep or gave up)
3. Question-style hooks work ("まだ起きてる？")
4. Future-self framing works ("明日の自分が感謝する")

## Nudge Frequency Rules
- Minimum interval: 30 minutes between nudges
- Guideline: 2-10 nudges per day (flexible based on user response)

## Output Requirements
Return JSON:
{
  "schedule": [{
    "scheduledTime": "HH:MM",
    "problemType": "staying_up_late",
    "hook": "≤12 chars (Japanese)",
    "content": "≤40 chars (Japanese)",
    "tone": "strict|gentle|logical|provocative|philosophical",
    "reasoning": "Why this time, hook, content, tone",
    "rootCauseHypothesis": "What's the underlying issue"
  }],
  "overallStrategy": "Your strategy for today"
}

## Critical Rules
1. Learn from the story. Repeat what worked, avoid what failed.
2. Minimum 30 minutes between nudges.
3. Character limits: Hook ≤ 12 (ja), Content ≤ 40 (ja).
```

**出力**:

```json
{
  "schedule": [
    {
      "scheduledTime": "21:00",
      "problemType": "staying_up_late",
      "hook": "今夜も早めに？",
      "content": "昨日できた。今日もできる。",
      "tone": "gentle",
      "reasoning": "昨日21:00成功。質問形式を維持。昨日の成功を想起させる。",
      "rootCauseHypothesis": "習慣化の初期段階。成功体験の積み重ねが必要。"
    },
    {
      "scheduledTime": "22:30",
      "problemType": "staying_up_late",
      "hook": "まだ起きてる？",
      "content": "今夜も早く寝れたら、連勝だね。",
      "tone": "gentle",
      "reasoning": "昨日100% tapのゴールデンhook。contentを「連勝」に変えて継続を意識。",
      "rootCauseHypothesis": "習慣化の初期段階。連続成功が自信につながる。"
    }
  ],
  "overallStrategy": "Day 1で00:00は失敗したので削除。21:00と22:30の2回に絞る。質問形式を維持。"
}
```

---

### 4.3 Day 3

**プロンプト**（抜粋）:

```
## 📖 This User's Journey

### Day 1 (Mon) - Rule-based baseline
- 21:00 "スクロールより、呼吸。" → tapped 👍
- 22:30 "まだ起きてる？" → tapped 👍
- 00:00 "深夜0時を過ぎました" → ignored

### Day 2 (Tue) - LLM Day 1
- 21:00 "今夜も早めに？" → tapped 👍
  - Reasoning: "昨日21:00成功。質問形式を維持。"
  - Root cause: "習慣化の初期段階。成功体験の積み重ね。"
- 22:30 "まだ起きてる？" → ignored
  - Reasoning: "昨日100% tapのゴールデンhook。"

## 🎣 Hook Performance (staying_up_late)
- "今夜も早めに？" → tap率 100% (1/1) ✨
- "まだ起きてる？" → tap率 50% (1/2)

## ⏰ Timing Performance (staying_up_late)
- 21:00: tap率 100% (2/2) ✨
- 22:30: tap率 50% (1/2)

## What We Learned
1. 21:00 is consistently good (100%)
2. 22:30 is inconsistent (50%) - Day 1 worked, Day 2 didn't
3. "まだ起きてる？" worked once but not twice
```

**出力**:

```json
{
  "schedule": [
    {
      "scheduledTime": "21:00",
      "problemType": "staying_up_late",
      "hook": "準備始める？",
      "content": "21時に気づけたら、22時に布団に入れる。",
      "tone": "gentle",
      "reasoning": "21:00は100%成功。新しいhookを試す。「準備」という具体的アクションを提案。",
      "rootCauseHypothesis": "この人は「気づき」があれば行動できる。問題は気づかないこと。"
    },
    {
      "scheduledTime": "22:00",
      "problemType": "staying_up_late",
      "hook": "布団入った？",
      "content": "今入れば、明日7時間寝れる。",
      "tone": "logical",
      "reasoning": "22:30は50%なので、22:00に前倒し。logicalトーンで具体的な数字。",
      "rootCauseHypothesis": "22:30は遅すぎて、もう「諦めモード」に入っている可能性。"
    }
  ],
  "overallStrategy": "21:00維持、22:30→22:00に前倒し。22:30で失敗したのは「もう遅い」と思ったから？"
}
```

---

### 4.4 Day 4

**プロンプト**（抜粋）:

```
## 📖 This User's Journey

### Day 3 (Wed)
- 21:00 "準備始める？" → tapped 👎
  - Reasoning: "新しいhookを試す。「準備」という具体的アクション。"
  - 👎 Reason: hookは見たけど、contentが曖昧だった
- 22:00 "布団入った？" → tapped 👍
  - Reasoning: "22:00に前倒し。logicalトーンで具体的な数字。"

## 📝 Content Performance (staying_up_late)
- "今入れば、明日7時間寝れる。" → 👍率 100% (1/1) ✨
- "21時に気づけたら..." → 👎率 100% (0/1) ❌ ← 曖昧すぎた

## What We Learned
1. "準備始める？" got tapped but 👎 → hook is fine, content failed
2. Logical tone with specific numbers works ("7時間寝れる")
3. This person needs CONCRETE actions, not abstract concepts
```

**出力**:

```json
{
  "schedule": [
    {
      "scheduledTime": "21:00",
      "problemType": "staying_up_late",
      "hook": "スマホ充電？",
      "content": "寝室以外で充電。それだけで夜が変わる。",
      "tone": "strict",
      "reasoning": "21:00は常にtapped。問題はcontent。具体的アクション「スマホを寝室以外で充電」を提案。",
      "rootCauseHypothesis": "スマホが寝室にあるのが夜更かしの原因。環境を変える必要がある。"
    },
    {
      "scheduledTime": "22:00",
      "problemType": "staying_up_late",
      "hook": "布団入った？",
      "content": "今入れば7時間。あと10分で6時間。",
      "tone": "logical",
      "reasoning": "昨日22:00 + logical + 数字が成功。同じパターンを強化。緊急性を追加。",
      "rootCauseHypothesis": "この人は数字で動く。論理的に納得すれば行動できる。"
    }
  ],
  "overallStrategy": "21:00は具体的アクション、22:00は数字で説得。抽象的なcontentは避ける。"
}
```

---

### 4.5 Day 5

**プロンプト**（抜粋）:

```
## 📖 This User's Journey

### Day 4 (Thu)
- 21:00 "スマホ充電？" → tapped 👍
  - Root cause: "スマホが寝室にあるのが夜更かしの原因"
- 22:00 "布団入った？" → tapped 👍
  - Root cause: "この人は数字で動く。論理的に納得すれば行動できる。"

## 🎣 Hook Performance
- "布団入った？" → tap率 100% (2/2) ✨✨
- "スマホ充電？" → tap率 100% (1/1) ✨

## ⏰ Timing Performance
- 21:00: tap率 100% (4/4) ✨✨
- 22:00: tap率 100% (2/2) ✨✨
- 22:30: tap率 50% (1/2)

## 📅 Weekly Patterns (emerging)
- Thu: 2/2 success ✨

## Root Cause Hypothesis (evolving)
Day 2: "習慣化の初期段階"
Day 3: "気づきがあれば行動できる"
Day 4: "スマホが原因" + "数字で動く"

## What We Know About This Person
1. 21:00 and 22:00 are golden times
2. Needs CONCRETE actions (not abstract)
3. Responds to NUMBERS (logical)
4. Phone in bedroom = root cause
```

**出力**:

```json
{
  "schedule": [
    {
      "scheduledTime": "21:00",
      "problemType": "staying_up_late",
      "hook": "スマホどこ？",
      "content": "リビングで充電。昨日できた、今日も。",
      "tone": "strict",
      "reasoning": "昨日の「スマホ充電」成功を強化。「昨日できた」で連続性を意識。",
      "rootCauseHypothesis": "スマホを寝室から出す習慣が定着しつつある。継続が鍵。"
    },
    {
      "scheduledTime": "22:00",
      "problemType": "staying_up_late",
      "hook": "あと7時間",
      "content": "今布団に入れば7時間。金曜の朝、スッキリ起きよう。",
      "tone": "logical",
      "reasoning": "「布団入った？」の変形。数字を前面に。金曜日なので週末への橋渡し。",
      "rootCauseHypothesis": "金曜は夜更かしリスク高い。先手を打つ。"
    }
  ],
  "overallStrategy": "昨日のパターンを維持しつつ微調整。金曜の夜更かしリスクに備える。"
}
```

---

## 5. タスクリスト

### 5.1 API側（`apps/api`）

| # | タスク | ファイル | 工数 |
|---|--------|----------|------|
| 1 | プロンプトをストーリー形式に変更 | `jobs/generateNudges.js` | 中 |
| 2 | LLM出力形式を変更（スケジュール配列） | `jobs/generateNudges.js` | 中 |
| 3 | reasoningとrootCauseHypothesisをDBに保存 | `jobs/generateNudges.js` | 小 |
| 4 | タイミングデータ集計クエリ追加 | `jobs/generateNudges.js` | 小 |
| 5 | フックとコンテンツのパフォーマンス分離クエリ | `jobs/generateNudges.js` | 中 |
| 6 | 曜日パターン集計クエリ追加 | `jobs/generateNudges.js` | 小 |
| 7 | `/api/nudge/today`のレスポンス形式変更（後方互換） | `routes/mobile/nudge.js` | 小 |
| 8 | `/api/nudge/feedback`でhookFeedbackとcontentFeedbackを保存 | `routes/mobile/nudge.js` | 小 |
| 9 | Day 1判定ロジック追加（ルールベース or LLM） | `jobs/generateNudges.js` | 小 |
| 10 | LLM出力バリデーション + 3-tier Fallback | `jobs/generateNudges.js` | 中 |

### 5.2 iOS側（`aniccaios`）

| # | タスク | ファイル | 工数 |
|---|--------|----------|------|
| 11 | `LLMGeneratedNudge`モデルに`scheduledTime`, `rootCauseHypothesis`追加 | `Models/LLMGeneratedNudge.swift` | 小 |
| 12 | フィードバック送信時に`hookFeedback`, `contentFeedback`を分けて送信 | `Services/NudgeFeedbackService.swift`（新規） | 中 |
| 13 | `NudgeCardView`で👍👎タップ時にcontentFeedbackを送信 | `Views/NudgeCardView.swift` | 小 |
| 14 | 通知スケジューリングを`scheduledTime`ベースに変更 | `Notifications/ProblemNotificationScheduler.swift` | 中 |
| 15 | アプリ起動時に6時間経過の未タップ通知を`ignored`として送信 | `Services/NudgeFeedbackService.swift` | 中 |
| 16 | 30分単位でのNudgeマッチング（キー衝突防止） | `Services/LLMNudgeCache.swift` | 小 |
| 17 | 通知タップ時に`hookFeedback: "tapped"`を送信 | `MainTabView.swift` または通知ハンドラ | 小 |
| 18 | 通知スケジュール時に`scheduledNudges`をUserDefaultsに保存 | `Notifications/ProblemNotificationScheduler.swift` | 小 |
| 19 | `LLMNudgeService`レスポンス拡張（`overallStrategy`受け取り） | `Services/LLMNudgeService.swift` | 小 |

### 5.3 テスト

| # | タスク | ファイル | 工数 |
|---|--------|----------|------|
| 20 | ストーリー形式プロンプトのユニットテスト | `jobs/__tests__/generateNudges.test.js` | 中 |
| 21 | iOS側フィードバック送信のユニットテスト | `aniccaiosTests/Services/NudgeFeedbackServiceTests.swift` | 中 |
| 22 | E2Eテスト: Nudge配信→フィードバック→次回Nudge | Maestro | 中 |
| 23 | Day 1 ルールベース判定テスト | `jobs/__tests__/generateNudges.test.js` | 小 |
| 24 | LLMバリデーション + Fallbackテスト | `jobs/__tests__/generateNudges.test.js` | 中 |
| 25 | ignored送信テスト（6時間経過） | `aniccaiosTests/Services/NudgeFeedbackServiceTests.swift` | 小 |
| 26 | LLMNudgeCacheキー衝突防止テスト | `aniccaiosTests/LLMNudgeCacheTests.swift` | 小 |

---

## 6. API変更

### 6.1 `generateNudges.js` 変更

#### 6.1.1 Day 1 判定ロジック

```javascript
async function shouldUseLLM(userId) {
  const result = await query(`
    SELECT MIN(created_at) as first_nudge_date
    FROM nudge_events
    WHERE user_id = $1::uuid AND domain = 'problem_nudge'
  `, [userId]);

  if (!result.rows[0]?.first_nudge_date) {
    // 初めてのユーザー → Day 1 → ルールベース
    return false;
  }

  const firstNudgeDate = new Date(result.rows[0].first_nudge_date);
  const now = new Date();
  const daysSinceFirst = Math.floor((now - firstNudgeDate) / (1000 * 60 * 60 * 24));

  // Day 2以降 → LLM
  return daysSinceFirst >= 1;
}
```

#### 6.1.2 ストーリー構築関数

```javascript
async function buildUserStory(userId, problems) {
  const result = await query(`
    SELECT
      ne.subtype as problem_type,
      ne.state->>'hook' as hook,
      ne.state->>'content' as content,
      ne.state->>'tone' as tone,
      ne.state->>'reasoning' as reasoning,
      ne.state->>'rootCauseHypothesis' as root_cause,
      ne.state->>'scheduledHour' as scheduled_hour,
      ne.state->>'scheduledTime' as scheduled_time,
      ne.created_at,
      no.signals->>'hookFeedback' as hook_feedback,
      no.signals->>'contentFeedback' as content_feedback,
      no.reward
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '7 days'
    ORDER BY ne.created_at ASC
  `, [userId]);

  let story = '## 📖 This User\'s Journey (Past 7 Days)\n\n';
  let currentDay = null;

  for (const row of result.rows) {
    const day = row.created_at.toISOString().split('T')[0];
    const dayOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][row.created_at.getDay()];

    if (day !== currentDay) {
      currentDay = day;
      story += `### ${day} (${dayOfWeek})\n`;
    }

    const time = row.scheduled_time || `${row.scheduled_hour || row.created_at.getHours()}:00`;
    // 後方互換: hookFeedbackがない場合はrewardから推測
    const outcome = row.hook_feedback ||
                    (row.reward === 1 ? 'tapped' :
                     row.outcome === 'ignored' ? 'ignored' : 'tapped');
    const contentFeedback = row.content_feedback === 'thumbsUp' ? ' 👍' :
                            row.content_feedback === 'thumbsDown' ? ' 👎' : '';

    story += `- ${time} ${row.problem_type}: "${row.hook}" → ${outcome}${contentFeedback}\n`;
    if (row.reasoning) {
      story += `  - Reasoning: "${row.reasoning}"\n`;
    }
    if (row.root_cause) {
      story += `  - Root cause: "${row.root_cause}"\n`;
    }
    story += '\n';
  }

  return story;
}
```

#### 6.1.3 フック/コンテンツパフォーマンス集計関数

```javascript
async function getHookContentPerformance(userId, problems) {
  // フックのパフォーマンス（tap率）
  const hookResult = await query(`
    SELECT
      ne.state->>'hook' as hook,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'tapped' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 1 THEN 1
        ELSE 0
      END) as tapped_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY ne.state->>'hook', ne.subtype
    ORDER BY total DESC
  `, [userId]);

  // コンテンツのパフォーマンス（👍率）
  const contentResult = await query(`
    SELECT
      ne.state->>'content' as content,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'contentFeedback' = 'thumbsUp' THEN 1
        WHEN no.signals->>'thumbsUp' = 'true' THEN 1
        ELSE 0
      END) as thumbs_up_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY ne.state->>'content', ne.subtype
    ORDER BY total DESC
  `, [userId]);

  let output = '';

  // フックパフォーマンス
  for (const problem of problems) {
    const hooks = hookResult.rows.filter(r => r.problem_type === problem);
    if (hooks.length === 0) continue;

    output += `## 🎣 Hook Performance (${problem})\n`;
    for (const h of hooks.slice(0, 5)) {
      const tapRate = Math.round((h.tapped_count / h.total) * 100);
      const emoji = tapRate >= 80 ? ' ✨' : tapRate <= 30 ? ' ❌' : '';
      output += `- "${h.hook}" → tap率 ${tapRate}% (${h.tapped_count}/${h.total})${emoji}\n`;
    }
    output += '\n';
  }

  // コンテンツパフォーマンス
  for (const problem of problems) {
    const contents = contentResult.rows.filter(r => r.problem_type === problem);
    if (contents.length === 0) continue;

    output += `## 📝 Content Performance (${problem})\n`;
    for (const c of contents.slice(0, 5)) {
      const thumbsRate = Math.round((c.thumbs_up_count / c.total) * 100);
      const emoji = thumbsRate >= 80 ? ' ✨' : thumbsRate <= 30 ? ' ❌' : '';
      output += `- "${c.content.slice(0, 20)}..." → 👍率 ${thumbsRate}% (${c.thumbs_up_count}/${c.total})${emoji}\n`;
    }
    output += '\n';
  }

  return output;
}
```

#### 6.1.4 タイミングパフォーマンス集計関数

```javascript
async function getTimingPerformance(userId, problems) {
  const result = await query(`
    SELECT
      COALESCE(ne.state->>'scheduledTime', ne.state->>'scheduledHour' || ':00') as scheduled_time,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'tapped' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 1 THEN 1
        ELSE 0
      END) as tapped_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY COALESCE(ne.state->>'scheduledTime', ne.state->>'scheduledHour' || ':00'), ne.subtype
    ORDER BY scheduled_time
  `, [userId]);

  let output = '';

  for (const problem of problems) {
    const timings = result.rows.filter(r => r.problem_type === problem);
    if (timings.length === 0) continue;

    output += `## ⏰ Timing Performance (${problem})\n`;
    for (const t of timings) {
      const tapRate = Math.round((t.tapped_count / t.total) * 100);
      const emoji = tapRate >= 80 ? ' ✨' : tapRate <= 30 ? ' ❌' : '';
      output += `- ${t.scheduled_time}: tap率 ${tapRate}% (${t.tapped_count}/${t.total})${emoji}\n`;
    }
    output += '\n';
  }

  return output;
}
```

#### 6.1.5 曜日パターン集計関数

```javascript
async function getWeeklyPatterns(userId, problems) {
  const result = await query(`
    SELECT
      EXTRACT(DOW FROM ne.created_at) as day_of_week,
      ne.subtype as problem_type,
      COUNT(*) as total,
      SUM(CASE
        WHEN no.signals->>'hookFeedback' = 'ignored' THEN 1
        WHEN no.signals->>'hookFeedback' IS NULL AND no.reward = 0 THEN 1
        ELSE 0
      END) as ignored_count
    FROM nudge_events ne
    LEFT JOIN nudge_outcomes no ON no.nudge_event_id = ne.id
    WHERE ne.user_id = $1::uuid
      AND ne.domain = 'problem_nudge'
      AND ne.created_at >= NOW() - INTERVAL '30 days'
      AND no.id IS NOT NULL
    GROUP BY EXTRACT(DOW FROM ne.created_at), ne.subtype
    ORDER BY day_of_week
  `, [userId]);

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  let output = '## 📅 Weekly Patterns\n';

  // 問題発生率が高い曜日を抽出
  const highRiskDays = result.rows
    .filter(r => r.total >= 3) // 十分なデータがある曜日のみ
    .map(r => ({
      day: dayNames[r.day_of_week],
      problem: r.problem_type,
      ignoredRate: Math.round((r.ignored_count / r.total) * 100)
    }))
    .filter(r => r.ignoredRate >= 50) // ignored率50%以上
    .sort((a, b) => b.ignoredRate - a.ignoredRate);

  if (highRiskDays.length > 0) {
    for (const d of highRiskDays.slice(0, 3)) {
      output += `- ${d.day}: ${d.problem} ignored率 ${d.ignoredRate}%\n`;
    }
  } else {
    output += 'No significant weekly patterns yet.\n';
  }

  // 今日の曜日
  const today = dayNames[new Date().getDay()];
  const todayRisk = highRiskDays.find(d => d.day === today);
  if (todayRisk) {
    output += `\nToday is ${today}. High risk for ${todayRisk.problem}. Consider adjusting timing.\n`;
  } else {
    output += `\nToday is ${today}.\n`;
  }

  return output;
}
```

#### 6.1.7 LLM出力バリデーション + 3-tier Fallback

```javascript
const Ajv = require('ajv');
const ajv = new Ajv();

const nudgeScheduleSchema = {
  type: 'object',
  required: ['schedule', 'overallStrategy'],
  properties: {
    schedule: {
      type: 'array',
      items: {
        type: 'object',
        required: ['scheduledTime', 'problemType', 'hook', 'content', 'tone', 'reasoning'],
        properties: {
          scheduledTime: { type: 'string', pattern: '^([01]?[0-9]|2[0-3]):[0-5][0-9]$' },
          problemType: { type: 'string' },
          hook: { type: 'string', maxLength: 25 },
          content: { type: 'string', maxLength: 80 },
          tone: { type: 'string', enum: ['strict', 'gentle', 'logical', 'provocative', 'philosophical'] },
          reasoning: { type: 'string' },
          rootCauseHypothesis: { type: 'string' }
        }
      }
    },
    overallStrategy: { type: 'string' }
  }
};

const validate = ajv.compile(nudgeScheduleSchema);

async function generateWithFallback(userId, prompt) {
  let attempts = 0;
  let lastError = null;

  while (attempts < 3) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          messages: [{ role: 'user', content: prompt }],
          response_format: { type: 'json_object' }
        })
      });

      const data = await response.json();
      const content = JSON.parse(data.choices[0].message.content);

      if (!validate(content)) {
        throw new Error(`Validation failed: ${JSON.stringify(validate.errors)}`);
      }

      // 30分間隔チェック
      validateMinimumInterval(content.schedule);

      return content;

    } catch (error) {
      attempts++;
      lastError = error;

      if (attempts < 3) {
        // Tier 2: LLMに修正依頼
        prompt += `\n\nPrevious attempt failed: ${error.message}. Please fix.`;
        await new Promise(r => setTimeout(r, Math.pow(2, attempts) * 1000));
      }
    }
  }

  // Tier 3: ルールベースにフォールバック
  console.error(`LLM failed after 3 attempts for user ${userId}:`, lastError);
  return null;
}

function validateMinimumInterval(schedule) {
  const sorted = schedule.sort((a, b) => a.scheduledTime.localeCompare(b.scheduledTime));

  for (let i = 1; i < sorted.length; i++) {
    const prev = timeToMinutes(sorted[i - 1].scheduledTime);
    const curr = timeToMinutes(sorted[i].scheduledTime);

    if (curr - prev < 30) {
      throw new Error(`Nudges too close: ${sorted[i - 1].scheduledTime} and ${sorted[i].scheduledTime}`);
    }
  }
}

function timeToMinutes(time) {
  const [h, m] = time.split(':').map(Number);
  return h * 60 + m;
}
```

### 6.2 `/api/nudge/today` レスポンス変更（後方互換）

```javascript
// レスポンス形式
{
  nudges: [{
    id,
    problemType,
    scheduledTime: "22:00",      // 新フィールド（HH:MM）
    scheduledHour: 22,           // 旧フィールド（後方互換、計算値）
    hook,
    content,
    tone,
    reasoning,
    rootCauseHypothesis,         // 新フィールド（オプショナル）
    createdAt
  }],
  overallStrategy: "...",        // 新フィールド（オプショナル）
  version: "2"                   // APIバージョン
}
```

**後方互換性**:
- `scheduledHour` は `parseInt(scheduledTime.split(':')[0])` で計算して返す
- 古いアプリ（1.3.0）は `scheduledHour` を読む
- 新しいアプリ（1.4.0）は `scheduledTime` を読む

### 6.3 `/api/nudge/feedback` 変更

```javascript
// リクエストボディ
{
  "nudgeId": "xxx",
  "outcome": "success",
  "signals": {
    "hookFeedback": "tapped",      // "tapped" | "ignored"
    "contentFeedback": "thumbsUp", // "thumbsUp" | "thumbsDown" | null
    "timeSpentSeconds": 15
  }
}
```

**後方互換**:
- 既存の `outcome`, `thumbsUp` フィールドも引き続き動作
- 新フィールド `hookFeedback`, `contentFeedback` はオプショナル

---

## 7. iOS変更

### 7.1 `LLMGeneratedNudge.swift` 変更

```swift
struct LLMGeneratedNudge: Codable {
    let id: String
    let problemType: ProblemType
    let scheduledTime: String         // "22:00" (HH:MM) - NEW
    let hook: String
    let content: String
    let tone: NudgeTone
    let reasoning: String
    let rootCauseHypothesis: String?  // NEW
    let createdAt: Date

    // 後方互換: scheduledHourを計算プロパティとして維持
    var scheduledHour: Int {
        let components = scheduledTime.split(separator: ":")
        return Int(components.first ?? "0") ?? 0
    }

    var scheduledMinute: Int {
        let components = scheduledTime.split(separator: ":")
        guard components.count > 1 else { return 0 }
        return Int(components[1]) ?? 0
    }

    // デコード時の後方互換対応
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)

        let problemTypeString = try container.decode(String.self, forKey: .problemType)
        guard let pt = ProblemType(rawValue: problemTypeString) else {
            throw DecodingError.dataCorruptedError(
                forKey: .problemType, in: container,
                debugDescription: "Unknown problemType: \(problemTypeString)"
            )
        }
        problemType = pt

        // scheduledTime があれば使う、なければ scheduledHour から計算
        if let time = try? container.decode(String.self, forKey: .scheduledTime) {
            scheduledTime = time
        } else {
            let hour = try container.decode(Int.self, forKey: .scheduledHour)
            scheduledTime = String(format: "%02d:00", hour)
        }

        hook = try container.decode(String.self, forKey: .hook)
        content = try container.decode(String.self, forKey: .content)
        tone = try container.decode(NudgeTone.self, forKey: .tone)
        reasoning = try container.decode(String.self, forKey: .reasoning)
        rootCauseHypothesis = try? container.decode(String.self, forKey: .rootCauseHypothesis)
        createdAt = try container.decode(Date.self, forKey: .createdAt)
    }

    enum CodingKeys: String, CodingKey {
        case id, problemType, scheduledTime, scheduledHour, hook, content, tone
        case reasoning, rootCauseHypothesis, createdAt
    }
}
```

### 7.2 `NudgeFeedbackService.swift` 新規作成

```swift
import Foundation
import OSLog

actor NudgeFeedbackService {
    static let shared = NudgeFeedbackService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeFeedbackService")

    /// UserDefaultsキー（DateはUserDefaultsに直接保存できないのでTimeIntervalを使用）
    private let scheduledNudgesKey = "scheduledNudges"

    struct FeedbackPayload: Encodable {
        let nudgeId: String
        let outcome: String
        let signals: Signals

        struct Signals: Encodable {
            let hookFeedback: String
            let contentFeedback: String?
            let timeSpentSeconds: Int?
        }
    }

    func sendFeedback(
        nudgeId: String,
        hookFeedback: String,
        contentFeedback: String?,
        timeSpentSeconds: Int?
    ) async throws {
        let payload = FeedbackPayload(
            nudgeId: nudgeId,
            outcome: hookFeedback == "tapped" ? "success" : "ignored",
            signals: .init(
                hookFeedback: hookFeedback,
                contentFeedback: contentFeedback,
                timeSpentSeconds: timeSpentSeconds
            )
        )

        let url = await MainActor.run { AppConfig.nudgeFeedbackURL }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let deviceId = await AppState.shared.resolveDeviceId()
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(deviceId, forHTTPHeaderField: "user-id")

        request.httpBody = try JSONEncoder().encode(payload)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw ServiceError.feedbackFailed
        }

        logger.info("✅ Feedback sent: \(nudgeId) hookFeedback=\(hookFeedback)")
    }

    /// アプリ起動時に6時間経過の未タップ通知を`ignored`として送信
    func sendIgnoredFeedbackForExpiredNudges() async {
        let expiredNudges = getExpiredUnrespondedNudges()

        for nudgeId in expiredNudges {
            do {
                try await sendFeedback(
                    nudgeId: nudgeId,
                    hookFeedback: "ignored",
                    contentFeedback: nil,
                    timeSpentSeconds: nil
                )
                markNudgeAsProcessed(nudgeId)
                logger.info("📤 Sent ignored feedback for expired nudge: \(nudgeId)")
            } catch {
                logger.error("Failed to send ignored feedback for \(nudgeId): \(error)")
            }
        }
    }

    /// 6時間経過の未タップNudgeを取得（TimeIntervalで保存されているのでDateに変換）
    private func getExpiredUnrespondedNudges() -> [String] {
        let allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
        let now = Date().timeIntervalSince1970
        let expiredThreshold: TimeInterval = 6 * 60 * 60 // 6時間

        return allScheduled.compactMap { (nudgeId, scheduledTimestamp) in
            now - scheduledTimestamp > expiredThreshold ? nudgeId : nil
        }
    }

    /// Nudgeを処理済みとしてマーク（UserDefaultsから削除）
    private func markNudgeAsProcessed(_ nudgeId: String) {
        var allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
        allScheduled.removeValue(forKey: nudgeId)
        UserDefaults.standard.set(allScheduled, forKey: scheduledNudgesKey)
    }

    /// 通知タップ時に呼び出し（UserDefaultsから削除してtappedを送信）
    func handleNudgeTapped(nudgeId: String) async throws {
        // UserDefaultsから削除（もうignoredとして送信しない）
        markNudgeAsProcessed(nudgeId)

        // tappedを送信
        try await sendFeedback(
            nudgeId: nudgeId,
            hookFeedback: "tapped",
            contentFeedback: nil,
            timeSpentSeconds: nil
        )
    }

    enum ServiceError: Error {
        case feedbackFailed
    }
}
```

### 7.3 `MainTabView.swift`（または通知ハンドラ）変更 - hookFeedback送信

**通知タップ時に`hookFeedback: "tapped"`を送信する呼び出し元**:

```swift
// MainTabView.swift または AppDelegate の通知ハンドラ内

/// 通知タップ時の処理（NudgeCardView表示前に呼び出す）
func handleNotificationTap(nudgeContent: NudgeContent) {
    // LLM生成Nudgeの場合、hookFeedback: "tapped" を即座に送信
    if let nudgeId = nudgeContent.llmNudgeId {
        Task {
            do {
                try await NudgeFeedbackService.shared.handleNudgeTapped(nudgeId: nudgeId)
            } catch {
                // エラーは無視（ユーザー体験を妨げない）
                print("Failed to send tapped feedback: \(error)")
            }
        }
    }

    // NudgeCardViewを表示
    showNudgeCard(content: nudgeContent)
}
```

**呼び出しタイミング**:
1. 通知タップ → `userNotificationCenter(_:didReceive:)` が呼ばれる
2. `handleNotificationTap()` を呼ぶ
3. `NudgeFeedbackService.handleNudgeTapped()` で `hookFeedback: "tapped"` を送信
4. `NudgeCardView` を表示

### 7.4 `LLMNudgeCache.swift` 変更 - キー衝突防止

**問題**: 同じ時間帯（例: 22:00と22:30）に複数のNudgeがあると、`scheduledHour`が同じになりキーが衝突する。

```swift
import Foundation
import OSLog

/// LLM生成Nudgeのキャッシュ（@MainActorでスレッド安全性を保証）
@MainActor
final class LLMNudgeCache {
    static let shared = LLMNudgeCache()

    /// 後方互換: 時間のみのキー（problemType_hour）
    private var cacheByHour: [String: LLMGeneratedNudge] = [:]

    /// 新規: 分も含むキー（problemType_hour_minute）- キー衝突防止
    private var cacheByTime: [String: LLMGeneratedNudge] = [:]

    private let logger = Logger(subsystem: "com.anicca.ios", category: "LLMNudgeCache")

    private init() {}

    /// 指定された問題タイプと時刻のNudgeを取得（30分ウィンドウでマッチング）
    func getNudge(for problem: ProblemType, hour: Int, minute: Int = 0) -> LLMGeneratedNudge? {
        // 1. 完全一致を試す（分も含む）
        let exactKey = "\(problem.rawValue)_\(hour)_\(minute)"
        if let nudge = cacheByTime[exactKey] {
            return nudge
        }

        // 2. 30分ウィンドウ内でマッチング
        let targetMinutes = hour * 60 + minute
        for (_, nudge) in cacheByTime where nudge.problemType == problem {
            let nudgeMinutes = nudge.scheduledHour * 60 + nudge.scheduledMinute
            if abs(nudgeMinutes - targetMinutes) <= 30 {
                return nudge
            }
        }

        // 3. 後方互換: 時間のみのキーで検索
        let hourKey = "\(problem.rawValue)_\(hour)"
        return cacheByHour[hourKey]
    }

    /// 指定された問題タイプのNudgeを取得（時刻無視、デバッグ用）
    func getNudgeAnyHour(for problem: ProblemType) -> LLMGeneratedNudge? {
        return cacheByTime.values.first { $0.problemType == problem }
            ?? cacheByHour.values.first { $0.problemType == problem }
    }

    /// Nudgeをキャッシュに設定（複数一括設定）
    func setNudges(_ nudges: [LLMGeneratedNudge]) {
        cacheByHour.removeAll()
        cacheByTime.removeAll()

        for nudge in nudges {
            // 後方互換: 時間のみのキー
            let hourKey = "\(nudge.problemType.rawValue)_\(nudge.scheduledHour)"
            cacheByHour[hourKey] = nudge

            // 新規: 分も含むキー（キー衝突防止）
            let timeKey = "\(nudge.problemType.rawValue)_\(nudge.scheduledHour)_\(nudge.scheduledMinute)"
            cacheByTime[timeKey] = nudge
        }
        logger.info("📦 [LLMCache] Set \(nudges.count) nudges (byHour: \(self.cacheByHour.count), byTime: \(self.cacheByTime.count))")
    }

    /// キャッシュをクリア（テスト用）
    func clear() {
        cacheByHour.removeAll()
        cacheByTime.removeAll()
        logger.info("📦 [LLMCache] Cleared")
    }

    // MARK: - Debug Methods

    var count: Int { cacheByTime.count }

    func getFirstNudge() -> LLMGeneratedNudge? {
        cacheByTime.values.first ?? cacheByHour.values.first
    }
}
```

### 7.5 `ProblemNotificationScheduler.swift` 変更 - scheduledNudges保存

**通知スケジュール時にUserDefaultsに保存（ignored判定用）**:

```swift
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // ... 既存のスケジューリングロジック ...

    do {
        try await center.add(request)
        logger.info("Scheduled problem notification: \(problem.rawValue) at \(hour):\(minute)")

        // ★ 追加: LLM生成Nudgeの場合、UserDefaultsに保存（ignored判定用）
        if let llmNudgeId = selection.content?.id {
            saveScheduledNudge(nudgeId: llmNudgeId, hour: hour, minute: minute)
        }

        // 既存: NudgeStatsに記録
        await MainActor.run {
            NudgeStatsManager.shared.recordScheduled(
                problemType: problem.rawValue,
                variantIndex: selection.variantIndex,
                scheduledHour: hour,
                isAIGenerated: selection.isAIGenerated,
                llmNudgeId: selection.content?.id
            )
        }
    } catch {
        logger.error("Failed to schedule problem notification: \(error.localizedDescription)")
    }
}

/// scheduledNudgesをUserDefaultsに保存（ignored判定用）
private func saveScheduledNudge(nudgeId: String, hour: Int, minute: Int) {
    let scheduledNudgesKey = "scheduledNudges"

    // スケジュール予定時刻を計算
    let calendar = Calendar.current
    var components = calendar.dateComponents([.year, .month, .day], from: Date())
    components.hour = hour
    components.minute = minute

    guard let scheduledDate = calendar.date(from: components) else { return }

    // 過去の時刻なら翌日として扱う
    let targetDate: Date
    if scheduledDate < Date() {
        targetDate = calendar.date(byAdding: .day, value: 1, to: scheduledDate) ?? scheduledDate
    } else {
        targetDate = scheduledDate
    }

    // TimeIntervalとして保存（DateはUserDefaultsに直接保存できない）
    var allScheduled = UserDefaults.standard.dictionary(forKey: scheduledNudgesKey) as? [String: TimeInterval] ?? [:]
    allScheduled[nudgeId] = targetDate.timeIntervalSince1970
    UserDefaults.standard.set(allScheduled, forKey: scheduledNudgesKey)

    logger.info("📅 Saved scheduled nudge: \(nudgeId) at \(hour):\(minute)")
}
```

### 7.6 `LLMNudgeService.swift` 変更 - レスポンス拡張

**overallStrategyを受け取れるように拡張**:

```swift
import Foundation
import OSLog

actor LLMNudgeService {
    static let shared = LLMNudgeService()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "LLMNudgeService")
    private let session: URLSession
    private let decoder: JSONDecoder

    /// 今日の戦略（LLMが生成）
    private(set) var overallStrategy: String?

    private init() {
        self.session = URLSession.shared
        self.decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
    }

    /// 今日生成されたNudgeを取得
    func fetchTodaysNudges() async throws -> [LLMGeneratedNudge] {
        let url = await MainActor.run { AppConfig.nudgeTodayURL }
        let deviceId = await AppState.shared.resolveDeviceId()
        logger.info("🔄 [LLM] Requesting: \(url.absoluteString)")

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(deviceId, forHTTPHeaderField: "user-id")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw ServiceError.httpError((response as? HTTPURLResponse)?.statusCode ?? 0)
        }

        let responseBody = try decoder.decode(NudgeTodayResponse.self, from: data)

        // overallStrategyを保存
        self.overallStrategy = responseBody.overallStrategy

        logger.info("✅ [LLM] Decoded \(responseBody.nudges.count) nudges, strategy: \(responseBody.overallStrategy ?? "none")")
        return responseBody.nudges
    }

    enum ServiceError: Error {
        case invalidResponse
        case httpError(Int)
    }
}

/// APIレスポンス形式（拡張版）
private struct NudgeTodayResponse: Codable {
    let nudges: [LLMGeneratedNudge]
    let overallStrategy: String?  // 新フィールド（オプショナル）
    let version: String?          // 新フィールド（オプショナル、後方互換確認用）
}
```

### 7.7 `AppDelegate.swift` 変更

```swift
func application(_ application: UIApplication, didFinishLaunchingWithOptions...) -> Bool {
    // ... 既存の処理 ...

    // 6時間経過の未タップ通知をignoredとして送信
    Task {
        await NudgeFeedbackService.shared.sendIgnoredFeedbackForExpiredNudges()
    }

    return true
}
```

### 7.4 `AppConfig` に追加

```swift
static var nudgeFeedbackURL: URL {
    URL(string: "\(baseURL)/api/mobile/nudge/feedback")!
}
```

---

## 8. データモデル

### 8.1 DBスキーマ（変更なし、既存で対応可能）

`nudge_events.state` JSONBの構造を拡張:

```json
{
  "id": "uuid",
  "scheduledTime": "22:00",
  "hook": "...",
  "content": "...",
  "tone": "strict",
  "reasoning": "...",
  "rootCauseHypothesis": "...",
  "language": "ja"
}
```

`nudge_outcomes.signals` JSONBの構造を拡張:

```json
{
  "hookFeedback": "tapped",
  "contentFeedback": "thumbsUp",
  "timeSpentSeconds": 15,
  "thumbsUp": true,
  "outcome": "success"
}
```

### 8.2 後方互換性

| 項目 | 対応 |
|------|------|
| `scheduledHour`（旧） | `scheduledTime`から計算。APIレスポンスで両方返す |
| `thumbsUp/thumbsDown`（旧） | `contentFeedback`と並行して保存 |
| 古いアプリ（1.3.0） | `scheduledHour`を読む。新フィールドは無視 |

---

## 9. テストマトリックス

| # | To-Be | テスト名 | タイプ |
|---|-------|----------|--------|
| 1 | ストーリー形式プロンプト構築 | `test_buildUserStory_formats_correctly` | Unit |
| 2 | フック/コンテンツパフォーマンス集計 | `test_getHookContentPerformance_separates_correctly` | Unit |
| 3 | タイミングパフォーマンス集計 | `test_getTimingPerformance_groups_by_hour` | Unit |
| 4 | 曜日パターン集計 | `test_getWeeklyPatterns_detects_high_risk_days` | Unit |
| 5 | LLM出力バリデーション | `test_validateLLMOutput_rejects_invalid` | Unit |
| 6 | 3-tier Fallback | `test_generateWithFallback_falls_back_to_rule_based` | Unit |
| 7 | Day 1判定 | `test_shouldUseLLM_returns_false_for_day1` | Unit |
| 8 | iOS: scheduledTime→scheduledHour変換 | `test_LLMGeneratedNudge_scheduledHour_computed` | Unit |
| 9 | iOS: フィードバック送信 | `test_NudgeFeedbackService_sends_correctly` | Unit |
| 10 | iOS: ignored送信（6時間経過） | `test_sendIgnoredFeedbackForExpiredNudges` | Unit |
| 11 | iOS: 通知スケジューリング | `test_scheduleFromLLMNudges_sets_correct_time` | Unit |
| 12 | iOS: 30分単位マッチング（キー衝突防止） | `test_getNudge_matches_30min_window` | Unit |
| 13 | iOS: hookFeedback tapped送信 | `test_handleNudgeTapped_sends_feedback` | Unit |
| 14 | iOS: scheduledNudges UserDefaults保存 | `test_saveScheduledNudge_stores_correctly` | Unit |
| 15 | iOS: LLMNudgeService overallStrategy受け取り | `test_fetchTodaysNudges_parses_overallStrategy` | Unit |
| 16 | E2E: Nudge配信→タップ→フィードバック | `e2e_nudge_feedback_flow` | Maestro |
| 17 | E2E: Day1→Day2切り替え | `e2e_day1_to_day2_transition` | Maestro |

---

## 10. 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| Midday Re-evaluation（12:00 PM 再評価） | 1日計画で十分。局所最適化は避ける |
| MEM0統合 | 7日分のストーリーで十分。将来検討 |
| Exa API連携 | 苦しみを減らすことが本質。現時点では不要 |
| 深掘り回答の反映 | ユーザー入力不要がAniccaの強み |
| マルチモーダル | Phase 9以降 |
| リアルタイム（分単位）修正 | 1日計画が正しい設計思想 |

---

## 11. レビューチェックリスト

### 11.1 Spec レビュー

- [x] 全To-Beがタスクリストに含まれているか
- [x] 全To-Beがテストマトリックスに含まれているか
- [x] 後方互換性は保たれているか
- [x] プロンプト設計は明確か（Day 1〜5 具体例あり）
- [x] 境界（やらないこと）は明確か
- [x] コールドスタート戦略は明確か
- [x] 技術決定事項は全て明記されているか
- [x] hookFeedback送信の呼び出し元が明記されているか（7.3追加）
- [x] LLMNudgeCacheのキー衝突防止が明記されているか（7.4追加）
- [x] scheduledNudges保存タイミングが明記されているか（7.5追加）
- [x] プロンプト集計関数が明記されているか（6.1.3〜6.1.5追加）

### 11.2 実装レビュー

- [ ] API変更は後方互換か
- [ ] iOS変更は後方互換か
- [ ] テストカバレッジは80%以上か
- [ ] プロンプトの文字数制限は正しいか
- [ ] エラーハンドリングは適切か
- [ ] LLMバリデーション + Fallbackは動作するか

### 11.3 リリース前

- [ ] Staging環境で動作確認
- [ ] Mixpanelにログが送信されているか
- [ ] 実機で通知が正しい時刻に届くか
- [ ] フィードバックがDBに保存されているか
- [ ] Day 1→Day 2の切り替えが正しく動作するか

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd-workflow` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |

---

## 実行手順

### API側

```bash
cd apps/api
npm test  # ユニットテスト
npm run dev  # ローカル起動
```

### iOS側

```bash
cd aniccaios
xcodebuild test -project aniccaios.xcodeproj -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' \
  -only-testing:aniccaiosTests | xcpretty
```

### E2E

```bash
maestro test maestro/nudge/
```

---

*この仕様書は Phase 7+8 の完全な実装を定義する。1日計画でwisdomを蓄積し、人間を理解するBuddhaへ。*
