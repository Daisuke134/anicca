# Proactive Agent リファクタリング実装仕様書

> 作成日: 2026-01-20
> 目的: HabitType系レガシーコードの削除とコードベースの整理
> レビュー対象: 全Phase

---

## 1. エグゼクティブサマリー

### 1.1 目的
音声対話アプリからProactive Agentへの移行に伴い、使われていないコードを削除してAIエージェントの混乱を防ぐ。

### 1.2 影響範囲
- 削除ファイル: **27ファイル**
- 編集ファイル: **8ファイル**
- 追加ファイル: **0ファイル**

### 1.3 リスク評価
- **cantWakeUpアラーム機能**: 影響なし（ProblemAlarmKitSchedulerは独立）
- **Problem Nudge機能**: 影響なし
- **オンボーディング**: 影響なし（実際のフローは変わらない）

---

## 2. AS-IS（現在の状態）

### 2.1 ファイル構成

#### 2.1.1 削除対象ファイル一覧

| # | ファイルパス | 行数 | 理由 |
|---|-------------|------|------|
| 1 | `Views/Talk/TalkView.swift` | 103行 | Talkタブ非表示 |
| 2 | `Views/Talk/FeelingTopic.swift` | ~20行 | TalkView依存 |
| 3 | `Views/Talk/FeelingCard.swift` | ~50行 | TalkView依存 |
| 4 | `Views/Talk/QuoteCard.swift` | ~60行 | TalkView依存 |
| 5 | `Views/Session/SessionView.swift` | ~200行 | TalkView依存 |
| 6 | `Views/Session/HabitSessionView.swift` | 222行 | HabitType依存 |
| 7 | `Views/Session/OrbView.swift` | ~150行 | HabitSessionView依存 |
| 8 | `Views/Session/EMAModal.swift` | ~100行 | SessionView依存 |
| 9 | `Intents/StartConversationIntent.swift` | ~100行 | HabitType依存 |
| 10 | `VoiceSessionController.swift` | ~500行 | 音声セッション |
| 11 | `AudioSessionCoordinator.swift` | ~200行 | 音声セッション依存 |
| 12 | `WakePromptBuilder.swift` | ~100行 | HabitType依存 |
| 13 | `Onboarding/HabitType.swift` | ~80行 | 旧習慣enum |
| 14 | `Onboarding/HabitSetupStepView.swift` | 400行 | 到達不可 |
| 15 | `Onboarding/IdealsStepView.swift` | ~150行 | 到達不可 |
| 16 | `Onboarding/AuthenticationStepView.swift` | ~100行 | 到達不可 |
| 17 | `Onboarding/SourceStepView.swift` | ~80行 | 到達不可 |
| 18 | `Onboarding/ProfileInfoStepView.swift` | ~100行 | 到達不可 |
| 19 | `Onboarding/GenderStepView.swift` | ~80行 | 到達不可 |
| 20 | `Onboarding/AgeStepView.swift` | ~80行 | 到達不可 |
| 21 | `Onboarding/AlarmKitPermissionStepView.swift` | ~100行 | 到達不可 |
| 22 | `Onboarding/HabitSleepLocationStepView.swift` | ~80行 | 未使用 |
| 23 | `Onboarding/HabitTrainingFocusStepView.swift` | ~80行 | 未使用 |
| 24 | `Onboarding/HabitWakeLocationStepView.swift` | ~80行 | 未使用 |
| 25 | `Onboarding/WakeSetupStepView.swift` | ~80行 | 未使用 |
| 26 | `Onboarding/CompletionStepView.swift` | ~80行 | 未使用 |
| 27 | `Habits/HabitsTabView.swift` | 16行 | MyPathTabViewに置換済み |
| 28 | `Habits/HabitsSectionView.swift` | ~200行 | HabitsTabView依存 |
| 29 | `Habits/StreakMilestoneSheet.swift` | ~150行 | 未使用 |
| 30 | `Models/PendingHabitTrigger.swift` | 17行 | HabitType依存 |
| 31 | `Notifications/AlarmKitHabitCoordinator.swift` | 547行 | HabitType依存 |
| 32 | `Settings/HabitFollowUpView.swift` | ~100行 | HabitType依存 |
| 33 | `Services/AlarmKitPermissionManager.swift` | ~50行 | 未使用 |

#### 2.1.2 編集対象ファイル一覧

| # | ファイルパス | 変更内容 |
|---|-------------|----------|
| 1 | `AppState.swift` | RootTab.talk削除、HabitType関連プロパティ削除 |
| 2 | `AppDelegate.swift` | handleHabitLaunch削除、習慣通知ハンドリング削除 |
| 3 | `MainTabView.swift` | case .talk削除、fullScreenCover削除 |
| 4 | `OnboardingFlowView.swift` | 不要なcase削除 |
| 5 | `OnboardingStep.swift` | 不要なcase削除 |
| 6 | `ProblemType.swift` | relatedHabitType削除 |
| 7 | `ProfileView.swift` | 認証メソッド呼び出し先変更 |
| 8 | `ProblemAlarmKitScheduler.swift` | requestAuthorizationIfNeeded追加 |
| 9 | `NotificationScheduler.swift` | HabitType関連ロジック削除 |

### 2.2 現在のコード状態（詳細）

#### 2.2.1 AppState.swift - RootTab enum（80-84行目）

```swift
// AS-IS
enum RootTab: Int, Hashable {
    case talk = 0      // ← 削除対象
    case habits = 1
    case profile = 2
}
@Published var selectedRootTab: RootTab = .habits
```

#### 2.2.2 MainTabView.swift - switch文（12-20行目付近）

```swift
// AS-IS
switch selectedTab {
case .talk:
    TalkView()  // ← 削除対象
case .habits:
    MyPathTabView()
case .profile:
    ProfileView()
}
```

#### 2.2.3 OnboardingStep.swift（1-17行目）

```swift
// AS-IS
enum OnboardingStep: Int {
    case welcome       // 0 - 使用中
    case account       // 1 - 削除対象
    case value         // 2 - 使用中
    case source        // 3 - 削除対象
    case name          // 4 - 削除対象
    case gender        // 5 - 削除対象
    case age           // 6 - 削除対象
    case ideals        // 7 - 削除対象
    case struggles     // 8 - 使用中
    case habitSetup    // 9 - 削除対象
    case notifications // 10 - 使用中
    case att           // 11 - 使用中
    case alarmkit      // 12 - 削除対象
}
```

#### 2.2.4 OnboardingFlowView.swift - advance()（71-107行目）

```swift
// AS-IS - 実際のフロー
case .welcome:
    step = .value  // account をスキップ
case .value:
    step = .struggles  // ideals をスキップ
case .struggles:
    step = .notifications  // habitSetup をスキップ
case .notifications:
    step = .att
case .att:
    completeOnboarding()
    return
// 以下は到達不可能だがコードが存在
case .ideals, .habitSetup, .account, .source, .name, .gender, .age, .alarmkit:
    // ...
```

#### 2.2.5 ProblemType.swift - relatedHabitType（25-33行目）

```swift
// AS-IS - 使われていない
var relatedHabitType: HabitType? {
    switch self {
    case .stayingUpLate:
        return .bedtime
    case .cantWakeUp:
        return .wake
    default:
        return nil
    }
}
```

#### 2.2.6 ProfileView.swift - AlarmKit認証（806行目）

```swift
// AS-IS
let granted = await AlarmKitHabitCoordinator.shared.requestAuthorizationIfNeeded()
```

#### 2.2.7 AlarmKitHabitCoordinator.swift - requestAuthorizationIfNeeded（194-210行目）

```swift
// AS-IS - このメソッドだけ移動が必要
func requestAuthorizationIfNeeded() async -> Bool {
    do {
        let currentState = manager.authorizationState
        logger.info("Current AlarmKit authorization state: \(String(describing: currentState), privacy: .public)")

        if currentState == .authorized {
            return true
        }

        let state = try await manager.requestAuthorization()
        logger.info("AlarmKit authorization result: \(String(describing: state), privacy: .public)")
        return state == .authorized
    } catch {
        logger.error("AlarmKit authorization failed: \(error.localizedDescription, privacy: .public)")
        return false
    }
}
```

#### 2.2.8 AlarmKitHabitCoordinator.swift - Locale.Weekday拡張（57-62行目）

```swift
// AS-IS - ProblemAlarmKitSchedulerで使用しているため移動が必要
@available(iOS 26.0, *)
extension Locale.Weekday {
    static var allWeekdays: [Locale.Weekday] {
        [.sunday, .monday, .tuesday, .wednesday, .thursday, .friday, .saturday]
    }
}
```

**重要**: この拡張は `ProblemAlarmKitScheduler.swift:135` で使用されている。
AlarmKitHabitCoordinator削除前に移動しないと**コンパイルエラー**になる。

---

## 3. TO-BE（目標状態）

### 3.1 ファイル構成（削除後）

```
aniccaios/aniccaios/
├── Views/
│   ├── MyPathTabView.swift          # 保持
│   ├── NudgeCardView.swift          # 保持
│   ├── AddProblemSheetView.swift    # 保持
│   ├── Profile/
│   │   ├── ProfileView.swift        # 編集
│   │   └── TraitsDetailView.swift   # 保持
│   ├── Session/                     # ディレクトリごと削除
│   └── Talk/                        # ディレクトリごと削除
├── Onboarding/
│   ├── OnboardingFlowView.swift     # 編集
│   ├── OnboardingStep.swift         # 編集
│   ├── WelcomeStepView.swift        # 保持
│   ├── ValueStepView.swift          # 保持
│   ├── StrugglesStepView.swift      # 保持
│   ├── NotificationPermissionStepView.swift  # 保持
│   └── ATTPermissionStepView.swift  # 保持
├── Notifications/
│   ├── ProblemNotificationScheduler.swift  # 保持
│   ├── ProblemAlarmKitScheduler.swift      # 編集（認証メソッド追加）
│   └── NotificationScheduler.swift         # 編集（HabitType削除）
├── Models/
│   ├── ProblemType.swift            # 編集
│   └── UserProfile.swift            # 保持
├── Habits/                          # ディレクトリごと削除
├── Intents/                         # ディレクトリごと削除
├── AppState.swift                   # 編集
├── AppDelegate.swift                # 編集
├── MainTabView.swift                # 編集
└── ContentView.swift                # 保持
```

### 3.2 コード変更（詳細）

#### 3.2.1 AppState.swift - RootTab enum

```swift
// TO-BE
enum RootTab: Int, Hashable {
    case myPath = 0   // renamed from habits
    case profile = 1
}
@Published var selectedRootTab: RootTab = .myPath
```

**削除対象プロパティ:**
- `habitSchedules: [HabitType: DateComponents]`
- `habitFollowupCounts: [HabitType: Int]`
- `pendingHabitTrigger: PendingHabitTrigger?`
- `shouldStartSessionImmediately: Bool`
- `customHabits: [CustomHabitConfiguration]`

**削除対象メソッド:**
- `func prepareForImmediateSession(...)`
- `func handleHabitTrigger(...)`
- `func updateHabits(...)`
- `func followupCount(for:)`
- `func setFollowupCount(...)`
- その他HabitType関連メソッド

#### 3.2.2 MainTabView.swift

```swift
// TO-BE
switch selectedTab {
case .myPath:
    MyPathTabView()
case .profile:
    ProfileView()
}
```

**削除:**
- `@State private var activeHabitSession: ActiveHabitSession?`
- `struct ActiveHabitSession`
- `checkPendingHabitTrigger()` メソッド
- `.fullScreenCover(item: $activeHabitSession)`

#### 3.2.3 OnboardingStep.swift

```swift
// TO-BE
enum OnboardingStep: Int {
    case welcome = 0
    case value = 1
    case struggles = 2
    case notifications = 3
    case att = 4
}

extension OnboardingStep {
    // マイグレーション関数は削除（新規ユーザーのみ対応）
}
```

#### 3.2.4 OnboardingFlowView.swift

```swift
// TO-BE
switch step {
case .welcome:
    WelcomeStepView(next: advance)
case .value:
    ValueStepView(next: advance)
case .struggles:
    StrugglesStepView(next: advance)
case .notifications:
    NotificationPermissionStepView(next: advance)
case .att:
    ATTPermissionStepView(next: advance)
}

private func advance() {
    switch step {
    case .welcome:
        step = .value
    case .value:
        step = .struggles
    case .struggles:
        step = .notifications
    case .notifications:
        step = .att
    case .att:
        completeOnboarding()
        return
    }
    appState.setOnboardingStep(step)
}
```

#### 3.2.5 ProblemType.swift

```swift
// TO-BE - relatedHabitType プロパティを完全削除
// 行25-33を削除
```

#### 3.2.6 ProblemAlarmKitScheduler.swift

```swift
// TO-BE - Locale.Weekday拡張を追加（20行目付近、クラス定義の前）
// MARK: - Locale.Weekday Extension (AlarmKitHabitCoordinatorから移動)
@available(iOS 26.0, *)
extension Locale.Weekday {
    static var allWeekdays: [Locale.Weekday] {
        [.sunday, .monday, .tuesday, .wednesday, .thursday, .friday, .saturday]
    }
}

// TO-BE - requestAuthorizationIfNeeded を追加（クラス内、36行目付近）
@available(iOS 26.0, *)
final class ProblemAlarmKitScheduler {
    // ... 既存コード ...

    // MARK: - Authorization (AlarmKitHabitCoordinatorから移動)

    /// AlarmKit許可をリクエスト
    func requestAuthorizationIfNeeded() async -> Bool {
        do {
            let currentState = manager.authorizationState
            logger.info("Current AlarmKit authorization state: \(String(describing: currentState), privacy: .public)")

            if currentState == .authorized {
                return true
            }

            let state = try await manager.requestAuthorization()
            logger.info("AlarmKit authorization result: \(String(describing: state), privacy: .public)")
            return state == .authorized
        } catch {
            logger.error("AlarmKit authorization failed: \(error.localizedDescription, privacy: .public)")
            return false
        }
    }
}
```

#### 3.2.7 ProfileView.swift

```swift
// TO-BE - 呼び出し先を変更（806行目）
let granted = await ProblemAlarmKitScheduler.shared.requestAuthorizationIfNeeded()
```

#### 3.2.8 AppDelegate.swift

**削除対象:**
- `HabitLaunchBridge.startObserver` 呼び出し（10-12行目）
- `AlarmKitHabitCoordinator.shared.cancelAllAlarms()` 呼び出し（51-55行目）
- `consumePendingHabitLaunch()` メソッド（86-112行目）
- `userNotificationCenter(didReceive:)` 内の習慣通知ハンドリング（150-166行目）
- `userNotificationCenter(didReceive:)` 内のpreReminderハンドリング（168-181行目）
- `handleHabitLaunch()` メソッド（201-220行目）
- `habitContext(from:)` メソッド（222-234行目）

**保持:**
- Problem Nudge通知のハンドリング（129-148行目）
- Nudge（サーバー駆動型）通知のハンドリング（183-198行目）

---

## 4. 実装手順

### Phase 1: 認証メソッド・拡張移動（依存関係解消）

| # | 作業 | ファイル |
|---|------|----------|
| 1.1 | `Locale.Weekday.allWeekdays` 拡張を追加（**重要: 先に追加**） | `ProblemAlarmKitScheduler.swift` |
| 1.2 | `requestAuthorizationIfNeeded()` を ProblemAlarmKitScheduler に追加 | `ProblemAlarmKitScheduler.swift` |
| 1.3 | ProfileView の呼び出し先を変更 | `ProfileView.swift` |
| 1.4 | ビルド確認 | - |

**注意**: 1.1 の `Locale.Weekday.allWeekdays` 拡張は `ProblemAlarmKitScheduler.swift:135` で使用されている。
AlarmKitHabitCoordinator削除（Phase 4-8）前にこの拡張を追加しないと**コンパイルエラー**になる。

### Phase 2: Talk関連削除

| # | 作業 | ファイル |
|---|------|----------|
| 2.1 | `Views/Talk/` ディレクトリ削除 | 4ファイル |
| 2.2 | `Views/Session/` ディレクトリ削除 | 4ファイル |
| 2.3 | MainTabView から `case .talk` 削除 | `MainTabView.swift` |
| 2.4 | AppState から `RootTab.talk` 削除 | `AppState.swift` |
| 2.5 | ビルド確認 | - |

### Phase 3: Onboarding整理

| # | 作業 | ファイル |
|---|------|----------|
| 3.1 | 未使用Onboardingファイル削除（8ファイル） | `Onboarding/` |
| 3.2 | OnboardingStep enum を5ケースに縮小 | `OnboardingStep.swift` |
| 3.3 | OnboardingFlowView を5ケースに縮小 | `OnboardingFlowView.swift` |
| 3.4 | ビルド確認 | - |

### Phase 4: HabitType系統削除

| # | 作業 | ファイル |
|---|------|----------|
| 4.1 | `Habits/` ディレクトリ削除 | 3ファイル |
| 4.2 | `Intents/StartConversationIntent.swift` 削除 | 1ファイル |
| 4.3 | `VoiceSessionController.swift` 削除 | 1ファイル |
| 4.4 | `AudioSessionCoordinator.swift` 削除 | 1ファイル |
| 4.5 | `WakePromptBuilder.swift` 削除 | 1ファイル |
| 4.6 | `Models/PendingHabitTrigger.swift` 削除 | 1ファイル |
| 4.7 | `Onboarding/HabitType.swift` 削除 | 1ファイル |
| 4.8 | `Notifications/AlarmKitHabitCoordinator.swift` 削除 | 1ファイル |
| 4.9 | `Settings/HabitFollowUpView.swift` 削除 | 1ファイル |
| 4.10 | `Services/AlarmKitPermissionManager.swift` 削除 | 1ファイル |
| 4.11 | ProblemType から `relatedHabitType` 削除 | `ProblemType.swift` |
| 4.12 | AppState から HabitType関連コード削除 | `AppState.swift` |
| 4.13 | AppDelegate から習慣通知ハンドリング削除 | `AppDelegate.swift` |
| 4.14 | ビルド確認 | - |

### Phase 5: NotificationScheduler整理

| # | 作業 | ファイル |
|---|------|----------|
| 5.1 | HabitType関連のスケジューリングロジック削除 | `NotificationScheduler.swift` |
| 5.2 | Category.habitAlarm, Category.preReminder 削除 | `NotificationScheduler.swift` |
| 5.3 | ビルド確認 | - |
| 5.4 | 動作確認（オンボーディング、通知、アラーム） | - |

---

## 5. cantWakeUpアラーム機能の動作保証

### 5.1 依存関係図（リファクタリング後）

```
[ユーザー: トグルON]
    ↓
[ProfileView.swift]
    ↓ await ProblemAlarmKitScheduler.shared.requestAuthorizationIfNeeded()
[ProblemAlarmKitScheduler.swift] ← 認証メソッド追加済み
    ↓ AlarmManager.shared.requestAuthorization()
[Apple AlarmKit Framework]
    ↓ 許可
[ProfileView.swift]
    ↓ await ProblemAlarmKitScheduler.shared.scheduleCantWakeUp(hour: 6, minute: 0)
[ProblemAlarmKitScheduler.swift]
    ↓ 6:00と6:05のアラームをスケジュール
[Apple AlarmKit Framework]
    ↓
[アラーム発火]
    ↓
[OpenProblemOneScreenIntent / CantWakeUpStopIntent]
    ↓ ProblemAlarmKitScheduler.swift 内で定義済み
[動作]
```

### 5.2 HabitType非依存の確認

| コンポーネント | HabitType使用 | 備考 |
|---------------|--------------|------|
| `ProblemAlarmKitScheduler.swift` | **なし** | 完全独立 |
| `ProblemAlarmMetadata` | **なし** | problemType: String |
| `OpenProblemOneScreenIntent` | **なし** | problemType: String |
| `CantWakeUpStopIntent` | **なし** | alarmID: String |
| `ProblemNotificationScheduler.swift` | **なし** | ProblemType のみ使用 |

### 5.3 テスト項目

| # | テスト | 期待結果 |
|---|--------|----------|
| 1 | ProfileでcantWakeUpトグルON | AlarmKit許可ダイアログ表示 |
| 2 | 許可後 | 6:00と6:05のアラームがスケジュールされる |
| 3 | 6:00にアラーム発火 | フルスクリーンアラーム表示 |
| 4 | 「今日を始める」タップ | 6:05キャンセル、アプリ起動 |
| 5 | 「布団にいる」タップ | 6:05は鳴る |
| 6 | トグルOFF | アラームキャンセル、通常通知に切り替え |

---

## 6. レビューチェックリスト

### 6.1 Phase 1 レビュー項目

- [ ] `Locale.Weekday.allWeekdays` 拡張が `ProblemAlarmKitScheduler.swift` に追加されているか
- [ ] `ProblemAlarmKitScheduler.requestAuthorizationIfNeeded()` が追加されているか
- [ ] `ProfileView` の呼び出し先が `ProblemAlarmKitScheduler` に変更されているか
- [ ] ビルドが通るか

### 6.2 Phase 2 レビュー項目

- [ ] `Views/Talk/` ディレクトリが削除されているか
- [ ] `Views/Session/` ディレクトリが削除されているか
- [ ] `MainTabView` から `case .talk` が削除されているか
- [ ] `AppState.RootTab` から `.talk` が削除されているか
- [ ] ビルドが通るか

### 6.3 Phase 3 レビュー項目

- [ ] 未使用Onboardingファイル（8個）が削除されているか
- [ ] `OnboardingStep` が5ケースになっているか
- [ ] `OnboardingFlowView` が5ケースになっているか
- [ ] マイグレーション関数が削除されているか
- [ ] ビルドが通るか

### 6.4 Phase 4 レビュー項目

- [ ] `Habits/` ディレクトリが削除されているか
- [ ] `HabitType.swift` が削除されているか
- [ ] `AlarmKitHabitCoordinator.swift` が削除されているか
- [ ] `VoiceSessionController.swift` が削除されているか
- [ ] `ProblemType.relatedHabitType` が削除されているか
- [ ] `AppState` からHabitType関連が削除されているか
- [ ] `AppDelegate` から `HabitLaunchBridge.startObserver` が削除されているか
- [ ] `AppDelegate` から `AlarmKitHabitCoordinator.shared.cancelAllAlarms()` が削除されているか
- [ ] `AppDelegate` から習慣通知ハンドリング（150-166行目）が削除されているか
- [ ] `AppDelegate` から preReminderハンドリング（168-181行目）が削除されているか
- [ ] `AppDelegate` から `handleHabitLaunch()` と `habitContext()` が削除されているか
- [ ] `AppDelegate` から `consumePendingHabitLaunch()` が削除されているか
- [ ] ビルドが通るか

### 6.5 Phase 5 レビュー項目

- [ ] `NotificationScheduler` からHabitType関連が削除されているか
- [ ] ビルドが通るか

### 6.6 動作確認項目

- [ ] オンボーディングが正常に動作するか（welcome→value→struggles→notifications→att→complete）
- [ ] My Pathタブが正常に表示されるか
- [ ] Profileタブが正常に表示されるか
- [ ] Problem Nudge通知が正常にスケジュールされるか
- [ ] cantWakeUpアラームトグルが動作するか
- [ ] アラームが正常に発火するか（DEBUGテスト）

---

## 7. ロールバック手順

万が一問題が発生した場合:

```bash
# 直前のコミットに戻す
git reset --hard HEAD~1

# または特定のコミットに戻す
git log --oneline  # コミットハッシュを確認
git reset --hard <commit-hash>
```

---

## 8. CLAUDE.md 更新内容

リファクタリング完了後、以下を更新:

```markdown
## iOSアプリ現在の実装状況（2026年1月時点）

### タブ構成（2タブ）
| タブ | View | 内容 |
|------|------|------|
| My Path | `MyPathTabView` | ユーザーの問題一覧、Tell Anicca、DeepDive |
| Profile | `ProfileView` | Name, Plan, Data Integration, Nudge Strength |

### レガシーコード（リファクタリング予定）
~~以下のコードは非アクティブだが残存している:~~
~~- TalkView~~
~~- VoiceSessionController~~
~~- HabitSessionView~~
~~- HabitType~~

**リファクタリング完了** (2026-01-XX)
- 上記レガシーコードは全て削除済み
- HabitType系統は完全に削除
- cantWakeUpアラームはProblemAlarmKitSchedulerで独立動作
```

---

## 9. 備考

- **推定作業時間**: 2-3時間（各Phase 20-30分）
- **コミット粒度**: Phaseごとに1コミット推奨
- **テスト**: 各Phase完了後にビルド確認必須

---

最終更新: 2026-01-20（レビュー後修正: Locale.Weekday拡張移動、AppDelegate削除対象追記）
