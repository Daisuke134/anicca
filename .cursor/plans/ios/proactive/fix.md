# Proactive Agent Phase 3 修正パッチ

## 概要

Proactive Agent機能のApp Store提出前に発見された問題を修正するパッチ群。
HabitType → ProblemType への完全移行、ローカライズ修正、AlarmKit統合を含む。

**通知システムは1つに統一：ProblemType通知のみ**

- HabitType通知（wake, bedtime, training）→ 無効化
- カスタム習慣通知（UUID-based）→ 無効化
- ProblemType通知 → 唯一の通知システム

---

## パッチ1: HabitType通知 + カスタム習慣通知の完全無効化

### As-Is（現状の問題）

- HabitType（wake, bedtime, training）の通知システムが残っている
- カスタム習慣（UUID-based）の通知システムも残っている
- 旧バージョンで設定されたデータがあると通知が発火する可能性がある
- ProblemType通知と並行して発火し、ユーザーを混乱させる

### To-Be（実現したい状態）

- HabitType通知は完全に無効化
- カスタム習慣通知も完全に無効化
- 既存ユーザーのスケジュール済み通知もすべてクリア
- 通知はProblemNotificationSchedulerのみで管理

**ユーザー体験**: ProblemType（苦しみ）に基づいた通知のみを受け取る。古いシステムの通知は一切来ない。

### ファイル

`aniccaios/Notifications/NotificationScheduler.swift`

### 変更内容

#### 1-1: applySchedules（143-169行目付近）

```swift
// 変更前
func applySchedules(_ schedules: [HabitType: DateComponents]) async {
    await removePending(withPrefix: "HABIT_")
    // ... HabitTypeごとにスケジュール処理
    for (habit, components) in schedules {
        // スケジュール実行
    }
}

// 変更後
func applySchedules(_ schedules: [HabitType: DateComponents]) async {
    // すべてのHabitType通知を完全にクリア（既存ユーザー対応）
    await removePending(withPrefix: "HABIT_")
    await removeDelivered(withPrefix: "HABIT_")
    await removePending(withPrefix: "PRE_REMINDER_")

#if canImport(AlarmKit)
    if #available(iOS 26.0, *) {
        await AlarmKitHabitCoordinator.shared.cancelAllAlarms()
    }
#endif

    // HabitTypeの通知は一切スケジュールしない
    logger.info("HabitType notifications disabled - using ProblemType only")
}
```

#### 1-2: applyCustomSchedules（491-532行目付近）

```swift
// 変更前
func applyCustomSchedules(_ schedules: [UUID: (name: String, time: DateComponents)]) async {
    // ... カスタム習慣ごとにスケジュール処理
}

// 変更後
func applyCustomSchedules(_ schedules: [UUID: (name: String, time: DateComponents)]) async {
    // すべてのカスタム習慣通知を完全にクリア（既存ユーザー対応）
    await removePending(withPrefix: "CUSTOM_")
    await removeDelivered(withPrefix: "CUSTOM_")

#if canImport(AlarmKit)
    if #available(iOS 26.0, *) {
        for (id, _) in schedules {
            await AlarmKitHabitCoordinator.shared.cancelCustomHabitAlarms(id)
        }
    }
#endif

    // カスタム習慣の通知は一切スケジュールしない
    logger.info("Custom habit notifications disabled - using ProblemType only")
}
```

---

## パッチ2: cantWakeUpを6:00 AMに有効化 + AlarmKit分岐

### As-Is（現状の問題）

- ProblemNotificationSchedulerでcantWakeUpがスキップされている
- コード: `if problem == .cantWakeUp { continue }`
- cantWakeUpを選択しても、6:00 AMに通知が来ない

### To-Be（実現したい状態）

- cantWakeUpが6:00 AMに通知/アラームとしてスケジュールされる
- iOS 26+ & AlarmKit許可済み → フルスクリーンアラーム
- iOS 26未満 or 未許可 → 通常の通知

**ユーザー体験**: 「起きれない」を選択したユーザーは、毎日6:00 AMに起床を促す通知/アラームを受け取る。

### ファイル

`aniccaios/Notifications/ProblemNotificationScheduler.swift`

### 変更内容

#### 2-1: continueの削除（36-37行目）

```swift
// 変更前
// cant_wake_up はアラームとして別途処理されるのでスキップ
if problem == .cantWakeUp { continue }

// 変更後
// この2行を完全に削除
```

#### 2-2: scheduleNotificationメソッドにAlarmKit分岐を追加（122行目付近）

```swift
// 変更前
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    let content = NudgeContent.contentForToday(for: problem)
    // ... 通常通知スケジュール処理
}

// 変更後
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // cantWakeUpの場合、iOS 26+でAlarmKit許可済みならAlarmKitを使用
    if problem == .cantWakeUp {
#if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            let manager = AlarmManager.shared
            if manager.authorizationState == .authorized {
                await ProblemAlarmKitScheduler.shared.scheduleCantWakeUp(hour: hour, minute: minute)
                return  // 通常の通知はスケジュールしない
            }
        }
#endif
    }

    // 以下、既存の通常通知スケジュール処理
    let content = NudgeContent.contentForToday(for: problem)
    // ...
}
```

---

## パッチ2B: cantWakeUp文言の日本語化

### As-Is（現状の問題）

- `nudge_cant_wake_up_notification_3`が日本語ファイルでも「Stay Mediocre」のまま（英語）

### To-Be（実現したい状態）

- 日本語は完全に日本語で表示

### ファイル

`aniccaios/Resources/ja.lproj/Localizable.strings`

### 変更内容

```
// 変更前（679行目）
"nudge_cant_wake_up_notification_3" = "Stay Mediocre";

// 変更後
"nudge_cant_wake_up_notification_3" = "平凡なままでいい？";
```

---

## パッチ2C: AlarmKit「今日を始める」ボタンでOneScreenに飛ぶ

### As-Is（現状の問題）

- AlarmKitの「今日を始める」ボタンをタップした時の動作が未定義

### To-Be（実現したい状態）

- 「今日を始める」をタップ → アプリが開きOneScreen表示
- 「布団にいる」をタップ → アラーム停止のみ

**ユーザー体験**:

1. 6:00 AMにAlarmKitアラームが発火
2. フルスクリーンにタイトル「起床」、ボタン「布団にいる」「今日を始める ☀️」
3. 「今日を始める ☀️」タップ → OneScreen表示
4. 「布団にいる」タップ → アラーム停止、アプリは開かない

### 実装

パッチ8（ProblemAlarmKitScheduler新規作成）で対応。

---

## パッチ3: 30分ルールを15分シフトに変更

### As-Is（現状の問題）

- 通知が30分以内に被る場合、後の通知がスキップされる
- 複数の問題を選択した場合、一部の通知が届かない

### To-Be（実現したい状態）

- 通知が30分以内に被る場合、スキップせずに15分ずらす
- 例: 21:00と21:00に2つの問題 → 21:00と21:15にスケジュール

**ユーザー体験**: 選択したすべての苦しみに対して通知が届く。通知が欠落しない。

### ファイル

`aniccaios/Notifications/ProblemNotificationScheduler.swift`

### 変更内容

```swift
// 変更前（51-71行目付近）
for schedule in allSchedules {
    let currentMinutes = schedule.time.hour * 60 + schedule.time.minute
    if let last = lastScheduledMinutes {
        let diff = currentMinutes - last
        if diff < minimumIntervalMinutes && diff >= 0 {
            logger.info("Skipping \(schedule.problem.rawValue)...")
            continue  // スキップ
        }
    }
    await scheduleNotification(...)
    lastScheduledMinutes = currentMinutes
}

// 変更後
for schedule in allSchedules {
    var hour = schedule.time.hour
    var minute = schedule.time.minute
    var currentMinutes = hour * 60 + minute

    if let last = lastScheduledMinutes {
        let diff = currentMinutes - last
        if diff < minimumIntervalMinutes && diff >= 0 {
            // 15分ずらす（スキップしない）
            currentMinutes = last + 15
            hour = (currentMinutes / 60) % 24
            minute = currentMinutes % 60
            logger.info("Shifted \(schedule.problem.rawValue) to \(hour):\(minute)")
        }
    }
    await scheduleNotification(for: schedule.problem, hour: hour, minute: minute)
    lastScheduledMinutes = currentMinutes
}
```

---

## パッチ4: 英語ボタンから絵文字削除（3つのみ）

### As-Is（現状の問題）

- 英語の一部のボタンテキストが長すぎてUIで切れる

### To-Be（実現したい状態）

- ボタンテキストが短くなり、UIで切れない

### ファイル

`aniccaios/Resources/en.lproj/Localizable.strings`

### 変更内容

```
// 変更前
"problem_staying_up_late_positive_button" = "Protect Tomorrow 💪";
"problem_self_loathing_positive_button" = "Forgive Myself 🤍";
"problem_alcohol_dependency_positive_button" = "Stay Sober Tonight 🍵";

// 変更後
"problem_staying_up_late_positive_button" = "Protect Tomorrow";
"problem_self_loathing_positive_button" = "Forgive Myself";
"problem_alcohol_dependency_positive_button" = "Stay Sober";
```

---

## パッチ5: AlarmKit許可ダイアログ（cantWakeUp選択時）

### As-Is（現状の問題）

- 「起きれない」を選択しても、AlarmKit許可がリクエストされない

### To-Be（実現したい状態）

- 「起きれない」をタップした瞬間にAlarmKit許可ダイアログ表示
- 対象:
  1. オンボーディング（StrugglesStepView）
  2. My Pathで問題追加（AddProblemSheetView）

**ユーザー体験（iOS 26+）**:
1. 「起きれない」タップ → AlarmKit許可ダイアログ
2. 許可 → 毎日6:00 AMにフルスクリーンアラーム

### ファイル

1. `aniccaios/Onboarding/StrugglesStepView.swift`
2. `aniccaios/Views/AddProblemSheetView.swift`

### 変更内容

#### 5-1: StrugglesStepView.swift

```swift
// ファイル先頭にimport追加
#if canImport(AlarmKit)
import AlarmKit
#endif

// chipButton内のButton action（78-84行目付近）
// 変更前
Button {
    if isSelected {
        selected.remove(key)
    } else {
        selected.insert(key)
    }
}

// 変更後
Button {
    if isSelected {
        selected.remove(key)
    } else {
        selected.insert(key)
        if key == "cant_wake_up" {
#if canImport(AlarmKit)
            if #available(iOS 26.0, *) {
                Task {
                    await AlarmKitHabitCoordinator.shared.requestAuthorizationIfNeeded()
                }
            }
#endif
        }
    }
}
```

#### 5-2: AddProblemSheetView.swift

```swift
// ファイル先頭にimport追加
#if canImport(AlarmKit)
import AlarmKit
#endif

// chipButton内のButton action（89-94行目付近）
// 変更前
Button {
    if isSelected {
        selected.remove(key)
    } else {
        selected.insert(key)
    }
}

// 変更後
Button {
    if isSelected {
        selected.remove(key)
    } else {
        selected.insert(key)
        if key == "cant_wake_up" {
#if canImport(AlarmKit)
            if #available(iOS 26.0, *) {
                Task {
                    await AlarmKitHabitCoordinator.shared.requestAuthorizationIfNeeded()
                }
            }
#endif
        }
    }
}
```

---

## パッチ6: 日本語ローカライズ修正（OneScreen）

### As-Is（現状の問題）

- OneScreenのタイトル・詳細文が英語で表示される
- 原因: `String(localized:)`は動的キーでは機能しない

### To-Be（実現したい状態）

- すべてのProblemTypeで日本語ローカライズが機能

### ファイル

`aniccaios/Models/NudgeContent.swift`

### 変更内容

すべての`String(localized:)`を`NSLocalizedString`に変更。

```swift
// 変更前（例: cantWakeUp, 47-52行目）
case .cantWakeUp:
    return [
        String(localized: "nudge_cant_wake_up_notification_1"),
        String(localized: "nudge_cant_wake_up_notification_2"),
        String(localized: "nudge_cant_wake_up_notification_3")
    ]

// 変更後
case .cantWakeUp:
    return [
        NSLocalizedString("nudge_cant_wake_up_notification_1", comment: ""),
        NSLocalizedString("nudge_cant_wake_up_notification_2", comment: ""),
        NSLocalizedString("nudge_cant_wake_up_notification_3", comment: "")
    ]
```

**対象のcase（すべて同様に変更）:**
- cantWakeUp, selfLoathing, rumination, procrastination, anxiety, lying, badMouthing, pornAddiction, alcoholDependency, anger, obsessive, loneliness

**notificationMessages()とdetailMessages()の両方で変更が必要**

---

## パッチ7: オンボーディング2列グリッド

### As-Is（現状の問題）

- FlowLayoutで表示、チップサイズがバラバラ

### To-Be（実現したい状態）

- 2列のLazyVGridで均一表示

### ファイル

`aniccaios/Onboarding/StrugglesStepView.swift`

### 変更内容

```swift
// 変更前（36-46行目）
ScrollView {
    FlowLayout(spacing: 12) {
        ForEach(options, id: \.self) { key in
            chipButton(kind: "problem", key: key)
        }
    }
    .padding(.horizontal, 24)
    .padding(.top, 8)
    .padding(.bottom, 16)
}

// 変更後
ScrollView {
    LazyVGrid(columns: [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12)
    ], spacing: 12) {
        ForEach(options, id: \.self) { key in
            chipButton(kind: "problem", key: key)
        }
    }
    .padding(.horizontal, 24)
    .padding(.top, 8)
    .padding(.bottom, 16)
}
```

```swift
// chipButton（75-95行目）を修正
@ViewBuilder
private func chipButton(kind: String, key: String) -> some View {
    let isSelected = selected.contains(key)
    Button {
        if isSelected {
            selected.remove(key)
        } else {
            selected.insert(key)
            if key == "cant_wake_up" {
#if canImport(AlarmKit)
                if #available(iOS 26.0, *) {
                    Task {
                        await AlarmKitHabitCoordinator.shared.requestAuthorizationIfNeeded()
                    }
                }
#endif
            }
        }
    } label: {
        Text(NSLocalizedString("\(kind)_\(key)", comment: ""))
            .font(.system(size: 14, weight: .medium))
            .lineLimit(2)
            .minimumScaleFactor(0.8)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity, minHeight: 56)
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(isSelected ? AppTheme.Colors.buttonSelected : AppTheme.Colors.buttonUnselected)
            .foregroundStyle(isSelected ? AppTheme.Colors.buttonTextSelected : AppTheme.Colors.label)
            .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    .buttonStyle(.plain)
}
```

---

## パッチ8: ProblemAlarmKitScheduler新規作成

### 目的

cantWakeUp用のAlarmKitスケジューラを作成。「今日を始める」ボタンでOneScreenに飛ぶ機能を含む。

### ファイル（新規作成）

`aniccaios/Notifications/ProblemAlarmKitScheduler.swift`

### コード

```swift
#if canImport(AlarmKit)
import AlarmKit
import AppIntents
import Foundation
import OSLog

@available(iOS 26.0, *)
final class ProblemAlarmKitScheduler {
    static let shared = ProblemAlarmKitScheduler()

    private let logger = Logger(subsystem: "com.anicca.ios", category: "ProblemAlarmKit")
    private let manager = AlarmManager.shared
    private let storageKey = "com.anicca.alarmkit.cantWakeUp.id"

    private init() {}

    /// cantWakeUp用のAlarmKitアラームをスケジュール
    func scheduleCantWakeUp(hour: Int, minute: Int) async {
        await cancelCantWakeUp()

        let time = Alarm.Schedule.Relative.Time(hour: hour, minute: minute)
        let schedule = Alarm.Schedule.relative(.init(
            time: time,
            repeats: .weekly(Locale.Weekday.allWeekdays)
        ))

        let alert = AlarmPresentation.Alert(
            title: LocalizedStringResource("problem_cant_wake_up_notification_title"),
            stopButton: AlarmButton(
                text: LocalizedStringResource("problem_cant_wake_up_negative_button"),
                textColor: .red,
                systemImageName: "bed.double"
            ),
            secondaryButton: AlarmButton(
                text: LocalizedStringResource("problem_cant_wake_up_positive_button"),
                textColor: .white,
                systemImageName: "sun.max"
            ),
            secondaryButtonBehavior: .custom
        )

        let presentation = AlarmPresentation(alert: alert)
        let attributes = AlarmAttributes(presentation: presentation, tintColor: .orange)

        let identifier = UUID()
        let secondary = OpenProblemOneScreenIntent(problemType: "cant_wake_up")

        let configuration = AlarmManager.AlarmConfiguration(
            countdownDuration: nil,
            schedule: schedule,
            attributes: attributes,
            stopIntent: CantWakeUpStopIntent(alarmID: identifier.uuidString),
            secondaryIntent: secondary
        )

        do {
            _ = try await manager.schedule(id: identifier, configuration: configuration)
            UserDefaults.standard.set(identifier.uuidString, forKey: storageKey)
            logger.info("Scheduled AlarmKit alarm for cantWakeUp at \(hour):\(minute)")
        } catch {
            logger.error("Failed to schedule AlarmKit for cantWakeUp: \(error.localizedDescription)")
        }
    }

    /// cantWakeUp用のAlarmKitアラームをキャンセル
    func cancelCantWakeUp() async {
        guard let idString = UserDefaults.standard.string(forKey: storageKey),
              let id = UUID(uuidString: idString) else { return }

        do {
            try manager.cancel(id: id)
            UserDefaults.standard.removeObject(forKey: storageKey)
            logger.info("Cancelled AlarmKit for cantWakeUp")
        } catch {
            logger.error("Failed to cancel AlarmKit for cantWakeUp: \(error.localizedDescription)")
        }
    }
}

// MARK: - Intents

@available(iOS 26.0, *)
struct OpenProblemOneScreenIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "Open Problem OneScreen"

    @Parameter(title: "Problem Type")
    var problemType: String

    init() {
        self.problemType = "cant_wake_up"
    }

    init(problemType: String) {
        self.problemType = problemType
    }

    func perform() async throws -> some IntentResult {
        NotificationCenter.default.post(
            name: Notification.Name("OpenProblemOneScreen"),
            object: nil,
            userInfo: ["problemType": problemType]
        )
        return .result()
    }
}

@available(iOS 26.0, *)
struct CantWakeUpStopIntent: LiveActivityIntent {
    static var title: LocalizedStringResource = "Stop CantWakeUp Alarm"

    @Parameter(title: "Alarm ID")
    var alarmID: String

    init() {
        self.alarmID = ""
    }

    init(alarmID: String) {
        self.alarmID = alarmID
    }

    func perform() async throws -> some IntentResult {
        let logger = Logger(subsystem: "com.anicca.ios", category: "ProblemAlarmKit")
        logger.info("CantWakeUp alarm stopped: id=\(self.alarmID)")
        return .result()
    }
}
#endif
```

---

## パッチ9: MainAppでのOneScreen受信処理

### 目的

AlarmKitの「今日を始める」ボタンでOneScreenを開く処理を追加。

### ファイル

`aniccaios/App/AniccaApp.swift` または該当するメインApp構造体

### 変更内容

```swift
// WindowGroup内またはContentView内に追加
.onReceive(NotificationCenter.default.publisher(for: Notification.Name("OpenProblemOneScreen"))) { notification in
    guard let userInfo = notification.userInfo,
          let problemTypeRaw = userInfo["problemType"] as? String,
          let problemType = ProblemType(rawValue: problemTypeRaw) else { return }

    // OneScreenを表示
    let content = NudgeContent.contentForToday(for: problemType)
    appState.presentOneScreen(content: content)
}
```

### AppStateに追加

```swift
// AppState.swift
@Published var oneScreenContent: NudgeContent?

func presentOneScreen(content: NudgeContent) {
    self.oneScreenContent = content
}
```

---

## 実装順序

1. **パッチ1**: HabitType + カスタム習慣通知の完全無効化（最優先）
2. **パッチ8**: ProblemAlarmKitScheduler新規作成
3. **パッチ2**: cantWakeUp有効化 + AlarmKit分岐
4. **パッチ2B**: 日本語文言修正
5. **パッチ9**: OneScreen受信処理
6. **パッチ3**: 15分シフト
7. **パッチ4**: 英語絵文字削除
8. **パッチ5**: AlarmKit許可ダイアログ
9. **パッチ6**: NSLocalizedString統一
10. **パッチ7**: 2列グリッド

---

## 確認事項

- [ ] HabitType通知が発火しないことを確認
- [ ] カスタム習慣通知が発火しないことを確認
- [ ] cantWakeUpが6:00 AMに通知/アラームが来ることを確認
- [ ] iOS 26+でAlarmKitアラーム画面が表示されることを確認
- [ ] 「今日を始める」タップでOneScreenが開くことを確認
- [ ] OneScreenが日本語で表示されることを確認
- [ ] iOS 26+でAlarmKit許可ダイアログが表示されることを確認
- [ ] オンボーディングで13個すべての問題が2列グリッドで表示されることを確認
- [ ] My Pathで問題追加時にAlarmKit許可ダイアログが表示されることを確認

---

## アラーム画面の文言

| 項目 | 英語 | 日本語 |
|------|------|--------|
| タイトル | "Wake Up" | "起床" |
| 停止ボタン | "Stay in bed" | "布団にいる" |
| 起きるボタン | "Start Today ☀️" | "今日を始める ☀️" |

---

## cantWakeUp文言バリエーション

**通知文言（notification）- 3種類:**

| # | 英語 | 日本語 |
|---|------|--------|
| 1 | Your day won't start until you get up. | 起きないと、今日が始まらん。 |
| 2 | The 'just 5 more minutes' you has zero credibility. | あと5分の君、信用ゼロ。 |
| 3 | Stay Mediocre | 平凡なままでいい？ |

**詳細文言（detail）- 3種類:**

| # | 英語 | 日本語 |
|---|------|--------|
| 1 | Nothing changes under the blanket. Put your feet on the floor first. | 布団の中で何も変わらない。まず足を床につけよう。 |
| 2 | How many times have you said '5 more minutes'? Get up now, and you'll like today's you. | 「あと5分」を何回言った？今起きれば、今日の自分を好きになれる。 |
| 3 | Want to stay average? Get up now, and today will be different. | 平凡なままでいい？今起きれば、今日は違う1日になる。 |
