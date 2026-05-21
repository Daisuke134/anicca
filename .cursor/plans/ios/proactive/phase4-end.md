# Phase 4 完全実装仕様書

> **目的**: この文書を読んだエージェントが、追加の質問なしでPhase 4を完全に実装できること
>
> **最終更新**: 2026-01-21

---

## 目次

1. [概要](#1-概要)
2. [ファイル一覧](#2-ファイル一覧)
3. [Task 0: AnalyticsEvent 追加](#task-0-analyticsevent-追加)
4. [Task 1: 通知言語問題修正](#task-1-通知言語問題修正)
5. [Task 2: 時刻特有メッセージ修正](#task-2-時刻特有メッセージ修正)
6. [Task 3: カッコ削除](#task-3-カッコ削除)
7. [Task 4: nudge_tapped 実装](#task-4-nudge_tapped-実装)
8. [Task 5: nudge_ignored 推定](#task-5-nudge_ignored-推定)
9. [Task 6: NudgeStats モデル](#task-6-nudgestats-モデル)
10. [Task 7: ルールベース通知選択](#task-7-ルールベース通知選択)
11. [Task 8: ルールベースContent選択](#task-8-ルールベースcontent選択)
12. [Task 9: タイミング最適化](#task-9-タイミング最適化)
13. [Task 10: 課金ロジック](#task-10-課金ロジック)
14. [Task 11: Paywall Placement更新](#task-11-paywall-placement更新)
15. [テストケース](#テストケース)
16. [実装順序](#実装順序)

---

## 1. 概要

### 背景

Phase 4では以下の問題を解決する：

1. **言語バグ**: 端末を日本語にしても通知が英語で表示される
2. **時刻バグ**: 「深夜1時です」が21時に表示される
3. **学習なし**: どのバリアントが効果的かのフィードバックループがない

### ゴール

- 日本語ユーザーに日本語で通知が届く
- 時刻特有メッセージが正しい時刻に届く
- ルールベースの自律改善が開始される

---

## 2. ファイル一覧

### 変更するファイル

| ファイル | 変更内容 |
|---------|---------|
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/AnalyticsManager.swift` | Nudge用イベントケース追加 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift` | userInfoにキーを保存、NudgeContentSelector使用 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Models/NudgeContent.swift` | キーからテキスト解決、scheduledHour対応 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Views/NudgeCardView.swift` | カッコ削除 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/AppDelegate.swift` | nudge_tapped記録追加 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/AppState.swift` | 起動時チェック、課金カウンター追加 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/SuperwallManager.swift` | Placement更新 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/MainTabView.swift` | NudgeCard完了時のPaywall/レビュー処理、handleAppOpenPaywall削除 |

### 新規作成ファイル

| ファイル | 内容 |
|---------|------|
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/NudgeStatsManager.swift` | 統計データ管理 |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/NudgeContentSelector.swift` | バリアント選択ロジック |

### ローカライゼーションファイル（変更なし、参照のみ）

| ファイル | 内容 |
|---------|------|
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings` | 日本語文字列（既存） |
| `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Resources/en.lproj/Localizable.strings` | 英語文字列（既存） |

---

## Task 0: AnalyticsEvent 追加

### 問題

`AnalyticsEvent` enum に Nudge 用のイベントケースがない。

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/AnalyticsManager.swift`

**行**: enum AnalyticsEvent の末尾（185行付近）

```swift
// As-Is: enum AnalyticsEvent の末尾
    // Engagement
    case talkTabOpened = "talk_tab_opened"
    case settingsOpened = "settings_opened"
}

// To-Be: 以下の3ケースを追加
    // Engagement
    case talkTabOpened = "talk_tab_opened"
    case settingsOpened = "settings_opened"

    // Nudge (Phase 4)
    case nudgeTapped = "nudge_tapped"
    case nudgeIgnored = "nudge_ignored"
    case nudgeFeedback = "nudge_feedback"
}
```

---

## Task 1: 通知言語問題修正

### 問題

`NSLocalizedString`がスケジュール時に解決され、言語変更後も古い言語で配信される。

### 原因箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

**行**: 152-166

```swift
// As-Is (現状)
let content = NudgeContent.contentForToday(for: problem)

let notificationContent = UNMutableNotificationContent()
notificationContent.title = problem.notificationTitle  // ← 既に解決された文字列
notificationContent.body = content.notificationText    // ← 既に解決された文字列

notificationContent.userInfo = [
    "problemType": problem.rawValue,
    "notificationText": content.notificationText,      // ← 文字列を保存
    "detailText": content.detailText,                  // ← 文字列を保存
    "variantIndex": content.variantIndex
]
```

### 修正方法

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

```swift
// To-Be (修正後)
// scheduleNotification メソッド内

private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // cantWakeUp + AlarmKit許可済み + トグルON → AlarmKitに委譲
    if problem == .cantWakeUp {
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            let manager = AlarmManager.shared
            if manager.authorizationState == .authorized,
               AppState.shared.userProfile.useAlarmKitForCantWakeUp {
                if hour == 6 && minute == 0 {
                    await ProblemAlarmKitScheduler.shared.scheduleCantWakeUp(hour: hour, minute: minute)
                }
                return
            }
        }
        #endif
    }

    // NudgeContentSelectorでバリアント選択（Task 7で実装）
    let variantIndex = await MainActor.run {
        NudgeContentSelector.shared.selectVariant(for: problem, scheduledHour: hour)
    }

    // キーを生成（文字列ではなくキーを保存）
    let notificationTextKey = "nudge_\(problem.rawValue)_notification_\(variantIndex + 1)"
    let detailTextKey = "nudge_\(problem.rawValue)_detail_\(variantIndex + 1)"
    let titleKey = "problem_\(problem.rawValue)_notification_title"

    let notificationContent = UNMutableNotificationContent()
    // 通知のtitle/bodyはスケジュール時に解決（iOS通知センターに表示されるため）
    notificationContent.title = NSLocalizedString(titleKey, comment: "")
    notificationContent.body = NSLocalizedString(notificationTextKey, comment: "")
    notificationContent.categoryIdentifier = Category.problemNudge.rawValue
    notificationContent.sound = .default

    // userInfo にキーを保存（表示時に再解決）
    notificationContent.userInfo = [
        "problemType": problem.rawValue,
        "notificationTextKey": notificationTextKey,
        "detailTextKey": detailTextKey,
        "variantIndex": variantIndex,
        "scheduledHour": hour,
        "scheduledMinute": minute
    ]

    if #available(iOS 15.0, *) {
        notificationContent.interruptionLevel = .active
    }

    var dateComponents = DateComponents()
    dateComponents.hour = hour
    dateComponents.minute = minute
    let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)

    let identifier = "PROBLEM_\(problem.rawValue)_\(hour)_\(minute)"
    let request = UNNotificationRequest(
        identifier: identifier,
        content: notificationContent,
        trigger: trigger
    )

    do {
        try await center.add(request)
        logger.info("Scheduled problem notification: \(problem.rawValue) at \(hour):\(minute) variant:\(variantIndex)")

        // スケジュール成功時にNudgeStatsに記録（Task 6で実装）
        await MainActor.run {
            NudgeStatsManager.shared.recordScheduled(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                scheduledHour: hour
            )
        }
    } catch {
        logger.error("Failed to schedule problem notification: \(error.localizedDescription)")
    }
}
```

### NudgeContent.swift の修正

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Models/NudgeContent.swift`

```swift
// As-Is: nudgeContent(from:) メソッド（行 210-225）
static func nudgeContent(from userInfo: [AnyHashable: Any]) -> NudgeContent? {
    guard let problemRaw = userInfo["problemType"] as? String,
          let problem = ProblemType(rawValue: problemRaw),
          let notificationText = userInfo["notificationText"] as? String,
          let detailText = userInfo["detailText"] as? String,
          let variantIndex = userInfo["variantIndex"] as? Int else {
        return nil
    }

    return NudgeContent(
        problemType: problem,
        notificationText: notificationText,
        detailText: detailText,
        variantIndex: variantIndex
    )
}

// To-Be: キーから解決するように修正
static func nudgeContent(from userInfo: [AnyHashable: Any]) -> NudgeContent? {
    guard let problemRaw = userInfo["problemType"] as? String,
          let problem = ProblemType(rawValue: problemRaw),
          let variantIndex = userInfo["variantIndex"] as? Int else {
        return nil
    }

    // 新形式: キーから解決
    if let notificationTextKey = userInfo["notificationTextKey"] as? String,
       let detailTextKey = userInfo["detailTextKey"] as? String {
        let notificationText = NSLocalizedString(notificationTextKey, comment: "")
        let detailText = NSLocalizedString(detailTextKey, comment: "")

        return NudgeContent(
            problemType: problem,
            notificationText: notificationText,
            detailText: detailText,
            variantIndex: variantIndex
        )
    }

    // 後方互換: 古い形式（文字列直接保存）
    if let notificationText = userInfo["notificationText"] as? String,
       let detailText = userInfo["detailText"] as? String {
        return NudgeContent(
            problemType: problem,
            notificationText: notificationText,
            detailText: detailText,
            variantIndex: variantIndex
        )
    }

    return nil
}
```

---

## Task 2: 時刻特有メッセージ修正

### 問題

`stayingUpLate`のvariant_4「深夜0時を過ぎました」とvariant_5「深夜1時です」が、日付ベースのローテーションで間違った時刻に配信される。

### 原因箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Models/NudgeContent.swift`

**行**: 26-31

```swift
// As-Is (現状)
static func contentForToday(for problem: ProblemType) -> NudgeContent {
    let dayOfYear = Calendar.current.ordinality(of: .day, in: .year, for: Date()) ?? 1
    let messages = notificationMessages(for: problem)
    let index = (dayOfYear - 1) % max(1, messages.count)  // ← 時刻無関係！
    return content(for: problem, variantIndex: index)
}
```

### 修正方法

この修正はTask 7（NudgeContentSelector）で実装する。`contentForToday`は削除しないが、スケジューラはNudgeContentSelectorを使用する。

**時刻とバリアントのマッピング（stayingUpLate）**:

| scheduledHour | variantIndex | メッセージ |
|---------------|--------------|----------|
| 21 | 0, 1, 2 のいずれか（tap率ベース） | 汎用 |
| 22 | 0, 1, 2 のいずれか（tap率ベース） | 汎用 |
| 0 | **3 (固定)** | 「深夜0時を過ぎました」 |
| 1 | **4 (固定)** | 「深夜1時です」 |

---

## Task 3: カッコ削除

### 問題

NudgeCardViewで通知テキストが「」で囲まれている。

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Views/NudgeCardView.swift`

**行**: 58

```swift
// As-Is
Text("「\(content.notificationText)」")
    .font(.system(size: 22, weight: .semibold))

// To-Be
Text(content.notificationText)
    .font(.system(size: 22, weight: .semibold))
```

---

## Task 4: nudge_tapped 実装

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/AppDelegate.swift`

**行**: 67-92 (didReceive メソッド内)

```swift
// As-Is
if ProblemNotificationScheduler.isProblemNudge(identifier: notificationIdentifier) {
    switch identifier {
    case UNNotificationDefaultActionIdentifier,
         NotificationScheduler.Action.startConversation.rawValue:
        if let nudgeContent = ProblemNotificationScheduler.nudgeContent(from: content.userInfo) {
            Task { @MainActor in
                AppState.shared.showNudgeCard(nudgeContent)
            }
        }
    // ...
    }
    return
}

// To-Be
if ProblemNotificationScheduler.isProblemNudge(identifier: notificationIdentifier) {
    switch identifier {
    case UNNotificationDefaultActionIdentifier,
         NotificationScheduler.Action.startConversation.rawValue:
        if let nudgeContent = ProblemNotificationScheduler.nudgeContent(from: content.userInfo) {
            // nudge_tapped を記録
            let scheduledHour = content.userInfo["scheduledHour"] as? Int ?? 0
            Task { @MainActor in
                // NudgeStats に記録
                NudgeStatsManager.shared.recordTapped(
                    problemType: nudgeContent.problemType.rawValue,
                    variantIndex: nudgeContent.variantIndex,
                    scheduledHour: scheduledHour
                )

                // Mixpanel に送信
                AnalyticsManager.shared.track(.nudgeTapped, properties: [
                    "problem_type": nudgeContent.problemType.rawValue,
                    "variant_index": nudgeContent.variantIndex,
                    "scheduled_hour": scheduledHour
                ])

                // NudgeCard を表示
                AppState.shared.showNudgeCard(nudgeContent)
            }
        }
    case NotificationScheduler.Action.dismissAll.rawValue,
         UNNotificationDismissActionIdentifier:
        break
    default:
        break
    }
    return
}
```

---

## Task 5: nudge_ignored 推定

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/AppState.swift`

**init() 内に追加** (行70-100付近)

```swift
// To-Be: init() の最後に追加
private init() {
    // ... 既存のコード ...

    // アプリ起動時にignored判定を実行
    Task {
        await NudgeStatsManager.shared.checkAndRecordIgnored()
    }
}
```

**NudgeStatsManagerに実装** (Task 6で詳細)

---

## Task 6: NudgeStats モデル

### 新規ファイル作成

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/NudgeStatsManager.swift`

```swift
import Foundation
import OSLog

/// Nudge統計データ
struct NudgeStats: Codable, Equatable {
    let problemType: String
    let variantIndex: Int
    let scheduledHour: Int

    var tappedCount: Int = 0
    var ignoredCount: Int = 0
    var thumbsUpCount: Int = 0
    var thumbsDownCount: Int = 0
    var consecutiveIgnoredDays: Int = 0
    var lastTappedDate: Date?
    var lastScheduledDate: Date?

    /// tap率を計算
    var tapRate: Double {
        let total = tappedCount + ignoredCount
        guard total > 0 else { return 0.5 }
        return Double(tappedCount) / Double(total)
    }

    /// 👍率を計算
    var thumbsUpRate: Double {
        let total = thumbsUpCount + thumbsDownCount
        guard total > 0 else { return 0.5 }
        return Double(thumbsUpCount) / Double(total)
    }

    /// 総サンプル数
    var totalSamples: Int {
        tappedCount + ignoredCount
    }

    /// 一意キー
    var key: String {
        "\(problemType)_\(variantIndex)_\(scheduledHour)"
    }
}

/// スケジュールされたNudge（ignored判定用）
struct ScheduledNudge: Codable {
    let problemType: String
    let variantIndex: Int
    let scheduledHour: Int
    let scheduledDate: Date
    var wasTapped: Bool = false
}

/// Nudge統計管理
@MainActor
final class NudgeStatsManager {
    static let shared = NudgeStatsManager()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeStats")
    private let queue = DispatchQueue(label: "com.anicca.nudgeStats", qos: .utility)

    // Storage keys
    private let statsKey = "com.anicca.nudgeStats"
    private let scheduledKey = "com.anicca.scheduledNudges"

    // In-memory cache
    private var stats: [String: NudgeStats] = [:]
    private var scheduledNudges: [String: ScheduledNudge] = [:]

    private init() {
        loadFromStorage()
    }

    // MARK: - Public API

    /// 通知スケジュール成功時に記録
    func recordScheduled(problemType: String, variantIndex: Int, scheduledHour: Int) {
        let key = "\(problemType)_\(variantIndex)_\(scheduledHour)"
        let nudge = ScheduledNudge(
            problemType: problemType,
            variantIndex: variantIndex,
            scheduledHour: scheduledHour,
            scheduledDate: Date()
        )
        scheduledNudges[key] = nudge

        // statsも更新
        var stat = stats[key] ?? NudgeStats(problemType: problemType, variantIndex: variantIndex, scheduledHour: scheduledHour)
        stat.lastScheduledDate = Date()
        stats[key] = stat

        saveToStorage()
        logger.info("Recorded scheduled: \(key)")
    }

    /// 通知タップ時に記録
    func recordTapped(problemType: String, variantIndex: Int, scheduledHour: Int) {
        let key = "\(problemType)_\(variantIndex)_\(scheduledHour)"

        // scheduledNudgesを更新
        if var nudge = scheduledNudges[key] {
            nudge.wasTapped = true
            scheduledNudges[key] = nudge
        }

        // statsを更新
        var stat = stats[key] ?? NudgeStats(problemType: problemType, variantIndex: variantIndex, scheduledHour: scheduledHour)
        stat.tappedCount += 1
        stat.consecutiveIgnoredDays = 0  // リセット
        stat.lastTappedDate = Date()
        stats[key] = stat

        saveToStorage()
        logger.info("Recorded tapped: \(key), tapRate: \(stat.tapRate)")
    }

    /// ignored判定（アプリ起動時に呼び出す）
    func checkAndRecordIgnored() async {
        let now = Date()
        let calendar = Calendar.current

        for (key, nudge) in scheduledNudges {
            // 24時間以上前 & 未tapped = ignored
            guard let scheduledDate = nudge.scheduledDate as Date?,
                  !nudge.wasTapped,
                  let hoursDiff = calendar.dateComponents([.hour], from: scheduledDate, to: now).hour,
                  hoursDiff >= 24 else {
                continue
            }

            recordIgnored(
                problemType: nudge.problemType,
                variantIndex: nudge.variantIndex,
                scheduledHour: nudge.scheduledHour
            )

            // Mixpanelに送信
            AnalyticsManager.shared.track(.nudgeIgnored, properties: [
                "problem_type": nudge.problemType,
                "variant_index": nudge.variantIndex,
                "scheduled_hour": nudge.scheduledHour
            ])

            // scheduledNudgesから削除
            scheduledNudges.removeValue(forKey: key)
        }

        saveToStorage()
    }

    /// ignored記録
    private func recordIgnored(problemType: String, variantIndex: Int, scheduledHour: Int) {
        let key = "\(problemType)_\(variantIndex)_\(scheduledHour)"

        var stat = stats[key] ?? NudgeStats(problemType: problemType, variantIndex: variantIndex, scheduledHour: scheduledHour)
        stat.ignoredCount += 1
        stat.consecutiveIgnoredDays += 1
        stats[key] = stat

        logger.info("Recorded ignored: \(key), consecutiveIgnoredDays: \(stat.consecutiveIgnoredDays)")
    }

    /// 👍記録
    func recordThumbsUp(problemType: String, variantIndex: Int) {
        // scheduledHourは不明なので、全時間帯の同じvariantを更新
        for (key, var stat) in stats {
            if stat.problemType == problemType && stat.variantIndex == variantIndex {
                stat.thumbsUpCount += 1
                stats[key] = stat
            }
        }
        saveToStorage()

        AnalyticsManager.shared.track(.nudgeFeedback, properties: [
            "problem_type": problemType,
            "variant_index": variantIndex,
            "is_positive": true
        ])
    }

    /// 👎記録
    func recordThumbsDown(problemType: String, variantIndex: Int) {
        for (key, var stat) in stats {
            if stat.problemType == problemType && stat.variantIndex == variantIndex {
                stat.thumbsDownCount += 1
                stats[key] = stat
            }
        }
        saveToStorage()

        AnalyticsManager.shared.track(.nudgeFeedback, properties: [
            "problem_type": problemType,
            "variant_index": variantIndex,
            "is_positive": false
        ])
    }

    /// 統計取得
    func getStats(problemType: String, variantIndex: Int, hour: Int) -> NudgeStats? {
        let key = "\(problemType)_\(variantIndex)_\(hour)"
        return stats[key]
    }

    /// 問題タイプの全バリアント統計取得
    func getAllStats(for problemType: String, hour: Int) -> [NudgeStats] {
        return stats.values.filter { $0.problemType == problemType && $0.scheduledHour == hour }
    }

    /// 時間帯の連続ignored日数取得
    func getConsecutiveIgnoredDays(problemType: String, hour: Int) -> Int {
        let hourStats = stats.values.filter { $0.problemType == problemType && $0.scheduledHour == hour }
        return hourStats.map { $0.consecutiveIgnoredDays }.max() ?? 0
    }

    // MARK: - Storage

    private func loadFromStorage() {
        let defaults = UserDefaults.standard

        if let data = defaults.data(forKey: statsKey),
           let decoded = try? JSONDecoder().decode([String: NudgeStats].self, from: data) {
            stats = decoded
        }

        if let data = defaults.data(forKey: scheduledKey),
           let decoded = try? JSONDecoder().decode([String: ScheduledNudge].self, from: data) {
            scheduledNudges = decoded
        }
    }

    private func saveToStorage() {
        queue.async { [stats, scheduledNudges] in
            let defaults = UserDefaults.standard

            if let data = try? JSONEncoder().encode(stats) {
                defaults.set(data, forKey: self.statsKey)
            }

            if let data = try? JSONEncoder().encode(scheduledNudges) {
                defaults.set(data, forKey: self.scheduledKey)
            }
        }
    }

    // MARK: - Debug

    #if DEBUG
    func resetAllStats() {
        stats = [:]
        scheduledNudges = [:]
        saveToStorage()
        logger.info("All stats reset")
    }
    #endif
}
```

---

## Task 7: ルールベース通知選択

### 新規ファイル作成

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/NudgeContentSelector.swift`

```swift
import Foundation
import OSLog

/// Nudgeコンテンツ選択ロジック
@MainActor
final class NudgeContentSelector {
    static let shared = NudgeContentSelector()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "NudgeContentSelector")

    private init() {}

    /// 問題タイプと時刻からベストなバリアントを選択
    func selectVariant(for problem: ProblemType, scheduledHour: Int) -> Int {
        // 1. 時刻固定バリアントをチェック
        if let fixedVariant = getTimeSpecificVariant(problem: problem, hour: scheduledHour) {
            logger.info("Selected time-specific variant \(fixedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
            return fixedVariant
        }

        // 2. 汎用バリアントから選択
        let genericVariants = getGenericVariantIndices(for: problem)
        guard !genericVariants.isEmpty else {
            return 0
        }

        // 3. データ量に応じた選択戦略
        let selectedVariant = selectByDataLevel(
            variants: genericVariants,
            problem: problem,
            hour: scheduledHour
        )

        logger.info("Selected variant \(selectedVariant) for \(problem.rawValue) at hour \(scheduledHour)")
        return selectedVariant
    }

    // MARK: - Time-Specific Variants

    /// 時刻固定バリアントを返す（該当しない場合はnil）
    private func getTimeSpecificVariant(problem: ProblemType, hour: Int) -> Int? {
        switch problem {
        case .stayingUpLate:
            // 深夜0時 → variant_4（インデックス3）
            if hour == 0 { return 3 }
            // 深夜1時 → variant_5（インデックス4）
            if hour == 1 { return 4 }
            return nil
        default:
            return nil
        }
    }

    /// 汎用バリアントのインデックス配列を返す
    private func getGenericVariantIndices(for problem: ProblemType) -> [Int] {
        switch problem {
        case .stayingUpLate:
            // variant_1, 2, 3 (インデックス0, 1, 2) が汎用
            return [0, 1, 2]
        case .cantWakeUp:
            return [0, 1, 2]
        case .selfLoathing:
            return [0, 1, 2]
        case .rumination:
            return [0, 1, 2]
        case .procrastination:
            return [0, 1, 2]
        case .anxiety:
            return [0, 1, 2]
        case .lying:
            return [0]  // 1種類のみ
        case .badMouthing:
            return [0, 1]
        case .pornAddiction:
            return [0, 1]
        case .alcoholDependency:
            return [0, 1]
        case .anger:
            return [0, 1]
        case .obsessive:
            return [0, 1, 2]
        case .loneliness:
            return [0, 1]
        }
    }

    // MARK: - Data-Level Selection

    /// データ量に応じた選択戦略
    private func selectByDataLevel(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        // 各バリアントのサンプル数を取得
        let variantSamples = variants.map { variantIndex -> (Int, Int) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            let samples = stats?.totalSamples ?? 0
            return (variantIndex, samples)
        }

        let minSamples = variantSamples.map { $0.1 }.min() ?? 0
        let totalSamples = variantSamples.map { $0.1 }.reduce(0, +)

        // Phase A: 全バリアントが最低3回ずつ試されるまで
        // → 最もサンプル数が少ないバリアントを優先
        if minSamples < 3 {
            let leastTested = variantSamples.filter { $0.1 == minSamples }
            if let selected = leastTested.randomElement() {
                logger.info("Phase A (exploration): selected least tested variant \(selected.0)")
                return selected.0
            }
        }

        // Phase B: 全バリアントが3回以上 & 合計15回未満
        // → 50%活用 / 50%探索
        if totalSamples < 15 {
            if Double.random(in: 0...1) < 0.5 {
                logger.info("Phase B (50/50): exploitation")
                return selectByTapRate(variants: variants, problem: problem, hour: hour)
            } else {
                logger.info("Phase B (50/50): exploration")
                return variants.randomElement() ?? variants[0]
            }
        }

        // Phase C: 合計15回以上
        // → 80%活用 / 20%探索
        if Double.random(in: 0...1) < 0.8 {
            logger.info("Phase C (80/20): exploitation")
            return selectByTapRate(variants: variants, problem: problem, hour: hour)
        } else {
            logger.info("Phase C (80/20): exploration")
            return variants.randomElement() ?? variants[0]
        }
    }

    /// tap率ベースで選択
    private func selectByTapRate(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        let variantRates = variants.map { variantIndex -> (Int, Double) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            let tapRate = stats?.tapRate ?? 0.5
            return (variantIndex, tapRate)
        }

        // 最高tap率のバリアントを選択
        if let best = variantRates.max(by: { $0.1 < $1.1 }) {
            return best.0
        }

        return variants[0]
    }

    // MARK: - Content Selection (Task 8)

    /// 👍率ベースでdetailを選択（通知とペアなので同じvariantIndexを使用）
    /// Phase 4ではペアのまま運用。将来的に分離可能。
    func selectContentVariant(for problem: ProblemType, notificationVariant: Int) -> Int {
        // 現在はnotificationとdetailはペア
        return notificationVariant
    }

    /// 複合スコアで選択（tap率 70% + 👍率 30%）
    func selectByCompositeScore(variants: [Int], problem: ProblemType, hour: Int) -> Int {
        let variantScores = variants.map { variantIndex -> (Int, Double) in
            let stats = NudgeStatsManager.shared.getStats(
                problemType: problem.rawValue,
                variantIndex: variantIndex,
                hour: hour
            )
            let tapRate = stats?.tapRate ?? 0.5
            let thumbsUpRate = stats?.thumbsUpRate ?? 0.5
            let score = tapRate * 0.7 + thumbsUpRate * 0.3
            return (variantIndex, score)
        }

        if let best = variantScores.max(by: { $0.1 < $1.1 }) {
            return best.0
        }

        return variants[0]
    }
}
```

---

## Task 8: ルールベースContent選択

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/MainTabView.swift`

NudgeCard表示部分を探し、onFeedback の処理を追加。

Task 11 の完全な MainTabView パッチに含まれる。

---

## Task 9: タイミング最適化

### 修正箇所

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift`

`scheduleNotifications` メソッド内でタイミング調整を追加：

```swift
// To-Be: scheduleNotifications メソッド全体

func scheduleNotifications(for problems: [String]) async {
    await removeAllProblemNotifications()

    // ★ 重要: Free プランかつ月間上限到達済みの場合はスケジュールしない
    let canSchedule = await MainActor.run { AppState.shared.canReceiveNudge }

    if !canSchedule {
        logger.info("Monthly nudge limit reached (Free plan). No notifications scheduled.")
        return
    }

    var allSchedules: [(time: (hour: Int, minute: Int), problem: ProblemType)] = []

    for problemRaw in problems {
        guard let problem = ProblemType(rawValue: problemRaw) else { continue }

        for time in problem.notificationSchedule {
            var adjustedHour = time.hour
            var adjustedMinute = time.minute

            // タイミング最適化: 2日連続ignoredならシフト
            let consecutiveIgnored = await MainActor.run {
                NudgeStatsManager.shared.getConsecutiveIgnoredDays(problemType: problemRaw, hour: time.hour)
            }

            if consecutiveIgnored >= 2 {
                // 30分後ろにシフト
                adjustedMinute += 30
                if adjustedMinute >= 60 {
                    adjustedMinute -= 60
                    adjustedHour = (adjustedHour + 1) % 24
                }
                logger.info("Shifted \(problemRaw) from \(time.hour):\(time.minute) to \(adjustedHour):\(adjustedMinute) due to \(consecutiveIgnored) consecutive ignored days")
            }

            allSchedules.append((time: (adjustedHour, adjustedMinute), problem: problem))
        }
    }

    // 時刻でソート
    allSchedules.sort { $0.time.hour * 60 + $0.time.minute < $1.time.hour * 60 + $1.time.minute }

    // 30分以内に被る場合は15分ずらしてスケジュール（既存ロジック）
    var lastScheduledMinutes: Int?
    var scheduledCount = 0

    for schedule in allSchedules {
        var hour = schedule.time.hour
        var minute = schedule.time.minute
        var currentMinutes = hour * 60 + minute

        if let last = lastScheduledMinutes {
            if currentMinutes < last + minimumIntervalMinutes {
                currentMinutes = last + 15
                hour = (currentMinutes / 60) % 24
                minute = currentMinutes % 60
                logger.info("Shifted \(schedule.problem.rawValue) to \(hour):\(minute) to avoid collision")
            }
        }

        guard schedule.problem.isValidTime(hour: hour, minute: minute) else {
            logger.info("Skipped \(schedule.problem.rawValue) at \(hour):\(minute) - outside valid time range")
            continue
        }

        await scheduleNotification(
            for: schedule.problem,
            hour: hour,
            minute: minute
        )

        lastScheduledMinutes = currentMinutes
        scheduledCount += 1
    }

    logger.info("Scheduled \(scheduledCount) problem notifications")
}
```

---

## Task 10: 課金ロジック

### 背景・なぜこれをやるか

Aniccaの新しい課金モデルは「NudgeCard完了回数ベース」:

| プラン | 月間回数 | 上限到達後 |
|--------|------------|-----------|
| Free | 10回/月 | **通知自体がスケジュールされない** |
| Pro | 無制限 | - |

**重要な設計決定**:

1. 通知とコンテンツ（NudgeCard）は完全にペア
2. `monthlyNudgeCount` は **NudgeCard完了時** にカウント（スケジュール時ではない）
3. 10回完了後、全通知をキャンセルし、再スケジュール時にブロック

### フロー

```
【Freeユーザーの月間フロー】

月初め:
  monthlyNudgeCount = 0
  canReceiveNudge = true
  → 通知がスケジュールされる

1回目〜9回目:
  通知配信 → タップ → NudgeCard表示 → 完了
  monthlyNudgeCount += 1

10回目:
  通知配信 → タップ → NudgeCard表示 → 完了
  monthlyNudgeCount = 10
  → Paywall表示 (nudge_card_complete_10)
  → 全通知キャンセル
  canReceiveNudge = false

11回目以降:
  通知が既にキャンセル済み
  次回スケジュール時も canReceiveNudge = false でブロック

月が変わる:
  checkAndResetMonthlyNudgeCountIfNeeded() 実行
  monthlyNudgeCount = 0
  canReceiveNudge = true
  → 通知スケジュール再開
```

### 修正箇所 1: AppState.swift（カウンター追加）

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/AppState.swift`

以下のプロパティとメソッドを追加：

```swift
// MARK: - Nudge Card / Paywall / Review (Phase 4)

/// NudgeCard完了回数（累計、レビュー・Paywall表示判定用）
@Published private(set) var nudgeCardCompletedCount: Int = 0

/// 月間NudgeCard完了回数（通知制限用、月初リセット）
@Published private(set) var monthlyNudgeCount: Int = 0

/// レビューリクエスト済みフラグ
@Published private(set) var hasRequestedReview: Bool = false

// UserDefaultsキー
private let nudgeCardCompletedCountKey = "com.anicca.nudgeCardCompletedCount"
private let monthlyNudgeCountKey = "com.anicca.monthlyNudgeCount"
private let hasRequestedReviewKey = "com.anicca.hasRequestedReview"
private let lastNudgeResetMonthKey = "com.anicca.lastNudgeResetMonth"
private let lastNudgeResetYearKey = "com.anicca.lastNudgeResetYear"

// MARK: - Nudge Card / Paywall / Review Methods

/// NudgeCard完了回数をインクリメント
func incrementNudgeCardCompletedCount() {
    nudgeCardCompletedCount += 1
    defaults.set(nudgeCardCompletedCount, forKey: nudgeCardCompletedCountKey)
}

/// 月間NudgeCard完了回数をインクリメント
func incrementMonthlyNudgeCount() {
    monthlyNudgeCount += 1
    defaults.set(monthlyNudgeCount, forKey: monthlyNudgeCountKey)
}

/// レビューリクエスト済みとしてマーク
func markReviewRequested() {
    hasRequestedReview = true
    defaults.set(true, forKey: hasRequestedReviewKey)
}

/// 月間NudgeCard完了回数をリセット
func resetMonthlyNudgeCount() {
    monthlyNudgeCount = 0
    defaults.set(0, forKey: monthlyNudgeCountKey)
}

/// Nudge受信可能かどうか
var canReceiveNudge: Bool {
    if subscriptionInfo.plan == .pro { return true }
    return monthlyNudgeCount < 10
}

/// 月初リセットチェック（アプリ起動時に呼び出す）
func checkAndResetMonthlyNudgeCountIfNeeded() {
    let calendar = Calendar.current
    let now = Date()
    let currentMonth = calendar.component(.month, from: now)
    let currentYear = calendar.component(.year, from: now)

    let lastMonth = defaults.integer(forKey: lastNudgeResetMonthKey)
    let lastYear = defaults.integer(forKey: lastNudgeResetYearKey)

    if currentYear != lastYear || currentMonth != lastMonth {
        resetMonthlyNudgeCount()
        defaults.set(currentMonth, forKey: lastNudgeResetMonthKey)
        defaults.set(currentYear, forKey: lastNudgeResetYearKey)

        // 月が変わったら通知を再スケジュール
        Task {
            await ProblemNotificationScheduler.shared.scheduleNotifications(for: userProfile.struggles)
        }
    }
}
```

**init() 内に追加**：

```swift
// init() 内に追加
self.nudgeCardCompletedCount = defaults.integer(forKey: nudgeCardCompletedCountKey)
self.monthlyNudgeCount = defaults.integer(forKey: monthlyNudgeCountKey)
self.hasRequestedReview = defaults.bool(forKey: hasRequestedReviewKey)

// 月初リセットチェック
checkAndResetMonthlyNudgeCountIfNeeded()
```

### 修正箇所 2: ProblemNotificationScheduler.swift（上限到達時のブロック）

**このパッチは Task 9 に統合済み**。`scheduleNotifications` メソッドの先頭で `canReceiveNudge` をチェック。

---

## Task 11: Paywall Placement更新

### 修正箇所 1: SuperwallManager.swift

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/Services/SuperwallManager.swift`

```swift
// As-Is (現状のenum)
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case sessionComplete1 = "session_complete_1"
    case sessionComplete3 = "session_complete_3"
    case campaignAppLaunch = "campaign_app_launch"
    case profilePlanTap = "profile_plan_tap"
    case quotaExceeded = "quota_exceeded"
}

// To-Be
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case nudgeCardComplete5 = "nudge_card_complete_5"
    case nudgeCardComplete10 = "nudge_card_complete_10"
    case profilePlanTap = "profile_plan_tap"
}
```

### 修正箇所 2: MainTabView.swift（完全なパッチ）

**ファイル**: `/Users/cbns03/Downloads/anicca-project/aniccaios/aniccaios/MainTabView.swift`

```swift
import SwiftUI
import UIKit
import Combine
import StoreKit

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState

    var body: some View {
        Group {
            switch appState.selectedRootTab {
            case .myPath:
                MyPathTabView()
                    .environmentObject(appState)
            case .profile:
                ProfileView()
                    .environmentObject(appState)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        // Proactive Agent: NudgeCard表示
        .fullScreenCover(item: $appState.pendingNudgeCard) { content in
            NudgeCardView(
                content: content,
                onPositiveAction: {
                    handleNudgeCardCompletion(content: content)
                },
                onNegativeAction: {
                    handleNudgeCardCompletion(content: content)
                },
                onFeedback: { isPositive in
                    if isPositive {
                        NudgeStatsManager.shared.recordThumbsUp(
                            problemType: content.problemType.rawValue,
                            variantIndex: content.variantIndex
                        )
                    } else {
                        NudgeStatsManager.shared.recordThumbsDown(
                            problemType: content.problemType.rawValue,
                            variantIndex: content.variantIndex
                        )
                    }
                },
                onDismiss: {
                    appState.dismissNudgeCard()
                }
            )
        }
        .safeAreaInset(edge: .bottom) {
            FigmaTabBar(selectedTab: $appState.selectedRootTab)
        }
        .background(AppBackground())
        .ignoresSafeArea(.keyboard, edges: .bottom)
    }

    // MARK: - NudgeCard Completion Handler

    private func handleNudgeCardCompletion(content: NudgeContent) {
        // カウンターをインクリメント
        appState.incrementNudgeCardCompletedCount()

        // Freeプランの場合、月間カウントもインクリメント
        if appState.subscriptionInfo.plan != .pro {
            appState.incrementMonthlyNudgeCount()
        }

        let count = appState.nudgeCardCompletedCount
        let monthlyCount = appState.monthlyNudgeCount
        let plan = appState.subscriptionInfo.plan

        // NudgeCardを閉じる
        appState.dismissNudgeCard()

        // 3回目: レビューリクエスト
        if count == 3 && !appState.hasRequestedReview {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                if let scene = UIApplication.shared.connectedScenes
                    .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene {
                    SKStoreReviewController.requestReview(in: scene)
                }
            }
            appState.markReviewRequested()
            return
        }

        // 5回目: Paywall
        if count == 5 && plan != .pro {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                SuperwallManager.shared.register(placement: SuperwallPlacement.nudgeCardComplete5.rawValue)
            }
            return
        }

        // 10回目（月間）: Paywall + 通知キャンセル
        if monthlyCount >= 10 && plan != .pro {
            // 全通知をキャンセル
            Task {
                await ProblemNotificationScheduler.shared.cancelAllNotifications()
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                SuperwallManager.shared.register(placement: SuperwallPlacement.nudgeCardComplete10.rawValue)
            }
            return
        }
    }
}
```

---

## テストケース

### Task 0: AnalyticsEvent

- [ ] ビルドエラーなし（.nudgeTapped, .nudgeIgnored, .nudgeFeedback が存在）

### Task 1: 言語問題

- [ ] 端末を英語に設定 → 通知スケジュール → 端末を日本語に変更 → 通知タップ → NudgeCard表示 → **日本語で表示される**

### Task 2: 時刻特有メッセージ

- [ ] stayingUpLate 21:00 → variant 0, 1, 2 のいずれか
- [ ] stayingUpLate 0:00 → **必ずvariant 3**「深夜0時を過ぎました」
- [ ] stayingUpLate 1:00 → **必ずvariant 4**「深夜1時です」

### Task 3: カッコ削除

- [ ] NudgeCard表示 → 通知テキストに「」がない

### Task 4-5: トラッキング

- [ ] 通知タップ → NudgeStats.tappedCount +1
- [ ] 24時間経過 & 未タップ → アプリ起動 → NudgeStats.ignoredCount +1

### Task 6-8: ルールベース選択

- [ ] 初回5回 → 各バリアントが均等に試される
- [ ] 15回後 → tap率が高いバリアントが80%選ばれる
- [ ] 👍タップ → thumbsUpCount +1

### Task 9: タイミング最適化

- [ ] 2日連続ignored → 次回は30分後ろにシフト

### Task 10-11: 課金

- [ ] NudgeCard 3回目完了 → レビューリクエスト
- [ ] NudgeCard 5回目完了 (Free) → Paywall表示
- [ ] NudgeCard 10回目完了 (Free) → Paywall表示 + 通知キャンセル
- [ ] 月が変わる → monthlyNudgeCount リセット → 通知再スケジュール

---

## 実装順序

1. **Task 0**: AnalyticsManager.swift（イベントケース追加）
2. **Task 6**: NudgeStatsManager.swift 新規作成
3. **Task 7**: NudgeContentSelector.swift 新規作成
4. **Task 10-a**: AppState.swift 修正（課金カウンター追加）
5. **Task 1 + Task 9**: ProblemNotificationScheduler.swift 修正（言語問題 + 上限チェック + タイミング最適化）
6. **Task 1**: NudgeContent.swift 修正
7. **Task 3**: NudgeCardView.swift 修正
8. **Task 4**: AppDelegate.swift 修正
9. **Task 5**: AppState.swift 修正（起動時チェック追加）
10. **Task 11**: SuperwallManager.swift 修正
11. **Task 8 + Task 11**: MainTabView.swift 修正（完全なパッチ）

---

## 注意事項

### ローカライゼーション

- `Localizable.strings` の変更は不要
- 既存のキー（`nudge_*_notification_*`, `nudge_*_detail_*`）をそのまま使用
- キーは `nudge_{problem_rawValue}_notification_{variantIndex+1}` の形式

### 後方互換性

- `NudgeContent.nudgeContent(from:)` は古い形式（文字列直接保存）もサポート
- 既にスケジュールされた通知は古い形式で動作し続ける

### Superwall Dashboard

実装後、以下の設定が必要：

1. **新規Placement追加**
   - `nudge_card_complete_5`
   - `nudge_card_complete_10`

2. **Placement削除**（使用されなくなる）
   - `session_complete_1`
   - `session_complete_3`
   - `campaign_app_launch`
   - `quota_exceeded`

---

## Superwall Dashboard 設定（手動作業）

コード実装後、以下のGUI設定が必要。

### 1. 新規Placement追加

**Dashboard → Placements → Create Placement**

| Placement Name | Identifier | 用途 |
|----------------|------------|------|
| NudgeCard Complete 5 | `nudge_card_complete_5` | 5回目完了時にPaywall表示 |
| NudgeCard Complete 10 | `nudge_card_complete_10` | 10回目完了時（月上限）にPaywall表示 |

### 2. Campaign設定

**Dashboard → Campaigns → Create Campaign（または既存を編集）**

#### nudge_card_complete_5 用

1. **Name**: NudgeCard 5 Paywall
2. **Trigger**: `nudge_card_complete_5`
3. **Paywall**: 使用するPaywallを選択
4. **Audience**: All Users
5. **Save**

#### nudge_card_complete_10 用

1. **Name**: NudgeCard 10 Paywall
2. **Trigger**: `nudge_card_complete_10`
3. **Paywall**: 使用するPaywallを選択
4. **Audience**: All Users
5. **Save**

### 3. Paywall文言更新（推奨）

**Dashboard → Paywalls → 対象Paywall → Edit**

| 項目 | 新しい文言 |
|------|----------|
| Headline | "Unlimited nudges, unlimited change." |
| Value Prop 1 | "Learns what hits you" |
| Value Prop 2 | "Catches you before you fall" |
| Value Prop 3 | "Stays one step ahead" |
| CTA Button | "Get unlimited nudges" |

### 4. 古いPlacement無効化

以下のPlacementはコードから呼ばれなくなる。Campaignから外すか削除（任意）：

- `session_complete_1`
- `session_complete_3`
- `campaign_app_launch`
- `quota_exceeded`

**注意**: 削除しなくても動作に影響なし。コードから呼ばれないだけ。

### 5. テスト手順

1. Sandboxアカウントでアプリ起動
2. オンボーディング完了
3. NudgeCard 5回完了 → **Paywall表示を確認**
4. Paywall閉じる
5. NudgeCard 10回完了 → **Paywall表示を確認** + **通知が来なくなることを確認**
6. 課金完了 → Paywall非表示を確認

---

## 作業分担まとめ

| 担当 | 作業内容 |
|------|---------|
| **エージェント（コード）** | 全12タスクの実装（Task 0〜11） |
| **あなた（GUI）** | Superwall Dashboard設定（Placement追加、Campaign設定） |

---

*この文書は Phase 4 の完全な実装仕様である。追加の質問なしで実装可能。*
