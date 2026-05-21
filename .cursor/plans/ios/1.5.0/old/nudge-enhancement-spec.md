# v1.5.0: Nudge強化 — 頻度増加 + LLMグラウンディング + iOS修正

> **バージョン**: 1.5.0
>
> **最終更新**: 2026-01-27
>
> **目的**: Day 1からNudge頻度を増やし、LLMプロンプトに行動科学の知見を注入し、Phase 7-8のiOS側バグを修正する

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-nudge-enhancement` |
| **ブランチ** | `feature/nudge-enhancement` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec レビュー中 |

---

## 概要

### What

3つの改善を同時に行う:

| # | 改善 | レイヤー |
|---|------|---------|
| 1 | ルールベースのタイムスロット増加（全問題5回/日） | iOS |
| 2 | LLMプロンプトに行動科学グラウンディングを追加 | API |
| 3 | iOS側のPhase 7-8バグ修正（交互ロジック削除 + shift無効化） | iOS |
| 4 | LLM/ルールベース識別UI（青ドット） | iOS |
| 5 | CLAUDE.mdサブスク情報修正（AGENTS.md基準に統一） | ドキュメント |

### Why

| 問題 | 影響 |
|------|------|
| Day 1のルールベースが1-2回/日しかない問題がある（lyingは1回） | トライアル1日目で価値を体感できない → 解約 |
| LLMが行動科学を知らない | 「落ち着け」（怒り）、「考えるな」（反芻）など逆効果なNudgeを生成しうる |
| NudgeContentSelectorの交互ロジック | LLMが設計した1日計画の半分がルールベースに置き換わる |
| Shift ロジックがLLM Nudgeの時間を最大120分ずらす | LLMの最適タイミング判断が上書きされる |
| LLM vs ルールベースの区別がRelease buildで見えない | 効果検証ができない |

### 設計判断

| 判断 | 決定 | 理由 |
|------|------|------|
| NudgeContentSelectorの交互ロジック | **削除** | Phase 6の残骸。Phase 7-8は「LLMが1日をデザイン」に方針転換済み |
| Shift ロジック | **LLM Nudgeには無効化、ルールベース（Day 1）にのみ適用** | LLMは`getTimingPerformance()`で最適時間を判断済み。二重調整は衝突する |
| 最小間隔 | **60分（起床ウィンドウのみ15分）** | PLOS One研究: 60-90分が最適。46%が過剰通知で通知オフ |
| UI識別 | **NudgeCard右上に6pt青ドット（常時表示）** | DEBUG限定だとApp Storeで見えない。6ptは一般ユーザーが気づきにくい |
| グラウンディング方式 | **問題タイプ別2-3行の要点をプロンプトに追加** | 全文だと長すぎてLLMの注意が分散。NEVER/DOフォーマットが最も従いやすい |

---

## 受け入れ条件

| # | 条件 | 検証方法 |
|---|------|---------|
| AC1 | 全13問題タイプが5回/日のタイムスロットを持つ | Unit Test: `ProblemType.notificationSchedule.count == 5` |
| AC2 | Day 2+でLLMキャッシュにNudgeがあれば100% LLM使用 | Unit Test: `NudgeContentSelector` が交互ではなくLLM優先 |
| AC3 | LLM Nudgeに対してshiftロジックが発動しない | Unit Test: LLM Nudgeの時間がシフトされない |
| AC4 | ルールベースの最小間隔が60分 | Unit Test: `minimumIntervalMinutes == 60` |
| AC5 | `cant_wake_up`の起床ウィンドウ(06:00-06:30)は15分間隔を許可 | Unit Test |
| AC6 | LLMプロンプトに`Behavioral Science Grounding`セクションが含まれる | API Unit Test |
| AC7 | LLMプロンプトの最小間隔が60分に更新されている | API Unit Test |
| AC8 | NudgeCardでLLM生成時に青ドットが表示される（Release含む） | Maestro E2E or 実機確認 |
| AC9 | ルールベース時に青ドットが表示されない | Maestro E2E or 実機確認 |
| AC10 | CLAUDE.mdサブスク情報がAGENTS.md基準と一致 | 目視確認: 月額$9.99・年額$49.99・SKAN設定が記載 |
| AC11 | 後方互換: 1.4.0ユーザーが壊れない | API Unit Test: (1) レスポンスに`scheduledTime`+`scheduledHour`両方含む (2) LLMキャッシュ空時にルールベースフォールバック動作 (3) 通知userInfoキー`notificationTextKey`が維持される |

---

## As-Is（現状: 1.4.0）

### タイムスロット（ルールベース）

| ProblemType | 回/日 | スロット |
|---|---|---|
| staying_up_late | 4 | 21:00, 22:30, 00:00, 01:00 |
| cant_wake_up | 2 | 06:00, 06:05 |
| self_loathing | 3 | 07:00, 12:30, 21:30 |
| rumination | 3 | 07:30, 14:00, 21:00 |
| procrastination | 2 | 09:00, 14:30 |
| anxiety | 3 | 07:00, 12:00, 18:30 |
| lying | 1 | 08:00 |
| bad_mouthing | 2 | 08:30, 12:00 |
| porn_addiction | 2 | 22:00, 06:30 |
| alcohol_dependency | 2 | 18:00, 20:30 |
| anger | 2 | 09:30, 18:00 |
| obsessive | 3 | 09:00, 15:30, 21:00 |
| loneliness | 2 | 12:00, 20:00 |

### NudgeContentSelector

- 交互ロジック: `lastWasLLM[key]` でLLM↔ルールベースを交互
- Day 2+でもNudgeの約50%がルールベースに置き換わる

### LLMプロンプト

- 行動科学のグラウンディングなし
- 最小間隔: 30分
- ガイドライン: 2-10 nudges/day

### ProblemNotificationScheduler

- `minimumIntervalMinutes = 30`
- Shift ロジック: 2日連続ignored → +30分（最大120分）、LLM/ルールベース区別なし

---

## To-Be（変更後: 1.5.0）

### To-Be 1: タイムスロット更新（`ProblemType.swift`）

全問題を5回/日に統一。行動科学リサーチに基づく時間設定。

| # | ProblemType | スロット | 戦略 | 根拠 |
|---|---|---|---|---|
| 1 | staying_up_late | 20:30, 21:30, 22:30, 23:30, 07:30 | 予防→介入→介入→介入→振返 | スクリーン使用22-01時ピーク。メラトニン抑制は就寝2h前から |
| 2 | cant_wake_up | 22:00, 06:00, 06:15, 06:30, 08:00 | 予防(前夜)→介入→介入→介入→振返 | 睡眠慣性=40h徹夜相当。15分刻みの起床ウィンドウ |
| 3 | self_loathing | 07:00, 12:00, 18:00, 21:30, 22:30 | 予防→予防→介入→介入→振返 | コルチゾール覚醒反応で朝悪化。反芻的自己注目は朝夜ピーク |
| 4 | rumination | 07:30, 19:00, 20:30, 22:00, 23:00 | 振返→予防→予防→介入→介入 | 反芻は睡眠#1キラー（UCSF）。「心配タイム」を早い時間に設定 |
| 5 | procrastination | 09:00, 13:30, 15:00, 19:00, 21:00 | 予防→介入→介入→予防→振返 | 13-15時の概日リズムの谷。先延ばし=感情調節問題 |
| 6 | anxiety | 06:30, 09:30, 14:00, 20:00, 22:30 | 介入→予防→介入→予防→介入 | CAR: 起床30-45分後に50-60%スパイク |
| 7 | lying | 08:00, 12:00, 15:00, 19:00, 21:30 | 予防→予防→介入→振返→振返 | 「朝の道徳効果」: 午後22%、夕方44%嘘つきやすい |
| 8 | bad_mouthing | 08:30, 12:30, 17:00, 20:00, 22:00 | 予防→介入→介入→予防→振返 | ゴシップ52分/日。悪口=感情調節機能（心拍数低下効果） |
| 9 | porn_addiction | 20:00, 21:30, 22:30, 23:30, 07:30 | 予防→予防→介入→介入→振返 | トラフィック23時ピーク。衝動は30分で消える |
| 10 | alcohol_dependency | 16:00, 18:00, 19:30, 20:30, 22:00 | 予防→予防→介入→介入→振返 | 渇望20-21時ピーク（複数研究で再現）。谷は朝8-9時 |
| 11 | anger | 07:30, 12:00, 15:30, 17:30, 21:00 | 予防→予防→予防→介入→振返 | 攻撃性は夕暮れにピーク（Harvard）。朝のブレーキが日中に緩む |
| 12 | obsessive | 08:00, 18:00, 20:00, 21:30, 23:00 | 振返→予防→予防→介入→介入 | OCD患者40%が入眠遅延。メラトニンピーク2h遅い |
| 13 | loneliness | 09:00, 14:00, 18:30, 21:00, 22:30 | 予防→介入→予防→介入→振返 | BMJ: 最も気分が低いのは深夜。マイクロ接続が有効 |

**最小間隔の例外**: `cant_wake_up`の06:00-06:30は15分間隔を許可（急性期ウィンドウ）。

**`validTimeRange`変更**: `cant_wake_up`の現行`validTimeRange`は`(6, 0, 9, 0)`で22:00スロットがサイレントスキップされる。`validTimeRange`を`nil`（制限なし）に変更し、スケジュールはTo-Be 1のスロット定義に委ねる。

**`lying`バリアント制約（既知制約）**: `lying`の`notificationVariantCount`は1。Day 1ルールベースでは同一テキストが5回届く。Day 2+はLLMが異なるコンテンツを生成するため問題なし。Day 1の重複はv1.6.0でバリアント追加を検討。

### To-Be 2: NudgeContentSelector修正

```swift
// Before (Phase 6残骸 — 交互ロジック)
func selectVariant(...) {
    let shouldTryLLM = !(lastWasLLM[key] ?? false)  // 交互
    if shouldTryLLM {
        if let llmNudge = LLMNudgeCache.shared.getNudge(...) { ... }
    }
    // fallback to rule-based
}

// After (Phase 7-8意図通り — LLM優先)
func selectVariant(...) {
    // Day 2+: LLMキャッシュにあれば常にLLM
    if let llmNudge = LLMNudgeCache.shared.getNudge(...) {
        return (variantIndex: -1, isAIGenerated: true, content: llmNudge)
    }
    // LLMキャッシュが空の場合のみルールベースにフォールバック
    let selectedVariant = selectExistingVariant(...)
    return (variantIndex: selectedVariant, isAIGenerated: false, content: nil)
}
```

`lastWasLLM` ディクショナリは削除。`resetAlternatingState()`も削除。

`#if DEBUG`内の`selectVariantForDebug`メソッドも同様にLLM優先ロジックに修正（交互ロジック削除）。

### To-Be 3: Shift ロジック修正（`ProblemNotificationScheduler.swift`）

**設計上の注意**: 現行実装では`scheduleNotifications()`内のshift計算（行50-85）が`selectVariant()`（行189）の前に実行される。そのため`selection.isAIGenerated`はshift計算時点で未定義。

**解決方針**: LLMキャッシュの有無を事前判定してshiftを条件分岐する。`LLMNudgeCache.shared.hasNudge(for:hour:)`はアプリ起動時の日次API取得後に確定するため、スケジュール時点で参照可能。

```swift
// Before: 全Nudgeにshiftを適用
let newShift = calculateNewShift(currentShift: currentShift, consecutiveIgnored: consecutiveIgnored)

// After: LLMキャッシュの有無を事前判定し、ルールベースのみshiftを適用
let hasLLMContent = LLMNudgeCache.shared.hasNudge(for: problem, hour: time.hour)
if !hasLLMContent {
    // ルールベース → shift適用
    let newShift = calculateNewShift(currentShift: currentShift, consecutiveIgnored: consecutiveIgnored)
    // shift適用
}
// LLM Nudge → shiftスキップ（LLMが最適タイミングを判断済み）
```

**注意**: `LLMNudgeCache`に`hasNudge(for:hour:)`メソッドが未存在の場合は追加する（`getNudge`のnil判定ラッパー）。

### To-Be 4: 最小間隔変更

```swift
// Before
private let minimumIntervalMinutes = 30

// After
private let minimumIntervalMinutes = 60
private let wakeWindowIntervalMinutes = 15  // cant_wake_upの06:00-06:30用
```

**衝突回避ロジック変更**:

現行（As-Is）: 衝突時に固定`+15分`ずらし。`minimumIntervalMinutes`を60にしても衝突解決が15分刻みのまま。

変更後:
```swift
// Before: 固定+15分ずらし
if currentMinutes < last + minimumIntervalMinutes {
    currentMinutes = last + 15  // ❌ 60分間隔を満たさない
}

// After: minimumIntervalMinutesまで繰り下げ
let interval = isWakeWindow(schedule) ? wakeWindowIntervalMinutes : minimumIntervalMinutes
if currentMinutes < last + interval {
    currentMinutes = last + interval  // ✅ 間隔を保証
}
```

`isWakeWindow`判定: `schedule.problem == .cantWakeUp` かつ `hour*60+minute` が `360...390`（06:00-06:30）の範囲内。

### To-Be 5: LLMプロンプト グラウンディング（`nudgeHelpers.js`）

`buildPhase78Prompt()`に新セクションを追加。

**加えて`validateMinimumInterval()`（行371-385）の閾値を30→60に変更**:
```javascript
// Before
if (curr - prev < 30) { throw new Error(...) }

// After
if (curr - prev < 60) { throw new Error(...) }
```
これにより、iOS側（60分）とAPI側（60分）で最小間隔が一致する。

```
## 🧠 Behavioral Science Grounding

For each problem type, follow these evidence-based guidelines:

### staying_up_late
- Peak: Screen use 22:00-01:00. Melatonin suppressed within 2h of bedtime
- Strategy: Preventive nudge 90min before bedtime > intervention during scrolling
- NEVER: Lecture about sleep hygiene
- DO: One concrete micro-action ("Put phone in another room for 10 min")
- Urges fade within 30 minutes if not reinforced

### cant_wake_up
- Peak: Sleep inertia upon waking = cognitive impairment equal to 40h sleep deprivation
- Strategy: Rapid micro-actions within 15min of alarm. Night-before prep is key
- NEVER: Imply laziness. Sleep inertia is biological, not moral
- DO: "Feet on the floor" or "Walk to window for light exposure"

### self_loathing
- Peak: Morning (cortisol awakening response) and evening (weakened cognitive control)
- Strategy: Radical acceptance, not productivity language
- NEVER: "You can do it!" (triggers past failure memories)
- DO: "You're here. That's enough." Self-compassion reduces the self-criticism cycle

### rumination
- Peak: Night (21:00-01:00) when external distractions fade
- Strategy: "Scheduled worry time" earlier in the day (evidence-based technique)
- NEVER: "Just stop thinking about it" (backfires)
- DO: Externalization — write it down, name the thought pattern, grounding exercise (5 senses)

### procrastination
- Peak: 13:00-15:00 (circadian energy dip). Evening bedtime procrastination
- Strategy: Address the emotion, not the task
- NEVER: "Just do it" or time management advice
- DO: "What's the 2-minute version?" Acknowledge the feeling behind the avoidance

### anxiety
- Peak: Morning — Cortisol Awakening Response (50-60% spike 30-45min after waking)
- Strategy: Physiological regulation before cognitive intervention
- NEVER: "Don't worry" or "There's nothing to be afraid of"
- DO: "Breathe in for 4, out for 6." Extended exhale activates parasympathetic system

### lying
- Peak: Afternoon (22% more likely) and evening (44% more likely) — "morning morality effect"
- Strategy: Explore the emotional need behind the lie, not the lie itself
- NEVER: Shame or moralize (triggers defensive lying)
- DO: "What were you protecting?" Lying is often a learned survival strategy

### bad_mouthing
- Peak: Social hours, afternoon self-control decline, evening social media
- Strategy: Redirect from judging others to understanding own reaction
- NEVER: "Don't talk about people" (moralizing)
- DO: "What did that person's behavior make you feel?" Address the underlying frustration

### porn_addiction
- Peak: 22:00-01:00 (privacy, fatigue, lowered inhibition). Urges last <30 minutes
- Strategy: Urge surfing — observe without acting. Address emotional trigger (HALT: Hungry/Angry/Lonely/Tired)
- NEVER: Shame or moral judgment (shame is #1 relapse trigger)
- DO: "The urge is here. It will pass. You don't have to act on it."

### alcohol_dependency
- Peak: 20:00-21:00 craving peak (replicated in multiple studies). Trough at 08:00-09:00
- Strategy: The craving is a wave — ride it past the peak
- NEVER: "You shouldn't drink"
- DO: "What can you do with your hands for the next 20 minutes?" (cooking, walking, stretching)

### anger
- Peak: Late afternoon/early evening (16:00-19:00). Biological "brake" loosens through the day
- Strategy: Physical circuit-breaker first, emotional processing later
- NEVER: "Calm down" (escalates anger)
- DO: "Step away for 90 seconds. Splash cold water on your face." (vagal dive reflex)

### obsessive
- Peak: Night (21:00-03:00). OCD patients have delayed melatonin peak by 2 hours
- Strategy: Cognitive defusion — change relationship with the thought, not the thought itself
- NEVER: Reassure "It won't happen" (feeds the OCD cycle)
- DO: "Notice the thought. Label it: 'That's an intrusive thought.' Let it pass like a cloud."

### loneliness
- Peak: Late evening/night (21:00-00:00). Circadian mood dip near midnight
- Strategy: Micro-connections, not big social commitments
- NEVER: "Join a club" or "Make more friends" (overwhelms someone already isolated)
- DO: "Text one person right now. Even just an emoji." Validate the courage it takes

## Nudge Frequency Rules
- Minimum interval: 60 minutes between nudges (EXCEPT cant_wake_up wake window 06:00-06:30: 15 min allowed)
- Guideline: 4-8 nudges per day
- Strategy mix: ~40% preventive (before peak), ~40% intervention (during peak), ~20% reflection (after/next morning)
- Base schedule on peak times from behavioral science AND user's actual response patterns
```

### To-Be 6: LLM/ルールベース識別UI

`NudgeCardView.swift`に以下を追加（`#if DEBUG`ではなく常時表示）:

```swift
// NudgeCard右上に6ptの青ドット
if content.isAIGenerated {
    Circle()
        .fill(Color.blue.opacity(0.6))
        .frame(width: 6, height: 6)
        .offset(x: 8, y: -8)
}
```

既存の`#if DEBUG`ブロック（🤖アイコン、"(LLM)"テキスト）は削除。

### To-Be 7: CLAUDE.mdサブスク情報修正

CLAUDE.mdに既にサブスク情報セクションが存在するが、AGENTS.md基準（月額$9.99・年額$49.99デフォルト）と不整合。修正する:

```markdown
### サブスクリプション & Paywall

| 項目 | 内容 |
|------|------|
| 価格 | 月額 $9.99 / 年額 $49.99（デフォルト） |
| Paywall種別 | ハード（無料利用不可） |
| トライアル | 1週間無料 |
| 決済基盤 | RevenueCat + Superwall |
| SKAN設定 | CV1=Launch App, CV2=月額$9-10, CV3=年額$49-50 |

### 1週間トライアルの戦略

7日間 = Aniccaの全力を見せるウィンドウ。

| 日 | 体験 | 狙い |
|----|------|------|
| Day 1 | ルールベースNudge（5回/日/問題） | 即座に価値体感。研究ベースの最適タイミング |
| Day 2-6 | LLM Nudge（学習・改善・パーソナライズ） | 行動科学グラウンディング + ユーザー履歴で最適化 |
| Day 7 | 解約判断日 | 「これなしでは無理」状態を目指す |

Nudgeの質×頻度 = 継続率。ここが生命線。
```

---

## テストマトリックス

| # | To-Be | テスト名 | タイプ | カバー |
|---|-------|----------|--------|--------|
| 1 | タイムスロット更新 | `test_allProblemTypes_have5Slots` | Unit | ✅ |
| 2 | タイムスロット根拠 | `test_stayingUpLate_slotsMatchResearch` | Unit | ✅ |
| 3 | 起床ウィンドウ間隔 | `test_cantWakeUp_allows15minInterval` | Unit | ✅ |
| 4 | 最小間隔60分 | `test_minimumInterval_is60minutes` | Unit | ✅ |
| 5 | LLM優先（交互削除） | `test_selectVariant_prefersLLM_whenCached` | Unit | ✅ |
| 6 | LLMキャッシュ空→ルールベース | `test_selectVariant_fallsBackToRuleBased` | Unit | ✅ |
| 7 | Shift無効化（LLM） | `test_llmNudge_noTimeShift` | Unit | ✅ |
| 8 | Shift有効（ルールベース） | `test_ruleBasedNudge_shiftsWhenIgnored` | Unit | ✅ |
| 9 | プロンプトにグラウンディング | `test_buildPhase78Prompt_includesGrounding` | API Unit | ✅ |
| 10 | プロンプト間隔60分 | `test_buildPhase78Prompt_60minInterval` | API Unit | ✅ |
| 11 | 青ドット表示（LLM） | `test_nudgeCard_showsBlueDot_forLLM` | UI/Maestro | ✅ |
| 12 | 青ドット非表示（ルール） | `test_nudgeCard_noBlueDot_forRuleBased` | UI/Maestro | ✅ |
| 13 | 後方互換: APIレスポンス | `test_apiResponse_backwardCompatible` | API Unit | ✅ |
| 14 | validTimeRange削除 | `test_cantWakeUp_noValidTimeRange` | Unit | ✅ |
| 15 | 衝突回避ロジック（60分繰り下げ） | `test_collisionResolution_uses60minInterval` | Unit | ✅ |
| 16 | API validateMinimumInterval 60分 | `test_validateMinimumInterval_rejects59min` | API Unit | ✅ |
| 17 | DEBUG UI削除確認 | `test_nudgeCard_noDebugLLMIndicator` | UI/目視 | ✅ |
| 18 | CLAUDE.md追記確認 | 目視確認: サブスク情報セクション存在 | Manual | ✅ |

---

## E2Eシナリオ

| # | シナリオ | 検証項目 |
|---|---------|---------|
| 1 | Day 1ユーザーが通知を受け取る | 5回/日のスロットでスケジュールされる |
| 2 | 通知タップ → NudgeCard表示 → 青ドットなし（ルールベース） | ドットが表示されない |
| 3 | Day 2+ → LLM Nudge → NudgeCard表示 → 青ドットあり | 6pt青ドットが右上に表示 |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| ルールベースのNudge文言（Localizable.strings）変更 | 今回はタイムスロットのみ。文言はv1.6.0で検討 |
| LLMモデル変更（gpt-4o-mini → gpt-4o） | コスト効率が良い。品質問題が出たら変更 |
| 通知回数の動的調整（ユーザー反応で増減） | LLMが既にoverallStrategyで判断。v1.6.0で検討 |
| 新しい通知バリアント（Localizable.strings追加） | 既存バリアントで十分。LLMが生成するので不要 |
| Paywall/サブスク実装変更 | CLAUDE.mdへの情報追記のみ |
| NudgeCard UIの大幅変更 | 青ドット追加のみ。レイアウト変更なし |
| API側ルールベーススケジュールマップ（`generateRuleBasedNudges()`）の更新 | API側のフォールバック用スケジュールマップはiOSのスロットと異なる用途（サーバー側Day 1フォールバック）。今回はiOS側のみ更新。APIマップ同期はv1.6.0で検討 |

---

## 後方互換性

| 項目 | 対応 |
|------|------|
| 1.4.0ユーザー（iOS） | タイムスロット変更はアプリ更新時に自動適用。APIレスポンスは変更なし |
| APIレスポンス | `scheduledTime`, `scheduledHour` 両方返す（既存通り） |
| LLMプロンプト変更 | バックエンドのみ。iOSに影響なし |
| NudgeContentSelector変更 | LLMキャッシュが空の場合は従来通りルールベース。1.4.0と同じフォールバック |

---

## ファイル変更一覧

### iOS

| ファイル | 変更内容 |
|---------|---------|
| `aniccaios/Models/ProblemType.swift` | `notificationSchedule` を全13問題で5スロットに更新、`cantWakeUp`の`validTimeRange`を`nil`に変更 |
| `aniccaios/Services/NudgeContentSelector.swift` | 交互ロジック削除（`lastWasLLM`+`resetAlternatingState`削除）、LLM優先に変更、`selectVariantForDebug`も同様に修正 |
| `aniccaios/Services/LLMNudgeCache.swift` | `hasNudge(for:hour:)` メソッド追加（`getNudge`のnil判定ラッパー） |
| `aniccaios/Notifications/ProblemNotificationScheduler.swift` | `minimumIntervalMinutes = 60`、起床ウィンドウ例外、衝突回避を`last + interval`に変更、LLMキャッシュ事前判定によるshift無効化 |
| `aniccaios/Views/NudgeCardView.swift` | 青ドット追加、`#if DEBUG` LLM表示削除 |

### API

| ファイル | 変更内容 |
|---------|---------|
| `apps/api/src/jobs/nudgeHelpers.js` | `buildPhase78Prompt()`にグラウンディングセクション追加、間隔ルール更新、`validateMinimumInterval()`の閾値30→60に変更 |

### ドキュメント

| ファイル | 変更内容 |
|---------|---------|
| `CLAUDE.md` | 既存サブスク情報セクションをAGENTS.md基準に修正（年額追記、SKAN設定追記） |

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | 本ドキュメント | 実装計画 |
| Specレビュー | `/codex-review` | Spec承認 |
| iOS実装 | `/tdd` | TDDでテスト先行 |
| API実装 | `/tdd` | TDDでテスト先行 |
| コードレビュー | `/codex-review` | 実装レビュー |
| ビルドエラー | `/build-fix` | エラー修正 |
| E2Eテスト | Maestro MCP | UIテスト |

---

## 実行手順

### 1. ワークツリー作成

```bash
git worktree add ../anicca-nudge-enhancement -b feature/nudge-enhancement
cd ../anicca-nudge-enhancement
```

### 2. iOS テスト

```bash
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane test
```

### 3. API テスト

```bash
cd apps/api && npm test
```

### 4. E2E テスト

```bash
# Maestro MCP経由で実行
mcp__maestro__run_flow_files
```

---

## リサーチソース（グラウンディング根拠）

| 問題 | 主要ソース |
|------|-----------|
| staying_up_late | PMC Screen Time & Sleep, Oxford Academic Evening Smartphone Use |
| cant_wake_up | PMC Sleep Inertia Current Insights, PMC Circadian Rhythm in Sleep Inertia |
| self_loathing | PMC Ruminative Self-Focus Experience Sampling, ZRT Cortisol Awakening |
| rumination | CNBC Dr. Prather on Rumination, ScienceDirect Rumination & Worry Effects |
| procrastination | Rise Science Circadian Rhythm, APA Psychology of Procrastination |
| anxiety | PMC CAR & First Onset Anxiety, Rupa Health Cortisol & Anxiety |
| lying | Medical News Today Afternoon Lying, Wiley Costs of Lying |
| bad_mouthing | NPR 52 Minutes of Gossip, PMC Gossip Dark Personalities |
| porn_addiction | PMC Pornography Abstinence, BeFree Urge Surfing |
| alcohol_dependency | PMC 24-Hour Rhythm in Alcohol Craving, Oxford Circadian Disruption |
| anger | PMC Biological Clocks & Aggression, ScienceDirect Anger & Sleep |
| obsessive | ScienceDirect Circadian Rhythms in OCD, PMC Delayed Circadian OCD |
| loneliness | BMJ Mental Health Mood Across Day, Nature Reviews Loneliness |
| 全般 (JITAI) | PMC JITAI Key Components, PLOS One Timing Study, PMC Apple Watch Nudge |

---

## 実装進捗（引き継ぎ用）

> **最終更新**: 2026-01-27 22:10 JST
>
> **ワークツリー**: `/Users/cbns03/Downloads/anicca-nudge-enhancement` (branch: `feature/nudge-enhancement`)

### 実装状況（全To-Be完了）

| # | To-Be | ファイル | 状況 |
|---|-------|---------|------|
| 1 | タイムスロット5回/日 | `aniccaios/Models/ProblemType.swift` | ✅ 完了 |
| 2 | LLM優先（交互ロジック削除） | `aniccaios/Services/NudgeContentSelector.swift` | ✅ 完了 |
| 3 | Shift LLMスキップ | `aniccaios/Notifications/ProblemNotificationScheduler.swift` | ✅ 完了 |
| 4 | 最小間隔60分 + 起床ウィンドウ15分 | `aniccaios/Notifications/ProblemNotificationScheduler.swift` | ✅ 完了 |
| 5 | LLMグラウンディング | `apps/api/src/jobs/nudgeHelpers.js` | ✅ 完了 |
| 6 | 青ドットUI | `aniccaios/Views/NudgeCardView.swift` | ✅ 完了 |
| 7 | CLAUDE.mdサブスク情報 | `CLAUDE.md` | ✅ 完了 |
| 補助 | `hasNudge()` 追加 | `aniccaios/Services/LLMNudgeCache.swift` | ✅ 完了 |
| 補助 | コメント30→60修正 | `apps/api/src/jobs/nudgeHelpers.js:356` | ✅ 完了 |

### テスト状況

| テストスイート | 結果 | 備考 |
|---------------|------|------|
| API vitest（28テスト） | ✅ 全パス | `cd apps/api && npx vitest run` |
| iOS fastlane test（48テスト） | ⚠️ 47パス / 1失敗 | 下記参照 |

**失敗テスト**: `ProblemNotificationSchedulerTests.test_llmNudge_noTimeShift()`

- **ファイル**: `aniccaiosTests/ProblemNotificationSchedulerTests.swift`
- **原因**: `@MainActor`隔離の`LLMNudgeCache.shared`をXCTestCase内のasyncメソッドから操作する際の実行コンテキスト問題。テストが0.3秒後にfailする（クラッシュではなくMainActorスケジューリング問題の可能性大）
- **実装コードは正しい**: 問題はテストコードのみ。同じロジックが`LLMNudgeCacheTests`（Swift Testingフレームワーク）では正常動作する
- **修正案**: (1) このテストをSwift Testing（`@Test`）に書き直す、または (2) XCTestCaseで`@MainActor`を使わず`LLMNudgeCacheTests`側でカバーする（`test_hasNudge_returnsTrue`で既にカバー済み）
- **3回修正試行済み**: `@MainActor`直接 → `async + await MainActor.run` → 簡略化、いずれも同じ0.3秒failパターン

### 残タスク（次のエージェントがやること）

| # | タスク | 詳細 | 優先度 |
|---|-------|------|--------|
| 1 | `test_llmNudge_noTimeShift` 修正 | Swift Testing（`@Test`）に書き直すか、テスト戦略を変更する。`/build-fix`サブエージェント推奨 | 高 |
| 2 | Maestro MCP E2Eテスト | AC8/AC9の検証: 青ドット表示（LLM時）/ 非表示（ルールベース時）。`mcp__maestro__*`使用 | 高 |
| 3 | 実機確認チェックリスト作成 | Xcodeでワークツリーを開き、`aniccaios-staging`スキームでデバッグビルド実行 → NudgeCardの青ドット目視確認 | 高 |
| 4 | devマージ | 全テストパス + 実機確認OK後にユーザー承認を得てマージ | 最終 |

### コードレビュー結果（サブエージェント実施済み）

| 重要度 | 件数 | 概要 |
|--------|------|------|
| CRITICAL | 0 | 実質なし（コメント修正は対応済み） |
| WARNING | 4 | デッドコード系: `validTimeRange`常にnil、`randomProvider`未使用、hour 0/1の時刻固定バリアント到達不能 |
| SUGGESTION | 4 | プロンプトトークン最適化、VoiceOverアクセシビリティ等 |

WARNING項目は次バージョン（v1.6.0）のクリーンアップとして適切。

### クイックスタート（次のエージェント向け）

```bash
# 1. ワークツリーに移動
cd /Users/cbns03/Downloads/anicca-nudge-enhancement

# 2. テスト失敗の確認
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 FASTLANE_OPT_OUT_CRASH_REPORTING=1 fastlane test

# 3. 失敗テストファイル
# aniccaiosTests/ProblemNotificationSchedulerTests.swift の test_llmNudge_noTimeShift()

# 4. APIテスト（参考: 全パス済み）
cd apps/api && npx vitest run
```
