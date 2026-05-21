# cantWakeUp 起床アラーム実装仕様書

## 概要

cantWakeUp（起きれない）問題を選択したユーザー向けに、iOS 26+ AlarmKitを使用したフルスクリーンアラーム機能を実装する。

---

## AS-IS（現状）

### 1. ProblemType.swift（重要：既に変更済み）
- `notificationSchedule` が `[(6, 0), (6, 5)]` を返す（6:00と6:05の2回）
- `validTimeRange` で6:00-9:00の時間帯制限あり
- `isValidTime()` で有効時間帯チェック

### 2. ProblemAlarmKitScheduler.swift
- ファイル先頭に「⚠️ UNUSED」コメントあり（無効化）
- `scheduleCantWakeUp(hour, minute)` で**1つの時刻のみ**スケジュール
- 2段階アラーム（6:00 + 6:05）のロジックなし
- フォローアップキャンセル機能なし

### 3. ProblemNotificationScheduler.swift
- `scheduleNotifications()` が `[(6, 0), (6, 5)]` をループし、6:00と6:05で `scheduleNotification()` を**2回呼ぶ**
- 有効時間帯チェック（`isValidTime`）がループ内にある
- cantWakeUpは通常通知（UNUserNotificationCenter）としてスケジュール
- AlarmKitへの分岐ロジックなし

### 3. ProfileView.swift
- アラーム関連のトグルなし
- cantWakeUp選択者向けのセクションなし

### 4. UserProfile（モデル）
- `useAlarmKitForCantWakeUp` フラグなし

### 5. ローカライズ
- AlarmKitアラーム画面用のキーが不完全

---

## TO-BE（目標状態）

### 1. ProblemType.swift
- 変更なし（既に6:00と6:05、時間帯制限が実装済み）

### 2. ProblemAlarmKitScheduler.swift
- 「UNUSED」コメント削除、有効化
- 2段階アラーム（6:00 + 6:05）をスケジュール
- primaryId / followupId を分離管理
- `cancelFollowupAndReschedule()` メソッド追加
- DEBUG用テストメソッド追加

### 3. ProblemNotificationScheduler.swift
- cantWakeUp + AlarmKit許可済み + トグルON の場合:
  - 6:00の呼び出し → AlarmKitに委譲（内部で6:00と6:05をスケジュール）
  - 6:05の呼び出し → 何もしない（return）
  - 通常通知はスケジュールしない
- それ以外 → 従来通り通常通知（6:00と6:05の2回）

### 3. ProfileView.swift
- cantWakeUp選択者のみ「起床アラーム」セクション表示
- 「フルスクリーンアラーム」トグル追加
- トグルON時にAlarmKit許可リクエスト
- 許可拒否済みの場合は設定誘導アラート
- DEBUG用アラームテストUI追加

### 4. UserProfile（モデル）
- `useAlarmKitForCantWakeUp: Bool` 追加（デフォルト: false）

### 5. ローカライズ
- 全キー追加（日本語・英語）

---

## UI/UXフロー

### フロー1: オンボーディング

```
[StrugglesStepView]
「起きれない」を選択
    ↓
AlarmKit許可ダイアログは出さない（Apple審査対策）
    ↓
6:00に「通常通知」がスケジュール
```

### フロー2: Profile画面

```
[ProfileView] ※cantWakeUp選択者のみ表示

── 起床アラーム ────────────────
│ フルスクリーンアラーム   [OFF] │
│ ONにすると、毎朝6:00と6:05に   │
│ フルスクリーンアラームで       │
│ 起こします                     │
└─────────────────────────────────
```

### フロー3: トグルON（AlarmKit未許可）

```
トグルON
    ↓
AlarmKit許可ダイアログ表示
    ↓
許可 → トグルON維持、6:00+6:05アラームスケジュール
拒否 → トグルOFFに戻す
```

### フロー4: トグルON（AlarmKit拒否済み）

```
トグルON
    ↓
authorizationState == .denied
    ↓
アラート「設定で許可してください」
    ↓
「設定を開く」→ 設定アプリへ
「キャンセル」→ トグルOFFのまま
```

### フロー5: アラーム発火（6:00）

```
[フルスクリーンアラーム]

            6:00
           起床

    ┌─────────────────────┐
    │ 🛏️ 布団にいる        │ → アラーム停止のみ、6:05は鳴る
    └─────────────────────┘

    ┌─────────────────────┐
    │ ☀️ 今日を始める      │ → アプリ起動、One Screen、6:05キャンセル
    └─────────────────────┘

      ← スワイプで停止 →     → アラーム停止のみ、6:05は鳴る
```

### フロー6: 「今日を始める」タップ時の処理

```
1. OpenProblemOneScreenIntent.perform() 実行
2. 6:05のフォローアップアラームをキャンセル
3. 6:05のアラームを即座に再スケジュール（明日用）
4. NotificationCenter.post() でOne Screen表示を通知
5. アプリ起動、One Screen表示
```

### フロー7: DEBUG画面

```
#if DEBUG
── ⏰ アラームテスト ────────────
│ 時間を選択    [15:16]  ▼     │  ← DatePicker
│                              │
│ [選択した時間でアラーム設定]   │  ← ボタン
│                              │
│ [1分後にアラーム]             │  ← ショートカット
└─────────────────────────────────
#endif
```

---

## 修正ファイル詳細

### ファイル1: UserProfile.swift（またはUserProfile定義箇所）

**変更内容:**
```swift
// 追加
var useAlarmKitForCantWakeUp: Bool = false
```

**CodingKeys対応:**
- `useAlarmKitForCantWakeUp` を追加

**永続化:**
- UserDefaultsまたはサーバー同期対象に追加

---

### ファイル2: ProblemAlarmKitScheduler.swift

**変更1: 「UNUSED」コメント削除**
- ファイル先頭の警告コメント（1-14行目）を削除

**変更2: storageKey分離**
```swift
// 変更前
private let storageKey = "com.anicca.alarmkit.cantWakeUp.id"

// 変更後
private let primaryStorageKey = "com.anicca.alarmkit.cantWakeUp.primaryId"
private let followupStorageKey = "com.anicca.alarmkit.cantWakeUp.followupId"
```

**変更3: scheduleCantWakeUp() を2段階に**
```swift
func scheduleCantWakeUp(hour: Int, minute: Int) async {
    await cancelCantWakeUp()

    // 1. Primary alarm (6:00)
    let primaryId = UUID()
    // ... schedule with hour:minute
    UserDefaults.standard.set(primaryId.uuidString, forKey: primaryStorageKey)

    // 2. Followup alarm (6:05)
    let followupId = UUID()
    let followupMinute = (minute + 5) % 60
    let followupHour = minute + 5 >= 60 ? (hour + 1) % 24 : hour
    // ... schedule with followupHour:followupMinute
    UserDefaults.standard.set(followupId.uuidString, forKey: followupStorageKey)
}
```

**変更4: cancelFollowupAndReschedule() 追加**
```swift
/// 「今日を始める」タップ時に呼ばれる
/// 今日の6:05をキャンセルし、明日用に再スケジュール
func cancelFollowupAndReschedule() async {
    // 1. 現在のfollowupをキャンセル
    if let idString = UserDefaults.standard.string(forKey: followupStorageKey),
       let id = UUID(uuidString: idString) {
        try? manager.cancel(id: id)
    }

    // 2. 即座に再スケジュール（明日から有効）
    let followupId = UUID()
    // ... schedule with 6:05
    UserDefaults.standard.set(followupId.uuidString, forKey: followupStorageKey)
}
```

**変更5: cancelCantWakeUp() 修正**
```swift
func cancelCantWakeUp() async {
    // Primary
    if let idString = UserDefaults.standard.string(forKey: primaryStorageKey),
       let id = UUID(uuidString: idString) {
        try? manager.cancel(id: id)
        UserDefaults.standard.removeObject(forKey: primaryStorageKey)
    }

    // Followup
    if let idString = UserDefaults.standard.string(forKey: followupStorageKey),
       let id = UUID(uuidString: idString) {
        try? manager.cancel(id: id)
        UserDefaults.standard.removeObject(forKey: followupStorageKey)
    }
}
```

**変更6: OpenProblemOneScreenIntent.perform() 修正**
```swift
func perform() async throws -> some IntentResult {
    // ★ 追加: フォローアップキャンセル→再スケジュール
    await ProblemAlarmKitScheduler.shared.cancelFollowupAndReschedule()

    // 既存: One Screen表示通知
    NotificationCenter.default.post(
        name: Notification.Name("OpenProblemOneScreen"),
        object: nil,
        userInfo: ["problemType": problemType]
    )
    return .result()
}
```

**変更7: DEBUG用テストメソッド追加**
```swift
#if DEBUG
/// デバッグ用: 指定時刻にテストアラームをスケジュール
func scheduleTestAlarm(hour: Int, minute: Int) async {
    await scheduleCantWakeUp(hour: hour, minute: minute)
}
#endif
```

---

### ファイル3: ProblemNotificationScheduler.swift

**前提:** `ProblemType.notificationSchedule` は既に `[(6, 0), (6, 5)]` を返す。
つまり `scheduleNotification()` は6:00と6:05で**2回呼ばれる**。

**変更箇所: scheduleNotification() メソッド内**

```swift
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // ★ 追加: cantWakeUp + AlarmKit許可済み + トグルON → AlarmKitに委譲
    if problem == .cantWakeUp {
        #if canImport(AlarmKit)
        if #available(iOS 26.0, *) {
            let manager = AlarmManager.shared
            if manager.authorizationState == .authorized,
               AppState.shared.userProfile.useAlarmKitForCantWakeUp {
                // ★ 6:00の呼び出し時のみAlarmKitに委譲
                // AlarmKit側で6:00と6:05の両方をスケジュールする
                if hour == 6 && minute == 0 {
                    await ProblemAlarmKitScheduler.shared.scheduleCantWakeUp(hour: hour, minute: minute)
                }
                // 6:05の呼び出しは無視（AlarmKit側で既にスケジュール済み）
                // 通常通知はスケジュールしない
                return
            }
        }
        #endif
    }

    // 以下、既存の通常通知スケジュール処理（AlarmKit無効時のみ到達）
    let content = NudgeContent.contentForToday(for: problem)
    // ...
}
```

**動作フロー:**
- **AlarmKit有効時:**
  - 6:00の呼び出し → AlarmKitで6:00と6:05をスケジュール → return（通常通知なし）
  - 6:05の呼び出し → 何もしない → return（通常通知なし）
- **AlarmKit無効時（トグルOFF or iOS 25以下）:**
  - 6:00の呼び出し → 通常通知スケジュール
  - 6:05の呼び出し → 通常通知スケジュール
```

---

### ファイル4: ProfileView.swift

**変更1: 状態変数追加**
```swift
@State private var isShowingAlarmKitSettingsAlert = false
#if DEBUG
@State private var debugAlarmTime = Date()
#endif
```

**変更2: 起床アラームセクション追加（nudgeStrengthSectionの後）**

body内に条件付きで追加:
```swift
// cantWakeUp選択者のみ表示
if appState.userProfile.problems.contains("cant_wake_up") {
    wakeUpAlarmSection
}
```

**変更3: wakeUpAlarmSection実装**
```swift
@available(iOS 26.0, *)
private var wakeUpAlarmSection: some View {
    VStack(alignment: .leading, spacing: 10) {
        Text(String(localized: "profile_section_wake_alarm"))
            .font(.system(size: 18, weight: .bold))
            .foregroundStyle(AppTheme.Colors.label)
            .padding(.horizontal, 2)

        CardView(cornerRadius: 28) {
            VStack(alignment: .leading, spacing: 8) {
                Toggle(
                    String(localized: "profile_wake_alarm_toggle"),
                    isOn: alarmKitToggleBinding
                )
                .tint(AppTheme.Colors.accent)

                Text(String(localized: "profile_wake_alarm_description"))
                    .font(AppTheme.Typography.caption1Dynamic)
                    .foregroundStyle(AppTheme.Colors.secondaryLabel)
            }
        }
    }
    .alert(String(localized: "alarmkit_permission_needed_title"), isPresented: $isShowingAlarmKitSettingsAlert) {
        Button(String(localized: "common_open_settings")) { openSystemSettings() }
        Button(String(localized: "common_cancel"), role: .cancel) {}
    } message: {
        Text(String(localized: "alarmkit_permission_needed_message"))
    }
}

@available(iOS 26.0, *)
private var alarmKitToggleBinding: Binding<Bool> {
    Binding(
        get: { appState.userProfile.useAlarmKitForCantWakeUp },
        set: { newValue in
            if newValue {
                Task { @MainActor in
                    let manager = AlarmManager.shared

                    // 拒否済みの場合は設定誘導
                    if manager.authorizationState == .denied {
                        isShowingAlarmKitSettingsAlert = true
                        return
                    }

                    // 許可リクエスト
                    let granted = await AlarmKitHabitCoordinator.shared.requestAuthorizationIfNeeded()

                    var profile = appState.userProfile
                    profile.useAlarmKitForCantWakeUp = granted
                    appState.updateUserProfile(profile, sync: true)

                    // 許可されたらアラームをスケジュール
                    if granted {
                        await ProblemAlarmKitScheduler.shared.scheduleCantWakeUp(hour: 6, minute: 0)
                    }
                }
            } else {
                // OFFにした場合
                var profile = appState.userProfile
                profile.useAlarmKitForCantWakeUp = false
                appState.updateUserProfile(profile, sync: true)

                Task {
                    await ProblemAlarmKitScheduler.shared.cancelCantWakeUp()
                    // 通常通知を再スケジュール
                    await ProblemNotificationScheduler.shared.scheduleNotifications(
                        for: appState.userProfile.problems
                    )
                }
            }
        }
    )
}

private func openSystemSettings() {
    guard let url = URL(string: UIApplication.openSettingsURLString) else { return }
    UIApplication.shared.open(url)
}
```

**変更4: iOS 26未満の分岐**
```swift
// body内
if #available(iOS 26.0, *) {
    if appState.userProfile.problems.contains("cant_wake_up") {
        wakeUpAlarmSection
    }
}
// iOS 26未満では何も表示しない（通常通知のみ）
```

**変更5: DEBUG用アラームテストUI追加**
```swift
#if DEBUG
private var alarmTestSection: some View {
    VStack(alignment: .leading, spacing: 10) {
        Text("⏰ アラームテスト")
            .font(.system(size: 14, weight: .medium))
            .foregroundStyle(AppTheme.Colors.secondaryLabel)

        CardView {
            VStack(spacing: 12) {
                if #available(iOS 26.0, *) {
                    DatePicker(
                        "時間を選択",
                        selection: $debugAlarmTime,
                        displayedComponents: .hourAndMinute
                    )

                    Divider()

                    Button("⏰ 選択した時間でアラーム設定") {
                        let components = Calendar.current.dateComponents([.hour, .minute], from: debugAlarmTime)
                        Task {
                            await ProblemAlarmKitScheduler.shared.scheduleTestAlarm(
                                hour: components.hour!,
                                minute: components.minute!
                            )
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)

                    Divider()

                    Button("⏰ 1分後にアラーム") {
                        let future = Calendar.current.date(byAdding: .minute, value: 1, to: Date())!
                        let components = Calendar.current.dateComponents([.hour, .minute], from: future)
                        Task {
                            await ProblemAlarmKitScheduler.shared.scheduleTestAlarm(
                                hour: components.hour!,
                                minute: components.minute!
                            )
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    Text("AlarmKitはiOS 26+のみ対応")
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.vertical, 4)
        }
    }
}
#endif
```

DEBUGセクション内のrecordingSectionの後に追加:
```swift
#if DEBUG
recordingSection
alarmTestSection  // ★ 追加
#endif
```

---

### ファイル5: Localizable.strings（日本語）

**追加するキー:**
```
// Profile - 起床アラームセクション
"profile_section_wake_alarm" = "起床アラーム";
"profile_wake_alarm_toggle" = "フルスクリーンアラーム";
"profile_wake_alarm_description" = "ONにすると、毎朝6:00と6:05にフルスクリーンアラームで起こします";

// AlarmKit許可アラート
"alarmkit_permission_needed_title" = "アラームの許可が必要です";
"alarmkit_permission_needed_message" = "設定アプリでAniccaのアラームを許可してください。";

// AlarmKitアラーム画面
"problem_cant_wake_up_alarm_title" = "起床";
"problem_cant_wake_up_positive_button" = "今日を始める ☀️";
"problem_cant_wake_up_negative_button" = "布団にいる";
```

---

### ファイル6: Localizable.strings（英語）

**追加するキー:**
```
// Profile - Wake-up Alarm Section
"profile_section_wake_alarm" = "Wake-up Alarm";
"profile_wake_alarm_toggle" = "Full Screen Alarm";
"profile_wake_alarm_description" = "When ON, a full screen alarm will wake you at 6:00 and 6:05 every morning";

// AlarmKit Permission Alert
"alarmkit_permission_needed_title" = "Alarm Permission Required";
"alarmkit_permission_needed_message" = "Please allow Anicca's alarm in Settings.";

// AlarmKit Alarm Screen
"problem_cant_wake_up_alarm_title" = "Wake Up";
"problem_cant_wake_up_positive_button" = "Start Today ☀️";
"problem_cant_wake_up_negative_button" = "Stay in bed";
```

---

### ファイル7: Info.plist

**確認事項:**
```xml
<key>NSAlarmKitUsageDescription</key>
<string>毎朝の起床をサポートするためにアラーム機能を使用します。</string>
```

英語版InfoPlist.strings:
```
"NSAlarmKitUsageDescription" = "Anicca uses alarms to help you wake up every morning.";
```

---

## 実装順序

1. **UserProfile.swift** - `useAlarmKitForCantWakeUp` フラグ追加
2. **ProblemAlarmKitScheduler.swift** - 2段階アラーム、キャンセル→再スケジュール
3. **ProblemNotificationScheduler.swift** - AlarmKit分岐
4. **ProfileView.swift** - 起床アラームセクション、DEBUGテストUI
5. **Localizable.strings（日本語）** - キー追加
6. **Localizable.strings（英語）** - キー追加
7. **Info.plist** - NSAlarmKitUsageDescription確認

---

## レビュー事項（レビュアーへ）

### 0. 既存コードの前提確認（重要）
- [ ] `ProblemType.notificationSchedule` の `.cantWakeUp` が `[(6, 0), (6, 5)]` を返しているか
- [ ] `ProblemType.validTimeRange` の `.cantWakeUp` が `(6, 0, 9, 0)` を返しているか
- [ ] `ProblemNotificationScheduler.scheduleNotifications()` 内で `isValidTime()` チェックがあるか

### 1. ローカライズ確認
- [ ] 日本語キーが全て `ja.lproj/Localizable.strings` に存在するか
- [ ] 英語キーが全て `en.lproj/Localizable.strings` に存在するか
- [ ] キー名が一致しているか（typoなし）
- [ ] 日本語・英語の文言が適切か

### 2. UserProfile確認
- [ ] `useAlarmKitForCantWakeUp` が追加されているか
- [ ] CodingKeysに追加されているか
- [ ] デフォルト値が `false` になっているか
- [ ] サーバー同期対象になっているか（必要に応じて）

### 3. ProblemAlarmKitScheduler確認
- [ ] 「UNUSED」コメントが削除されているか
- [ ] `primaryStorageKey` と `followupStorageKey` が分離されているか
- [ ] `scheduleCantWakeUp()` が2つのアラームをスケジュールしているか
- [ ] フォローアップの時刻計算（+5分）が正しいか
- [ ] `cancelFollowupAndReschedule()` が実装されているか
- [ ] `OpenProblemOneScreenIntent.perform()` 内で `cancelFollowupAndReschedule()` を呼んでいるか

### 4. ProblemNotificationScheduler確認
- [ ] cantWakeUp分岐が `scheduleNotification()` 内にあるか
- [ ] 条件が正しいか（AlarmKit許可済み AND トグルON）
- [ ] **6:00の呼び出し時のみ** AlarmKitに委譲しているか（`if hour == 6 && minute == 0`）
- [ ] 6:05の呼び出し時は何もせずreturnしているか
- [ ] AlarmKitに委譲した場合、通常通知をスケジュールしていないか

### 5. ProfileView確認
- [ ] `#available(iOS 26.0, *)` で囲まれているか
- [ ] cantWakeUp選択者のみ表示する条件があるか
- [ ] トグルON時に許可リクエストを呼んでいるか
- [ ] 許可拒否済み（.denied）の場合に設定誘導アラートを出しているか
- [ ] トグルOFF時にアラームキャンセル→通常通知再スケジュールしているか
- [ ] DEBUG用テストUIが `#if DEBUG` で囲まれているか

### 6. Info.plist確認
- [ ] `NSAlarmKitUsageDescription` が設定されているか
- [ ] 英語版が `InfoPlist.strings` にあるか

### 7. ロジック確認
- [ ] 「今日を始める」タップ → 6:05キャンセル → 再スケジュール の流れが正しいか
- [ ] 「布団にいる」タップ → 何もしない（6:05は鳴る）
- [ ] iOS 26未満では何も表示されないか（通常通知のみ動作）

### 8. 時刻のハードコード確認
- [ ] 6:00（primary）と 6:05（followup）が正しくハードコードされているか
- [ ] ユーザーが時刻を変更するUIは存在しないか（ユーザーに決めさせない）

---

## 備考

- iOS 25以下では通常通知1回のみ（6:00）。2段階アラームはiOS 26+限定。
- オンボーディングではAlarmKit許可ダイアログを出さない（Apple審査対策）
- Profile画面のトグルでのみAlarmKit許可をリクエストする
- DEBUG用テストUIは本番ビルドには含まれない

---

最終更新: 2026年1月19日
