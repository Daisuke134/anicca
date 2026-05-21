# Phase 6: LLM Debug Visibility Fix

## 概要

LLM生成Nudgeがデバッグテストで確認できない問題を修正する。

---

## 問題一覧

| # | 問題 | 症状 | 原因 |
|---|------|------|------|
| 1 | Nudge通知テストでLLM出ない | 全てルールベース | `testNotification()`がLLM無視 |
| 2 | カードで🤖マーク出ない | LLMかどうか見た目でわからない | 表示コードがない |
| 3 | 通知に🤖マークがない | LLM通知かどうかわからない | bodyに🤖を付けていない |
| 4 | 50%がランダム | 確認しづらい | 交互にすべき |
| 5 | 6件しかない | - | 正常（選択した問題数=6） |

---

## 修正内容

### Patch 1: NudgeContentSelector.swift - 交互ロジック

**変更点**:
- 50%ランダムから**交互切り替え**に変更
- 問題タイプ+時刻ごとにフラグを保持
- LLMキャッシュがない場合はルールベースにフォールバック（フラグは更新しない）

**実装済み**:
```swift
// Phase 6: 交互切り替え用フラグ（問題タイプ+時刻ごと）
private var lastWasLLM: [String: Bool] = [:]

func selectVariant(for problem: ProblemType, scheduledHour: Int) -> (...) {
    let key = "\(problem.rawValue)_\(scheduledHour)"

    // 交互切り替え: 前回がルールベースならLLMを試みる
    let shouldTryLLM = !(lastWasLLM[key] ?? false)

    if shouldTryLLM {
        if let llmNudge = LLMNudgeCache.shared.getNudge(...) {
            lastWasLLM[key] = true
            return (variantIndex: -1, isAIGenerated: true, content: llmNudge)
        }
        // LLMキャッシュがなければフォールバック（フラグは更新しない）
    }

    // ルールベース
    lastWasLLM[key] = false
    ...
}
```

---

### Patch 2: ProblemNotificationScheduler.swift - testNotification() LLM対応

**変更点**:
- `selectVariant()` の全結果を使用（`isAIGenerated`, `content` を無視しない）
- LLM通知の場合、bodyに🤖マークを追加
- `userInfo` に LLM 用のキーを設定

**実装済み**:
```swift
func testNotification(for problem: ProblemType, scheduledHour: Int?) async {
    let hour = scheduledHour ?? 9
    let selection = await MainActor.run {
        NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: hour)
    }

    if selection.isAIGenerated, let llmNudge = selection.content {
        // LLM生成の場合: 🤖マーク + LLMコンテンツ
        notificationContent.body = "🤖 " + llmNudge.hook
        notificationContent.userInfo = [
            "problemType": problem.rawValue,
            "isAIGenerated": true,
            "llmNudgeId": llmNudge.id,
            "notificationText": llmNudge.hook,
            "detailText": llmNudge.content,
            ...
        ]
    } else {
        // ルールベースの場合（既存ロジック）
        ...
    }
}
```

---

### Patch 3: NudgeCardView.swift - 🤖マーク表示

**変更点**:
- アイコンの右上に🤖マークを表示（DEBUG ビルドのみ）
- タイトルの横に "(LLM)" テキストを表示（DEBUG ビルドのみ）

**実装済み**:
```swift
VStack(spacing: 12) {
    ZStack(alignment: .topTrailing) {
        Text(content.problemType.icon)
            .font(.system(size: 48))

        #if DEBUG
        if content.isAIGenerated {
            Text("🤖")
                .font(.system(size: 16))
                .offset(x: 8, y: -8)
        }
        #endif
    }

    HStack(spacing: 4) {
        Text(content.problemType.notificationTitle)
            ...

        #if DEBUG
        if content.isAIGenerated {
            Text("(LLM)")
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.blue)
        }
        #endif
    }
}
```

---

### Patch 4: AppDelegate.swift（通知タップハンドラー）

**修正不要** - 既に対応済み

`ProblemNotificationScheduler.nudgeContent(from:)` が `isAIGenerated`、`notificationText`、`detailText` キーを読み取る実装が既に存在する。

---

## テストマトリックス

| # | テスト | 1回目 | 2回目 | 3回目 | 4回目 |
|---|--------|-------|-------|-------|-------|
| 1 | 21時ボタン | 🤖 LLM | 📋 ルール | 🤖 LLM | 📋 ルール |
| 2 | 通知body | "🤖 [LLMテキスト]" | "[ルールテキスト]" | "🤖 [LLMテキスト]" | "[ルールテキスト]" |
| 3 | カード | 🤖マークあり | 🤖マークなし | 🤖マークあり | 🤖マークなし |
| 4 | 1枚画面テスト | 🤖マークあり | 🤖マークなし | 🤖マークあり | 🤖マークなし |

**注意**: LLMキャッシュが空の場合はルールベースにフォールバックし、次回もLLMを試みる（交互カウントはスキップ）。

---

## 実行手順

```bash
# 1. ビルド
cd aniccaios && xcodebuild build \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' \
  -quiet

# 2. 実機デプロイ
cd aniccaios && fastlane build_for_device

# 3. テスト
# - Profile > Phase 4/5 デバッグ > 21時ボタン（4回連続で押して交互確認）
# - 通知が来たら🤖マークの有無を確認
# - 通知タップでカードを開き、🤖マークの有無を確認
# - 1枚画面テストボタンでカード表示、交互に🤖マークが出ることを確認
```

---

## レビューチェックリスト

- [x] `NudgeContentSelector` が交互ロジックを実装している
- [x] `testNotification()` が LLM 対応している
- [x] 通知の body に🤖マークが付く（LLMの場合）
- [x] 通知の `userInfo` に `isAIGenerated` フラグがある
- [x] 通知タップ時のハンドラーが `isAIGenerated` を読み取る（既存）
- [x] `NudgeCardView` が DEBUG ビルドで🤖を表示する
- [x] 既存のルールベースロジックが壊れていない
- [x] 1枚画面テストが交互に動作する

---

最終更新: 2026-01-24（交互ロジック実装、🤖マーク通知対応）
