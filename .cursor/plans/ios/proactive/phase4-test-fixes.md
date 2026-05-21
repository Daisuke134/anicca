# Phase 4 テスト修正仕様書

> **目的**: Phase 4 実装後のテストで発見された問題を修正するための完全なパッチ仕様
>
> **作成日**: 2026-01-21
>
> **最終更新**: 2026-01-21（パッチ修正済み）
>
> **ステータス**: ✅ レビュー完了・実装可能

---

## 目次

1. [問題1: デバッグ通知タップで画面遷移しない](#問題1-デバッグ通知タップで画面遷移しない)
2. [問題2: AlarmKitボタンタップで画面遷移しない + バックグラウンドスレッドエラー](#問題2-alarmkitボタンタップで画面遷移しない--バックグラウンドスレッドエラー)
3. [問題3: Mixpanelイベント名を分離](#問題3-mixpanelイベント名を分離)
4. [問題4: MyPathタブの日本語翻訳](#問題4-mypathタブの日本語翻訳)
5. [問題5: デバッグ用即時テスト機能追加](#問題5-デバッグ用即時テスト機能追加)

---

## 問題1: デバッグ通知タップで画面遷移しない

### As-Is（現状）

**ファイル**: `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

**行**: 283-285

```swift
/// 通知がProblem Nudgeかどうか判定
static func isProblemNudge(identifier: String) -> Bool {
    return identifier.hasPrefix("PROBLEM_")
}
```

**問題**:
- テスト通知のIDは `TEST_PROBLEM_{problemType}_{timestamp}` 形式
- `"TEST_PROBLEM_".hasPrefix("PROBLEM_")` は `false` を返す
- そのため `AppDelegate.didReceive` で Problem Nudge として認識されず、NudgeCard が表示されない

### To-Be（あるべき姿）

テスト通知も本番通知も同じ Problem Nudge として認識され、タップ時に NudgeCard が表示される。

### Patch

```diff
--- a/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift
+++ b/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift
@@ -281,6 +281,6 @@ final class ProblemNotificationScheduler {

     /// 通知がProblem Nudgeかどうか判定
     static func isProblemNudge(identifier: String) -> Bool {
-        return identifier.hasPrefix("PROBLEM_")
+        return identifier.hasPrefix("PROBLEM_") || identifier.hasPrefix("TEST_PROBLEM_")
     }
 }
```

### テスト方法

1. アプリ起動
2. Profile → 🔔 Nudge通知テスト（夜更かし）をタップ
3. 5秒後に通知が届く
4. 通知をタップ
5. **期待結果**: NudgeCard が表示される

---

## 問題2: AlarmKitボタンタップで画面遷移しない + バックグラウンドスレッドエラー

### As-Is（現状）

**ファイル**: `aniccaios/aniccaios/aniccaiosApp.swift`

**行**: 22-30

```swift
// AlarmKit「今日を始める」ボタンでOneScreenを開く
.onReceive(NotificationCenter.default.publisher(for: Notification.Name("OpenProblemOneScreen"))) { notification in
    guard let userInfo = notification.userInfo,
          let problemTypeRaw = userInfo["problemType"] as? String,
          let problemType = ProblemType(rawValue: problemTypeRaw) else { return }

    // OneScreenを表示
    let content = NudgeContent.contentForToday(for: problemType)
    appState.pendingNudgeCard = content
}
```

**問題**:
- `OpenProblemOneScreenIntent.perform()` はバックグラウンドスレッドで実行される
- `NotificationCenter.post` → Observer → `appState.pendingNudgeCard = content`
- `@Published` プロパティをバックグラウンドスレッドから更新 → エラー
- 結果: 画面遷移しない + コンソールに `Publishing changes from background threads is not allowed` エラー

### To-Be（あるべき姿）

AlarmKit のオレンジボタン（今日を始める）をタップすると、確実に NudgeCard が表示される。エラーなし。

### Patch

```diff
--- a/aniccaios/aniccaios/aniccaiosApp.swift
+++ b/aniccaios/aniccaios/aniccaiosApp.swift
@@ -19,10 +19,12 @@ struct aniccaiosApp: App {
                 .tint(AppTheme.Colors.accent)
                 // AlarmKit「今日を始める」ボタンでOneScreenを開く
                 .onReceive(NotificationCenter.default.publisher(for: Notification.Name("OpenProblemOneScreen"))) { notification in
                     guard let userInfo = notification.userInfo,
                           let problemTypeRaw = userInfo["problemType"] as? String,
                           let problemType = ProblemType(rawValue: problemTypeRaw) else { return }

-                    // OneScreenを表示
-                    let content = NudgeContent.contentForToday(for: problemType)
-                    appState.pendingNudgeCard = content
+                    // OneScreenを表示（MainActorで実行）
+                    Task { @MainActor in
+                        let content = NudgeContent.contentForToday(for: problemType)
+                        appState.pendingNudgeCard = content
+                    }
                 }
         }
     }
 }
```

### テスト方法

1. Profile → ⏰ アラームテスト → 2分後の時刻を設定 → アラーム設定
2. アプリをバックグラウンドにする
3. 設定した時刻にアラームが鳴る
4. オレンジボタン（☀️ 今日を始める）をタップ
5. **期待結果**:
   - NudgeCard（cant_wake_up）が表示される
   - コンソールに `Publishing changes from background threads` エラーが出ない

---

## 問題3: Mixpanelイベント名を分離

### As-Is（現状）

**ファイル1**: `aniccaios/aniccaios/Services/AnalyticsManager.swift`

```swift
// Nudge (Phase 4)
case nudgeTapped = "nudge_tapped"
case nudgeIgnored = "nudge_ignored"
case nudgeFeedback = "nudge_feedback"
```

**ファイル2**: `aniccaios/aniccaios/Services/NudgeStatsManager.swift`

**行**: 172-176 (recordThumbsUp)

```swift
AnalyticsManager.shared.track(.nudgeFeedback, properties: [
    "problem_type": problemType,
    "variant_index": variantIndex,
    "is_positive": true
])
```

**行**: 189-193 (recordThumbsDown)

```swift
AnalyticsManager.shared.track(.nudgeFeedback, properties: [
    "problem_type": problemType,
    "variant_index": variantIndex,
    "is_positive": false
])
```

**問題**:
- `nudge_feedback` という1つのイベントに `is_positive: true/false` を付けている
- Mixpanel での分析時に `nudge_positive_feedback` / `nudge_negative_feedback` として分けたい

### To-Be（あるべき姿）

- 👍 タップ → `nudge_positive_feedback` イベント
- 👎 タップ → `nudge_negative_feedback` イベント

### Patch

**ファイル1**: `AnalyticsManager.swift`

```diff
--- a/aniccaios/aniccaios/Services/AnalyticsManager.swift
+++ b/aniccaios/aniccaios/Services/AnalyticsManager.swift
@@ -103,7 +103,8 @@ enum AnalyticsEvent: String {
     // Nudge (Phase 4)
     case nudgeTapped = "nudge_tapped"
     case nudgeIgnored = "nudge_ignored"
-    case nudgeFeedback = "nudge_feedback"
+    case nudgePositiveFeedback = "nudge_positive_feedback"
+    case nudgeNegativeFeedback = "nudge_negative_feedback"
 }
```

**ファイル2**: `NudgeStatsManager.swift`

```diff
--- a/aniccaios/aniccaios/Services/NudgeStatsManager.swift
+++ b/aniccaios/aniccaios/Services/NudgeStatsManager.swift
@@ -169,10 +169,9 @@ final class NudgeStatsManager {
         }
         saveToStorage()

-        AnalyticsManager.shared.track(.nudgeFeedback, properties: [
+        AnalyticsManager.shared.track(.nudgePositiveFeedback, properties: [
             "problem_type": problemType,
-            "variant_index": variantIndex,
-            "is_positive": true
+            "variant_index": variantIndex
         ])
     }

@@ -186,10 +185,9 @@ final class NudgeStatsManager {
         }
         saveToStorage()

-        AnalyticsManager.shared.track(.nudgeFeedback, properties: [
+        AnalyticsManager.shared.track(.nudgeNegativeFeedback, properties: [
             "problem_type": problemType,
-            "variant_index": variantIndex,
-            "is_positive": false
+            "variant_index": variantIndex
         ])
     }
```

### テスト方法

1. NudgeCard を表示
2. 👍 ボタンをタップ
3. Xcode コンソールで `Tracked event: nudge_positive_feedback` を確認
4. 別の NudgeCard を表示
5. 👎 ボタンをタップ
6. Xcode コンソールで `Tracked event: nudge_negative_feedback` を確認

---

## 問題4: MyPathタブの日本語翻訳

### As-Is（現状）

**ファイル1**: `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`

**行**: 521

```
"tab_mypath" = "My Path";
```

**ファイル2**: `aniccaios/aniccaios/Views/MyPathTabView.swift`

**行**: 77

```swift
.navigationTitle("My Path")
```

**問題**:
- 日本語ローカライズファイルで `tab_mypath` が英語のまま
- `MyPathTabView` の `.navigationTitle` がハードコードされている

### To-Be（あるべき姿）

日本語環境では「マイパス」と表示される。

### Patch

**ファイル1**: `ja.lproj/Localizable.strings`

```diff
--- a/aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings
+++ b/aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings
@@ -518,7 +518,7 @@ "ema_yes" = "はい";
 "ema_no" = "いいえ";
 "ema_skip" = "スキップ";
 "tab_habits" = "習慣";
-"tab_mypath" = "My Path";
+"tab_mypath" = "マイパス";
 "tab_profile" = "プロファイル";
```

**ファイル2**: `MyPathTabView.swift`

```diff
--- a/aniccaios/aniccaios/Views/MyPathTabView.swift
+++ b/aniccaios/aniccaios/Views/MyPathTabView.swift
@@ -74,7 +74,7 @@ struct MyPathTabView: View {
                 .padding(.bottom, 100)
             }
-            .navigationTitle("My Path")
+            .navigationTitle(String(localized: "tab_mypath"))
             .background(AppBackground())
             .toolbar {
```

### テスト方法

1. 端末の言語設定を日本語にする
2. アプリを起動
3. **期待結果**:
   - タブバーに「マイパス」と表示
   - ナビゲーションタイトルに「マイパス」と表示

---

## 問題5: デバッグ用即時テスト機能追加

### As-Is（現状）

以下のテストが即時にできない:

| テスト項目 | 現状 |
|---------|-----|
| 時刻固定バリアント（0時→variant3, 1時→variant4） | 実際の時刻まで待つ必要あり |
| 2日連続ignored → 30分シフト | 2日待つ必要あり |
| 月変わり → カウントリセット | 月変わりまで待つ必要あり |
| 5回/10回完了 → Paywall | 5回/10回完了するまで待つ必要あり |

### To-Be（あるべき姿）

DEBUG モードで以下の機能が使える:

1. **時刻指定してNudge発火**: `scheduledHour` を指定して通知を発火
2. **ignored強制記録**: 任意の回数の ignored を記録
3. **月変わりシミュレート**: monthlyNudgeCount をリセット
4. **NudgeCard完了回数を設定**: 任意の回数を設定（Paywall テスト用）

### Patch

**ファイル1**: `NudgeStatsManager.swift` - DEBUG メソッド追加

> **注意**: `recordIgnored` は private のまま維持。`debugRecordIgnored` 内でロジックを複製する。

```diff
--- a/aniccaios/aniccaios/Services/NudgeStatsManager.swift
+++ b/aniccaios/aniccaios/Services/NudgeStatsManager.swift
@@ -248,5 +248,20 @@ final class NudgeStatsManager {
         saveToStorage()
         logger.info("All stats reset")
     }
+
+    /// DEBUG用: 指定回数のignoredを強制記録
+    func debugRecordIgnored(problemType: String, variantIndex: Int, scheduledHour: Int, count: Int) {
+        let key = "\(problemType)_\(variantIndex)_\(scheduledHour)"
+
+        var stat = stats[key] ?? NudgeStats(problemType: problemType, variantIndex: variantIndex, scheduledHour: scheduledHour)
+
+        for _ in 0..<count {
+            stat.ignoredCount += 1
+            stat.consecutiveIgnoredDays += 1
+        }
+
+        stats[key] = stat
+        saveToStorage()
+        logger.info("DEBUG: Recorded \(count) ignored for \(problemType), consecutiveIgnoredDays: \(stat.consecutiveIgnoredDays)")
+    }
     #endif
 }
```

**ファイル2**: `AppState.swift` - DEBUG メソッド追加

```diff
--- a/aniccaios/aniccaios/AppState.swift
+++ b/aniccaios/aniccaios/AppState.swift
@@ -末尾の #if DEBUG ブロック内に追加

     #if DEBUG
+    /// DEBUG用: NudgeCard完了回数を設定
+    func debugSetNudgeCardCompletedCount(_ count: Int) {
+        nudgeCardCompletedCount = count
+        defaults.set(count, forKey: nudgeCardCompletedCountKey)
+    }
+
+    /// DEBUG用: 月間NudgeCard完了回数を設定
+    func debugSetMonthlyNudgeCount(_ count: Int) {
+        monthlyNudgeCount = count
+        defaults.set(count, forKey: monthlyNudgeCountKey)
+    }
+
+    /// DEBUG用: 月変わりをシミュレート
+    func debugSimulateMonthChange() {
+        resetMonthlyNudgeCount()
+        Task {
+            await ProblemNotificationScheduler.shared.scheduleNotifications(for: userProfile.struggles)
+        }
+    }
     #endif
```

**ファイル3**: `ProblemNotificationScheduler.swift` - scheduledHour 指定テスト通知追加

> **注意**: 既存の `testNotification(for:)` メソッドを完全に置き換える。

```diff
--- a/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift
+++ b/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift
@@ -112,30 +112,53 @@ final class ProblemNotificationScheduler {
     #if DEBUG
     /// テスト用: 指定した問題の通知を5秒後に発火
     func testNotification(for problem: ProblemType) async {
-        let content = NudgeContent.contentForToday(for: problem)
-
-        let notificationContent = UNMutableNotificationContent()
-        notificationContent.title = problem.notificationTitle
-        notificationContent.body = content.notificationText
-        notificationContent.categoryIdentifier = Category.problemNudge.rawValue
-        notificationContent.sound = .default
-
-        notificationContent.userInfo = [
-            "problemType": problem.rawValue,
-            "notificationText": content.notificationText,
-            "detailText": content.detailText,
-            "variantIndex": content.variantIndex
-        ]
-
-        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
-        let identifier = "TEST_PROBLEM_\(problem.rawValue)_\(Date().timeIntervalSince1970)"
-        let request = UNNotificationRequest(identifier: identifier, content: notificationContent, trigger: trigger)
-
-        do {
-            try await center.add(request)
-            logger.info("Test notification scheduled for \(problem.rawValue)")
-        } catch {
-            logger.error("Failed to schedule test notification: \(error.localizedDescription)")
+        await testNotification(for: problem, scheduledHour: nil)
+    }
+
+    /// テスト用: 指定した問題・時刻の通知を5秒後に発火
+    func testNotification(for problem: ProblemType, scheduledHour: Int?) async {
+        // scheduledHour が指定されていれば、その時刻用のバリアントを選択
+        let variantIndex: Int
+        if let hour = scheduledHour {
+            variantIndex = await MainActor.run {
+                NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: hour)
+            }
+        } else {
+            variantIndex = NudgeContent.contentForToday(for: problem).variantIndex
         }
+
+        let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(variantIndex + 1)"
+        let detailTextKey = "nudge_\(problem.rawValue)_detail_\(variantIndex + 1)"
+
+        let notificationContent = UNMutableNotificationContent()
+        notificationContent.title = problem.notificationTitle
+        notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
+        notificationContent.categoryIdentifier = Category.problemNudge.rawValue
+        notificationContent.sound = .default
+
+        notificationContent.userInfo = [
+            "problemType": problem.rawValue,
+            "notificationTextKey": notificationTextKey,
+            "detailTextKey": detailTextKey,
+            "variantIndex": variantIndex,
+            "scheduledHour": scheduledHour ?? 0,
+            "scheduledMinute": 0
+        ]
+
+        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
+        let identifier = "TEST_PROBLEM_\(problem.rawValue)_\(Date().timeIntervalSince1970)"
+        let request = UNNotificationRequest(identifier: identifier, content: notificationContent, trigger: trigger)
+
+        do {
+            try await center.add(request)
+            logger.info("Test notification scheduled for \(problem.rawValue) variant:\(variantIndex) hour:\(scheduledHour ?? -1)")
+        } catch {
+            logger.error("Failed to schedule test notification: \(error.localizedDescription)")
+        }
     }
     #endif
```

**ファイル4**: `ProfileView.swift` - DEBUG セクションにテスト機能追加

```diff
--- a/aniccaios/aniccaios/Views/Profile/ProfileView.swift
+++ b/aniccaios/aniccaios/Views/Profile/ProfileView.swift
@@ 既存の recordingSection の後に追加

+    // MARK: - Phase 4 Debug Section
+    #if DEBUG
+    private var phase4DebugSection: some View {
+        VStack(spacing: 10) {
+            Text("🧪 Phase 4 デバッグ")
+                .font(.system(size: 14, weight: .medium))
+                .foregroundStyle(AppTheme.Colors.secondaryLabel)
+                .frame(maxWidth: .infinity, alignment: .leading)
+                .padding(.top, 16)
+
+            CardView {
+                VStack(spacing: 12) {
+                    // 時刻指定Nudgeテスト
+                    Text("時刻指定Nudgeテスト (stayingUpLate)")
+                        .font(.subheadline.weight(.medium))
+                        .frame(maxWidth: .infinity, alignment: .leading)
+
+                    HStack(spacing: 8) {
+                        Button("21時") {
+                            Task {
+                                await ProblemNotificationScheduler.shared.testNotification(for: .stayingUpLate, scheduledHour: 21)
+                            }
+                        }
+                        .buttonStyle(.bordered)
+
+                        Button("0時") {
+                            Task {
+                                await ProblemNotificationScheduler.shared.testNotification(for: .stayingUpLate, scheduledHour: 0)
+                            }
+                        }
+                        .buttonStyle(.bordered)
+
+                        Button("1時") {
+                            Task {
+                                await ProblemNotificationScheduler.shared.testNotification(for: .stayingUpLate, scheduledHour: 1)
+                            }
+                        }
+                        .buttonStyle(.bordered)
+                    }
+
+                    Divider()
+
+                    // ignored強制記録
+                    Text("ignored強制記録 (stayingUpLate, 21時)")
+                        .font(.subheadline.weight(.medium))
+                        .frame(maxWidth: .infinity, alignment: .leading)
+
+                    HStack(spacing: 8) {
+                        Button("1回") {
+                            NudgeStatsManager.shared.debugRecordIgnored(problemType: "staying_up_late", variantIndex: 0, scheduledHour: 21, count: 1)
+                        }
+                        .buttonStyle(.bordered)
+
+                        Button("2回") {
+                            NudgeStatsManager.shared.debugRecordIgnored(problemType: "staying_up_late", variantIndex: 0, scheduledHour: 21, count: 2)
+                        }
+                        .buttonStyle(.bordered)
+                    }

+                    Divider()

+                    // NudgeCard完了回数設定
+                    Text("NudgeCard完了回数: \(appState.nudgeCardCompletedCount)")
+                        .font(.subheadline.weight(.medium))
+                        .frame(maxWidth: .infinity, alignment: .leading)

+                    HStack(spacing: 8) {
+                        Button("2回") { appState.debugSetNudgeCardCompletedCount(2) }
+                            .buttonStyle(.bordered)
+                        Button("4回") { appState.debugSetNudgeCardCompletedCount(4) }
+                            .buttonStyle(.bordered)
+                        Button("9回") { appState.debugSetNudgeCardCompletedCount(9) }
+                            .buttonStyle(.bordered)
+                        Button("0") { appState.debugSetNudgeCardCompletedCount(0) }
+                            .buttonStyle(.bordered)
+                    }

+                    Divider()

+                    // 月間カウント
+                    Text("月間NudgeCard完了: \(appState.monthlyNudgeCount)")
+                        .font(.subheadline.weight(.medium))
+                        .frame(maxWidth: .infinity, alignment: .leading)

+                    HStack(spacing: 8) {
+                        Button("9回") { appState.debugSetMonthlyNudgeCount(9) }
+                            .buttonStyle(.bordered)
+                        Button("月変わり") { appState.debugSimulateMonthChange() }
+                            .buttonStyle(.bordered)
+                    }
+                }
+                .padding(.vertical, 4)
+            }
+        }
+    }
+    #endif
```

**ProfileView の body 内で phase4DebugSection を呼び出す**:

```diff
@@ ProfileView.swift の #if DEBUG ブロック内

 #if DEBUG
 recordingSection
 alarmTestSection
+phase4DebugSection
 #endif
```

**ファイル5**: `NudgeCardView.swift` - DEBUG用バリアント表示追加（確認用）

```diff
--- a/aniccaios/aniccaios/Views/NudgeCardView.swift
+++ b/aniccaios/aniccaios/Views/NudgeCardView.swift
@@ NudgeCardView の body 内、通知テキスト表示の近くに追加

+            #if DEBUG
+            Text("DEBUG: variant \(content.variantIndex)")
+                .font(.caption)
+                .foregroundStyle(.gray)
+            #endif
```

### テスト方法

**時刻固定バリアント**:
1. Profile → 🧪 Phase 4 デバッグ → 「0時」ボタンタップ
2. 5秒後に通知が届く → タップ
3. **期待結果**:
   - NudgeCard に「深夜0時を過ぎました」が表示
   - DEBUG表示で `variant 3` と表示される

**時刻固定バリアント（1時）**:
1. Profile → 🧪 Phase 4 デバッグ → 「1時」ボタンタップ
2. 5秒後に通知が届く → タップ
3. **期待結果**:
   - NudgeCard に「深夜1時です」が表示
   - DEBUG表示で `variant 4` と表示される

**2日連続ignored**:
1. Profile → 🧪 Phase 4 デバッグ → ignored強制記録「2回」をタップ
2. アプリを再起動（または通知を再スケジュール）
3. **期待結果**: stayingUpLate の 21時通知が 21:30 にシフト

**Paywall テスト（5回目）**:
1. Profile → 🧪 Phase 4 デバッグ → NudgeCard完了回数「4回」をタップ
2. NudgeCard を表示して完了
3. **期待結果**: Paywall が表示される

**Paywall テスト（10回目・月間上限）**:
1. Profile → 🧪 Phase 4 デバッグ → 月間NudgeCard完了「9回」をタップ
2. NudgeCard を表示して完了
3. **期待結果**: Paywall が表示される + 通知がキャンセルされる

**月変わりシミュレート**:
1. Profile → 🧪 Phase 4 デバッグ → 「月変わり」ボタンタップ
2. **期待結果**: 月間カウントが 0 にリセット + 通知が再スケジュール

---

## 実装順序

1. **問題1**: `ProblemNotificationScheduler.swift` の `isProblemNudge` 修正（1行）
2. **問題2**: `aniccaiosApp.swift` の MainActor 対応（3行）
3. **問題3**: `AnalyticsManager.swift` + `NudgeStatsManager.swift` のイベント名変更
4. **問題4**: `Localizable.strings` + `MyPathTabView.swift` の翻訳修正
5. **問題5**: デバッグ機能追加（複数ファイル）

---

## チェックリスト

実装後、以下を全て確認:

- [ ] デバッグ通知タップ → NudgeCard 表示
- [ ] AlarmKit ボタンタップ → NudgeCard 表示 + エラーなし
- [ ] 👍 タップ → `nudge_positive_feedback` イベント
- [ ] 👎 タップ → `nudge_negative_feedback` イベント
- [ ] 日本語で「マイパス」表示
- [ ] 時刻指定Nudge（0時） → variant 3 表示
- [ ] 時刻指定Nudge（1時） → variant 4 表示
- [ ] 完了回数4→5 → Paywall 表示
- [ ] 月間回数9→10 → Paywall + 通知停止
- [ ] 月変わり → カウントリセット

---

## 修正履歴

| 日付 | 内容 |
|------|------|
| 2026-01-21 | 初版作成 |
| 2026-01-21 | パッチ修正: (1) testNotification の未使用 `content` 変数削除、(2) recordIgnored の可視性変更を撤回し debugRecordIgnored 内でロジック複製、(3) NudgeCardView に DEBUG 用バリアント表示追加、(4) ProfileView の phase4DebugSection に #if DEBUG 追加 |

---

*このドキュメントはレビュー完了済みです。パッチは完全な diff 形式で記載されており、そのまま実装可能です。*
