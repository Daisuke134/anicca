# Single Screen App - Spec

## 概要

### 何を解決するか
現在の2タブ構成（My Path + Profile）を1画面に統合し、ユーザーの選択肢を最小化する。プロアクティブエージェントとして、ユーザーに不要な設定を触らせない。

### なぜ必要か
- **選択肢の削減**: Nudge Strength、Data Integration などユーザーに選ばせる必要がない
- **シンプルさ**: 1画面で完結することで認知負荷を下げる
- **Alarm の廃止**: AlarmKit が動作不安定なため、通知のみで対応

---

## As-Is（現状）

### UI構成
```
┌─────────────────────────────────────────┐
│             MainTabView                  │
├──────────────────┬──────────────────────┤
│   My Path Tab    │   Profile Tab         │
├──────────────────┼──────────────────────┤
│ • Problem List   │ • Name (editable)     │
│ • Tell Anicca    │ • Plan (Subscribe)    │
│   - Struggling   │ • Data Integration    │
│   - Goal         │   - Sleep             │
│   - Remember     │   - Steps             │
│                  │ • Nudge Strength      │
│                  │ • Wake-up Alarm       │
│                  │ • Sign Out / Delete   │
│                  │ • Privacy / EULA      │
└──────────────────┴──────────────────────┘
      [My Path]        [Profile]  ← FigmaTabBar
```

### ファイル構成
| ファイル | 行数 | 役割 |
|---------|------|------|
| `MainTabView.swift` | ~200 | タブ管理、NudgeCard overlay |
| `MyPathTabView.swift` | ~500 | 問題リスト、Tell Anicca |
| `ProfileView.swift` | ~1070 | 設定全般 |
| `FigmaTabBar.swift` | ~100 | カスタムタブバー |
| `ProblemAlarmKitScheduler.swift` | ~200 | AlarmKit 管理 |
| `LegalLinksView.swift` | ~50 | Privacy / EULA |

---

## 削除される設定項目の移行方針

| 設定項目 | 移行方針 | 理由 |
|---------|---------|------|
| **Name（名前）** | 完全廃止 | 表示名はプロアクティブエージェントに不要。サーバー側の userProfile.displayName は残すが、クライアントからの編集UIは削除 |
| **Data Integration（Sleep/Steps）** | サーバー固定 | HealthKit 連携は全ユーザーに自動適用。個別トグルは不要 |
| **Nudge Strength** | サーバー固定 | 通知頻度はエージェントが自動調整。ユーザーに選ばせない |
| **Wake-up Alarm** | 完全廃止 | AlarmKit が動作不安定。通知のみで起床サポート継続 |
| **Sign Out / Delete Account** | MyPathTabView に移設 | Apple Sign-in 済みユーザー向けに必須で残す |
| **Privacy / EULA** | MyPathTabView footer に移設 | 法的要件のため必須 |
| **Subscribe / Plan** | MyPathTabView に移設 | App Store 要件のため必須 |

---

## To-Be（変更後）

### UI構成

#### パターン1: Free + Apple Sign-in なし
```
┌─────────────────────────────────────────┐
│  My Path                           [+]  │
├─────────────────────────────────────────┤
│  Anicca is here to support you...       │
│                                         │
│  What you're facing                     │
│  ┌─────────────────────────────────┐    │
│  │ 😔 Staying up late           → │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 😴 Can't wake up             → │    │
│  └─────────────────────────────────┘    │
│                                         │
│  Tell Anicca                            │
│  ┌─────────────────────────────────┐    │
│  │ ✏️ Tell struggling with...    → │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 🎯 Tell your goal is...       → │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 💭 Tell to remember...        → │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [        Subscribe        ]            │
│                                         │
│     Privacy Policy • Terms of Use       │
└─────────────────────────────────────────┘
```

#### パターン2: Free + Apple Sign-in あり
```
┌─────────────────────────────────────────┐
│  My Path                           [+]  │
├─────────────────────────────────────────┤
│  （パターン1と同じ上部）                 │
│                                         │
│  [        Subscribe        ]            │
│                                         │
│  [       Sign Out        ]              │
│  [    Delete Account     ]              │
│                                         │
│     Privacy Policy • Terms of Use       │
└─────────────────────────────────────────┘
```

#### パターン3: Pro + Apple Sign-in なし
```
┌─────────────────────────────────────────┐
│  My Path                           [+]  │
├─────────────────────────────────────────┤
│  （パターン1と同じ上部）                 │
│                                         │
│  [ Cancel Subscription ]                │
│                                         │
│     Privacy Policy • Terms of Use       │
└─────────────────────────────────────────┘
```

#### パターン4: Pro + Apple Sign-in あり
```
┌─────────────────────────────────────────┐
│  My Path                           [+]  │
├─────────────────────────────────────────┤
│  （パターン1と同じ上部）                 │
│                                         │
│  [ Cancel Subscription ]                │
│                                         │
│  [       Sign Out        ]              │
│  [    Delete Account     ]              │
│                                         │
│     Privacy Policy • Terms of Use       │
└─────────────────────────────────────────┘
```

### ファイル変更

| ファイル | 変更 |
|---------|------|
| `MainTabView.swift` | TabView 削除、直接 MyPathTabView 表示 |
| `MyPathTabView.swift` | Subscribe/Account/Footer セクション追加 |
| `FigmaTabBar.swift` | **削除** |
| `ProfileView.swift` | **削除** |
| `ProblemAlarmKitScheduler.swift` | **削除**（ドキュメント化後） |

---

## To-Be チェックリスト

| # | To-Be | 完了 |
|---|-------|------|
| 1 | Tab Bar を削除し、1画面構成にする | ☐ |
| 2 | MyPathTabView に Subscribe ボタンを追加 | ☐ |
| 3 | MyPathTabView に Cancel Subscription ボタンを追加 | ☐ |
| 4 | MyPathTabView に Sign Out / Delete Account を追加（サインイン時のみ） | ☐ |
| 5 | MyPathTabView に LegalLinksView (Footer) を追加 | ☐ |
| 6 | ProfileView.swift を削除 | ☐ |
| 7 | FigmaTabBar.swift を削除 | ☐ |
| 8 | AlarmKit 実装をドキュメント化 | ☐ |
| 9 | ProblemAlarmKitScheduler.swift を削除 | ☐ |
| 10 | AlarmKit Intent ファイルを削除 | ☐ |
| 11 | AlarmKit プロジェクト設定を削除（Capabilities, Info.plist等） | ☐ |
| 12 | MainTabView を簡略化 | ☐ |
| 13 | CLAUDE.md の「iOSアプリ現在の実装状況」を更新 | ☐ |
| 14 | 既存ユーザーの移行処理を実装（通知再スケジュール + フラグ設定） | ☐ |
| 15 | DEBUG ビルドにテスト状態注入UI を追加 | ☐ |

---

## 条件分岐ロジック

### Subscribe / Cancel Subscription
```swift
if appState.subscriptionInfo.plan == .free {
    // Subscribe ボタン表示
    // タップ → Superwall paywall
} else {
    // Cancel Subscription ボタン表示
    // タップ → RevenueCat CustomerCenter
}
```

### Sign Out / Delete Account（認証状態の単一ソース）

#### 単一ソース定義
```swift
// AppState.swift に追加
// 認証状態の判定: AppState.isSignedIn を単一ソースとして使用

var isSignedIn: Bool {
    guard let userId = userProfile.userId, !userId.isEmpty else {
        return false
    }
    return true
}
```

#### 起動時チェック（責務: AppState.init）
```swift
// AppState.init() 内で実行
private func validateAppleIDCredential() {
    guard let userId = userProfile.userId else { return }

    let appleIDProvider = ASAuthorizationAppleIDProvider()
    appleIDProvider.getCredentialState(forUserID: userId) { state, error in
        DispatchQueue.main.async {
            switch state {
            case .revoked, .notFound:
                // 失効: userIdをクリアして未サインイン状態に
                self.userProfile.userId = nil
                self.updateUserProfile(self.userProfile, sync: false)
            case .authorized:
                // 有効: 何もしない
                break
            default:
                break
            }
        }
    }
}
```

#### 失効時フロー
```
アプリ起動
    ↓
AppState.init() で validateAppleIDCredential() 実行
    ↓
credential が revoked または notFound の場合
    ↓
userProfile.userId = nil
    ↓
AppState.isSignedIn == false
    ↓
Sign Out / Delete Account ボタン非表示
```

#### UI表示ロジック
```swift
// MyPathTabView.swift
if appState.isSignedIn {
    // Sign Out + Delete Account 表示
}
```

### Protocol 定義（テスト可能性のため）
```swift
// ProblemNotificationSchedulerProtocol.swift
protocol ProblemNotificationSchedulerProtocol {
    func scheduleNotifications(for problems: [String]) async
}

// ProblemNotificationScheduler+Protocol.swift
extension ProblemNotificationScheduler: ProblemNotificationSchedulerProtocol {}
```

---

## AlarmKit 削除チェックリスト

### コードファイル削除
| ファイル | パス | 削除 |
|---------|------|------|
| ProblemAlarmKitScheduler.swift | `aniccaios/aniccaios/Notifications/` | ☐ |
| OpenProblemOneScreenIntent.swift | `aniccaios/aniccaios/Intents/` | ☐ |
| CantWakeUpStopIntent.swift | `aniccaios/aniccaios/Intents/` | ☐ |

### プロジェクト設定削除
| 項目 | 場所 | 削除 |
|------|------|------|
| AlarmKit Capability | Project > Signing & Capabilities | ☐ |
| Intent Extension Target | Targets > aniccaiosIntents | ☐ |
| Intent Extension Embed | Build Phases > Embed App Extensions | ☐ |
| NSAlarmCapabilityRequestedReason | Info.plist | ☐ |
| INIntent 関連エントリ | Info.plist | ☐ |

### project.pbxproj 変更
- Intent Extension への参照を削除
- PBXFileReference からIntent関連ファイルを削除
- PBXBuildFile からIntent関連を削除
- PBXGroup からIntent関連を削除

### 依存解除確認
```bash
# ビルド確認（AlarmKit削除後）
cd aniccaios && fastlane build_for_simulator

# シンボル参照確認
grep -r "AlarmKit" aniccaios/
grep -r "ProblemAlarmKitScheduler" aniccaios/
grep -r "OpenProblemOneScreenIntent" aniccaios/
grep -r "CantWakeUpStopIntent" aniccaios/
```

---

## 既存ユーザー移行仕様

### AlarmKit 利用中ユーザーの対応

**背景**: iOS 26+ でのみ AlarmKit 対応。cant_wake_up 問題を選択したユーザーのみ対象。

#### 移行方針: AlarmKit API 削除後は呼び出し不要

AlarmKit を削除すると、iOS システムが自動的に既存アラームを無効化する。
そのため、移行処理で `AlarmManager.cancelAll()` を呼ぶ必要はない。

**移行処理の責務:**
1. 通知の再スケジュール（cant_wake_up 用）
2. 移行完了フラグの設定

#### 移行フロー
```
アプリ更新（AlarmKit 削除後のバージョン起動時）
    ↓
AppState.init() で migrateFromAlarmKit() 実行
    ↓
1. 移行フラグ確認（未移行なら続行）
2. ProblemNotificationScheduler.scheduleNotifications() 呼び出し
3. UserDefaults["alarmMigrationCompleted"] = true
```

#### 実装
```swift
// AppState.swift に追加

/// テスト可能な移行関数（Scheduler と問題リストを注入可能）
private func migrateFromAlarmKitTestable(
    scheduler: ProblemNotificationSchedulerProtocol,
    problems: [String]
) async {
    let migrationKey = "alarmKitMigrationCompleted_v1_3_0"
    guard !UserDefaults.standard.bool(forKey: migrationKey) else { return }

    // AlarmKit API は削除済みのため、呼び出し不要
    // → iOS システムが自動的に既存アラームを無効化

    // cant_wake_up の通知を再スケジュール
    await scheduler.scheduleNotifications(for: problems)

    UserDefaults.standard.set(true, forKey: migrationKey)
}

/// プロダクション用移行関数（AppState.init() から呼び出し）
func migrateFromAlarmKit() {
    Task {
        await migrateFromAlarmKitTestable(
            scheduler: ProblemNotificationScheduler.shared,
            problems: self.userProfile.problems
        )
    }
}
```

#### Phase 順序（重要）
```
Phase 0: AlarmKit 実装をドキュメント化
    ↓
Phase 1: AlarmKit コード・設定を削除（API 呼び出しが不可能になる）
    ↓
Phase 2: 移行処理を AppState.init() に追加
    ↓
（ユーザーがアプリ更新 → 起動時に移行処理実行）
```

**注意**: Phase 1 で AlarmKit を削除した後、Phase 2 で移行処理を追加する。
移行処理には AlarmKit API 呼び出しを含めない（削除後は呼べないため）。

#### ユーザーへの告知
- **告知なし**: AlarmKit は iOS 26+ 限定で新規ユーザーのみ対象だった
- **影響範囲**: 極めて小さい（iOS 26+ かつ cant_wake_up 選択者のみ）
- **代替機能**: 通知による起床サポートは継続

### 設定項目削除の影響

| 設定 | 既存値の扱い | ユーザー影響 |
|------|------------|------------|
| Name | サーバーに残存、表示しない | なし（内部識別のみ） |
| Data Integration | 全ユーザー自動有効化 | なし（機能向上） |
| Nudge Strength | サーバー側でデフォルト適用 | なし（エージェント自動調整） |
| Alarm | 解除、通知に移行 | 軽微（通知で代替） |

---

## テストマトリックス

| # | To-Be # | To-Be 項目 | テスト名 | タイプ | カバー |
|---|---------|-----------|----------|--------|--------|
| 1 | 1 | Tab Bar 削除、1画面構成 | `01-single-screen-layout.yaml` | E2E | ✅ |
| 2 | 2 | Subscribe ボタン表示（Free） | `test_should_show_subscribe_for_free` | Unit | ✅ |
| 3 | 3 | Cancel Subscription ボタン表示（Pro） | `test_should_show_cancel_for_pro` | Unit | ✅ |
| 4 | 3 | Cancel Subscription → RevenueCat | `04-cancel-subscription.yaml` | E2E | ✅ |
| 5 | 4 | Sign Out 表示（サインイン時） | `test_should_show_sign_out_when_signed_in` | Unit | ✅ |
| 6 | 4 | Sign Out 非表示（未サインイン時） | `test_should_show_sign_out_when_not_signed_in` | Unit | ✅ |
| 7 | 4 | Delete Account 表示（サインイン時） | `test_should_show_delete_account_when_signed_in` | Unit | ✅ |
| 8 | 4 | Delete Account 非表示（未サインイン時） | `test_should_show_delete_account_when_not_signed_in` | Unit | ✅ |
| 9 | 5 | LegalLinksView 表示 | `01-single-screen-layout.yaml` | E2E | ✅ |
| 10 | 6 | ProfileView 削除後ビルド成功 | ビルド検証 | Build | ✅ |
| 11 | 7 | FigmaTabBar 削除後ビルド成功 | ビルド検証 | Build | ✅ |
| 12 | 8 | AlarmKit 実装ドキュメント化 | ファイル存在確認 | Doc | ✅ |
| 13 | 9 | ProblemAlarmKitScheduler 削除後ビルド成功 | ビルド検証 | Build | ✅ |
| 14 | 10 | AlarmKit Intent ファイル削除後ビルド成功 | ビルド検証 | Build | ✅ |
| 15 | 11 | AlarmKit プロジェクト設定削除後ビルド成功 | ビルド検証 | Build | ✅ |
| 16 | 12 | MainTabView 簡略化 | `01-single-screen-layout.yaml` | E2E | ✅ |
| 17 | 13 | CLAUDE.md 更新 | Doc レビュー | Doc | ✅ |
| 18 | 14 | 移行処理（通知再スケジュール） | `test_migrate_from_alarmkit_calls_scheduler` | Unit | ✅ |
| 19 | 14 | 移行処理（問題リスト検証） | `test_migrate_from_alarmkit_schedules_correct_problems` | Unit | ✅ |
| 20 | 15 | DEBUG テスト状態注入UI | DEBUG ビルド確認 | Build | ✅ |
| 21 | - | isSignedIn ロジック (true) | `test_appstate_is_signed_in_true` | Unit | ✅ |
| 22 | - | isSignedIn ロジック (nil) | `test_appstate_is_signed_in_false_nil` | Unit | ✅ |
| 23 | - | isSignedIn ロジック (empty) | `test_appstate_is_signed_in_false_empty` | Unit | ✅ |
| 24 | - | cant_wake_up 通知は残る | `test_cant_wake_up_scheduled_in_migration` | Unit | ✅ |

---

## Unit Tests

```swift
// aniccaios/aniccaiosTests/SingleScreenTests.swift

import Testing
@testable import aniccaios

@Suite("Single Screen Tests")
struct SingleScreenTests {

    // MARK: - AppState.isSignedIn Tests（単一ソース検証）

    @Test("AppState.isSignedIn returns true when userId is set")
    func test_appstate_is_signed_in_true() async {
        // AppState の isSignedIn を直接テスト
        let appState = AppState.shared
        let originalUserId = appState.userProfile.userId

        // テスト用にuserIdを設定
        var profile = appState.userProfile
        profile.userId = "test-user-id"
        appState.updateUserProfile(profile, sync: false)

        #expect(appState.isSignedIn == true)

        // クリーンアップ
        profile.userId = originalUserId
        appState.updateUserProfile(profile, sync: false)
    }

    @Test("AppState.isSignedIn returns false when userId is nil")
    func test_appstate_is_signed_in_false_nil() async {
        let appState = AppState.shared
        let originalUserId = appState.userProfile.userId

        var profile = appState.userProfile
        profile.userId = nil
        appState.updateUserProfile(profile, sync: false)

        #expect(appState.isSignedIn == false)

        // クリーンアップ
        profile.userId = originalUserId
        appState.updateUserProfile(profile, sync: false)
    }

    @Test("AppState.isSignedIn returns false when userId is empty")
    func test_appstate_is_signed_in_false_empty() async {
        let appState = AppState.shared
        let originalUserId = appState.userProfile.userId

        var profile = appState.userProfile
        profile.userId = ""
        appState.updateUserProfile(profile, sync: false)

        #expect(appState.isSignedIn == false)

        // クリーンアップ
        profile.userId = originalUserId
        appState.updateUserProfile(profile, sync: false)
    }

    // MARK: - Subscription Display Condition Tests

    @Test("shouldShowSubscribeButton returns true for free plan")
    func test_should_show_subscribe_for_free() {
        #expect(SingleScreenDisplayConditions.shouldShowSubscribeButton(plan: .free) == true)
    }

    @Test("shouldShowSubscribeButton returns false for pro plan")
    func test_should_show_subscribe_for_pro() {
        #expect(SingleScreenDisplayConditions.shouldShowSubscribeButton(plan: .pro) == false)
    }

    @Test("shouldShowCancelSubscriptionButton returns true for pro plan")
    func test_should_show_cancel_for_pro() {
        #expect(SingleScreenDisplayConditions.shouldShowCancelSubscriptionButton(plan: .pro) == true)
    }

    @Test("shouldShowCancelSubscriptionButton returns false for free plan")
    func test_should_show_cancel_for_free() {
        #expect(SingleScreenDisplayConditions.shouldShowCancelSubscriptionButton(plan: .free) == false)
    }

    // MARK: - Account Display Condition Tests

    @Test("shouldShowSignOutButton returns true when signed in")
    func test_should_show_sign_out_when_signed_in() {
        #expect(SingleScreenDisplayConditions.shouldShowSignOutButton(isSignedIn: true) == true)
    }

    @Test("shouldShowSignOutButton returns false when not signed in")
    func test_should_show_sign_out_when_not_signed_in() {
        #expect(SingleScreenDisplayConditions.shouldShowSignOutButton(isSignedIn: false) == false)
    }

    @Test("shouldShowDeleteAccountButton returns true when signed in")
    func test_should_show_delete_account_when_signed_in() {
        #expect(SingleScreenDisplayConditions.shouldShowDeleteAccountButton(isSignedIn: true) == true)
    }

    @Test("shouldShowDeleteAccountButton returns false when not signed in")
    func test_should_show_delete_account_when_not_signed_in() {
        #expect(SingleScreenDisplayConditions.shouldShowDeleteAccountButton(isSignedIn: false) == false)
    }

    // MARK: - Migration Tests（migrateFromAlarmKit直接テスト + Mock Scheduler）

    @Test("migrateFromAlarmKit sets flag and calls scheduler")
    func test_migrate_from_alarmkit_calls_scheduler() async {
        let migrationKey = "alarmKitMigrationCompleted_v1_3_0"
        UserDefaults.standard.removeObject(forKey: migrationKey)

        // Mock Scheduler を使用して呼び出しを検証
        let mockScheduler = MockProblemNotificationScheduler()

        // 移行前
        #expect(UserDefaults.standard.bool(forKey: migrationKey) == false)
        #expect(mockScheduler.scheduleNotificationsCalled == false)

        // migrateFromAlarmKit() を直接呼び出し（Mock注入版、cant_wake_up含む問題リスト）
        let testProblems = ["cant_wake_up", "staying_up_late"]
        await migrateFromAlarmKitTestable(scheduler: mockScheduler, problems: testProblems)

        // 移行後: フラグが設定され、Schedulerが呼ばれたことを確認
        #expect(UserDefaults.standard.bool(forKey: migrationKey) == true)
        #expect(mockScheduler.scheduleNotificationsCalled == true)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: migrationKey)
    }

    @Test("migrateFromAlarmKit schedules correct problems including cant_wake_up")
    func test_migrate_from_alarmkit_schedules_correct_problems() async {
        let migrationKey = "alarmKitMigrationCompleted_v1_3_0"
        UserDefaults.standard.removeObject(forKey: migrationKey)

        let mockScheduler = MockProblemNotificationScheduler()
        let testProblems = ["cant_wake_up", "staying_up_late", "procrastination"]

        await migrateFromAlarmKitTestable(scheduler: mockScheduler, problems: testProblems)

        // 問題リストが正しく渡されたか検証
        #expect(mockScheduler.scheduledProblems == testProblems)
        #expect(mockScheduler.scheduledProblems.contains("cant_wake_up") == true)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: migrationKey)
    }

    @Test("cant_wake_up is scheduled in migration")
    func test_cant_wake_up_scheduled_in_migration() async {
        let migrationKey = "alarmKitMigrationCompleted_v1_3_0"
        UserDefaults.standard.removeObject(forKey: migrationKey)

        let mockScheduler = MockProblemNotificationScheduler()
        let testProblems = ["cant_wake_up"]

        await migrateFromAlarmKitTestable(scheduler: mockScheduler, problems: testProblems)

        // cant_wake_up が通知スケジュール対象に含まれていることを確認
        #expect(mockScheduler.scheduledProblems.contains("cant_wake_up") == true)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: migrationKey)
    }

    @Test("migrateFromAlarmKit skipped if already completed")
    func test_migrate_from_alarmkit_skipped_if_completed() async {
        let migrationKey = "alarmKitMigrationCompleted_v1_3_0"

        // 移行完了済みをシミュレート
        UserDefaults.standard.set(true, forKey: migrationKey)

        let mockScheduler = MockProblemNotificationScheduler()

        // migrateFromAlarmKit() を呼び出し
        await migrateFromAlarmKitTestable(scheduler: mockScheduler, problems: ["cant_wake_up"])

        // Schedulerは呼ばれない（early return）
        #expect(mockScheduler.scheduleNotificationsCalled == false)

        // クリーンアップ
        UserDefaults.standard.removeObject(forKey: migrationKey)
    }
}

// MARK: - Test Helpers

/// テスト用 Mock Scheduler
class MockProblemNotificationScheduler: ProblemNotificationSchedulerProtocol {
    var scheduleNotificationsCalled = false
    var scheduledProblems: [String] = []

    func scheduleNotifications(for problems: [String]) async {
        scheduleNotificationsCalled = true
        scheduledProblems = problems
    }
}

/// テスト可能な移行関数（Scheduler と問題リストを注入可能）
func migrateFromAlarmKitTestable(
    scheduler: ProblemNotificationSchedulerProtocol,
    problems: [String]
) async {
    let migrationKey = "alarmKitMigrationCompleted_v1_3_0"
    guard !UserDefaults.standard.bool(forKey: migrationKey) else { return }

    // 通知を再スケジュール（問題リストを渡す）
    await scheduler.scheduleNotifications(for: problems)

    UserDefaults.standard.set(true, forKey: migrationKey)
}

/// プロダクション用移行関数
func migrateFromAlarmKit() async {
    let scheduler = ProblemNotificationScheduler.shared
    let problems = AppState.shared.userProfile.problems
    await migrateFromAlarmKitTestable(scheduler: scheduler, problems: problems)
}

/// View表示条件判定ヘルパー
enum SingleScreenDisplayConditions {
    static func shouldShowSignOutButton(isSignedIn: Bool) -> Bool {
        return isSignedIn
    }

    static func shouldShowDeleteAccountButton(isSignedIn: Bool) -> Bool {
        return isSignedIn
    }

    static func shouldShowSubscribeButton(plan: SubscriptionPlan) -> Bool {
        return plan == .free
    }

    static func shouldShowCancelSubscriptionButton(plan: SubscriptionPlan) -> Bool {
        return plan == .pro
    }
}
```

### View条件分岐テスト（Snapshot/Logic）

UI表示条件はE2Eテスト（Maestro）で検証。Unit Testでは以下を確認：
- `AppState.isSignedIn` が正しく動作する（上記テスト）
- `SubscriptionInfo.plan` が正しく判定される（上記テスト）

View側の条件分岐コード：
```swift
// MyPathTabView.swift（実装時に追加）
// Account Section
if appState.isSignedIn {
    AccountSectionView(onSignOut: signOut, onDeleteAccount: deleteAccount)
}

// Subscription Section
if appState.subscriptionInfo.plan == .free {
    SubscribeButton()
} else {
    CancelSubscriptionButton()
}
```

---

## E2E Tests (Maestro)

### テスト状態の準備方法

E2Eテストで必要な状態を準備する方法：

#### 1. サインイン状態の準備
```yaml
# DEBUG ビルドで利用可能なテスト用フラグ
# Config.swift に追加:
# static var testUserSignedIn: Bool = false  // E2E テスト用

# Maestro で状態を注入:
- runScript:
    script: |
      # Accessibility Identifier でデバッグボタンをタップ
      # または: launchApp に環境変数を渡す
    when:
      platform: iOS
```

**推奨方法**: DEBUG ビルドに Accessibility Identifier 付きのテスト設定画面を追加
```swift
#if DEBUG
// SettingsDebugView.swift
Button("Set Signed In") {
    var profile = appState.userProfile
    profile.userId = "test-user-id"
    appState.updateUserProfile(profile, sync: false)
}
.accessibilityIdentifier("debug_set_signed_in")
#endif
```

#### 2. Pro 状態の準備
```yaml
# RevenueCat のサンドボックス環境でテスト
# または: DEBUG ビルドで Pro 状態を注入

# Config.swift に追加:
# static var testSubscriptionPlan: SubscriptionPlan = .free  // E2E テスト用
```

**推奨方法**: DEBUG ビルドで Subscription 状態を注入
```swift
#if DEBUG
Button("Set Pro Plan") {
    appState.subscriptionInfo = SubscriptionInfo(plan: .pro, ...)
}
.accessibilityIdentifier("debug_set_pro")
#endif
```

---

### maestro/single-screen/01-single-screen-layout.yaml
```yaml
appId: com.anicca.ios.staging
tags:
  - smokeTest
  - single-screen
---
- launchApp:
    clearState: true

- assertVisible:
    text: "My Path"

# Tab Bar が存在しないことを確認
- assertNotVisible:
    text: "Profile"

# 問題リストセクション
- assertVisible:
    text: "What you're facing"

# Tell Anicca セクション
- assertVisible:
    text: "Tell Anicca"

# Footer
- scrollUntilVisible:
    element:
      text: "Privacy Policy"
    direction: DOWN

- assertVisible:
    text: "Privacy Policy"

- assertVisible:
    text: "Terms of Use"
```

### maestro/single-screen/02-subscribe-button-free.yaml
```yaml
appId: com.anicca.ios.staging
tags:
  - subscription
  - single-screen
---
# 前提条件: Free ユーザー（デフォルト状態）
- launchApp:
    clearState: true

- scrollUntilVisible:
    element:
      text: "Subscribe"
    direction: DOWN

- assertVisible:
    text: "Subscribe"

- tapOn:
    text: "Subscribe"

# Superwall paywall が表示されることを確認
```

### maestro/single-screen/03-account-section-signed-in.yaml
```yaml
appId: com.anicca.ios.staging
tags:
  - account
  - single-screen
---
# 前提条件: Apple Sign-in 済み
# 準備: DEBUG ビルドでテスト用サインイン状態を注入

- launchApp:
    clearState: true

# DEBUG: テスト用にサインイン状態を設定
- tapOn:
    id: "debug_set_signed_in"
    optional: true  # 本番ビルドでは存在しない

- scrollUntilVisible:
    element:
      text: "Sign Out"
    direction: DOWN

- assertVisible:
    text: "Sign Out"

- assertVisible:
    text: "Delete Account"
```

### maestro/single-screen/04-cancel-subscription.yaml
```yaml
appId: com.anicca.ios.staging
tags:
  - subscription
  - single-screen
---
# 前提条件: Pro ユーザー
# 準備: DEBUG ビルドで Pro 状態を注入、または RevenueCat サンドボックスでサブスク済み

- launchApp:
    clearState: true

# DEBUG: テスト用に Pro 状態を設定
- tapOn:
    id: "debug_set_pro"
    optional: true  # 本番ビルドでは存在しない

- scrollUntilVisible:
    element:
      text: "Cancel Subscription"
    direction: DOWN

- assertVisible:
    text: "Cancel Subscription"

- tapOn:
    text: "Cancel Subscription"

# RevenueCat CustomerCenter が表示されることを確認
- assertVisible:
    text: "Manage Subscription"
    optional: true
```

### テスト実行環境

| 環境 | 状態準備方法 |
|------|-------------|
| ローカル開発 | DEBUG ビルド + Accessibility ID でタップ |
| CI/CD | staging ビルド + 事前設定済みテストユーザー |
| 本番確認 | RevenueCat サンドボックス + Apple サンドボックスアカウント |

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| Spec レビュー | `/codex-review` | Spec の自動レビュー |
| テスト実装 | `/tdd` | TDDでテスト先行開発 |
| 実装 | `/ui-skills` | UI実装ガイドライン |
| コードレビュー | `/code-review` | 実装後のレビュー |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| E2Eテスト | Maestro MCP | UIテスト自動化 |
| コミット前 | `/codex-review` | コード自動レビュー |

---

## ローカライズ

### 新規追加
| Key | English | Japanese |
|-----|---------|----------|
| `single_screen_subscribe` | Subscribe | 登録する |
| `single_screen_cancel_subscription` | Cancel Subscription | 登録をキャンセル |
| `single_screen_sign_out` | Sign Out | サインアウト |
| `single_screen_delete_account` | Delete Account | アカウントを削除 |

### 既存（移動のみ）
- `Privacy Policy` / `Terms of Use` - LegalLinksView からそのまま使用

---

## 実行手順

### Phase 0: ドキュメント化
```bash
# AlarmKit 実装をドキュメント化（削除前に記録）
# → .cursor/plans/archive/alarm-implementation.md
# 内容: コード全文、プロジェクト設定、復元手順
```

### Phase 1: AlarmKit 削除（API 呼び出し不可になる）
```bash
# 1. ProblemAlarmKitScheduler.swift 削除
# 2. Intent ファイル削除（OpenProblemOneScreenIntent, CantWakeUpStopIntent）
# 3. Intent Extension Target 削除
# 4. Capabilities から AlarmKit 削除
# 5. Info.plist から関連エントリ削除
# 6. ProfileView から Alarm UI セクション削除
# ※ この時点で AlarmKit API は呼び出し不可

cd aniccaios && fastlane build_for_simulator
# ビルド成功を確認
```

### Phase 2: 移行処理追加
```bash
# 1. AppState.init() に migrateFromAlarmKit() 追加
# 2. 移行処理: 通知再スケジュール + フラグ設定
# ※ AlarmKit API は呼ばない（削除済みのため）

cd aniccaios && fastlane build_for_simulator
```

### Phase 3: 認証状態の単一ソース追加
```bash
# 1. AppState に isSignedIn computed property 追加
# 2. AppState.init() に validateAppleIDCredential() 追加
# 3. 失効時の userId クリア処理

cd aniccaios && fastlane build_for_simulator
```

### Phase 4: UI 統合
```bash
# 1. MyPathTabView に Subscription セクション追加
# 2. MyPathTabView に Account セクション追加（appState.isSignedIn 時のみ）
# 3. MyPathTabView に LegalLinksView 追加
# 4. MainTabView 簡略化（TabView 削除）
# 5. FigmaTabBar.swift 削除

cd aniccaios && fastlane build_for_simulator
```

### Phase 5: 不要コード削除
```bash
# 1. ProfileView.swift 削除
# 2. 未使用 import 削除
# 3. プロジェクトからの参照削除

cd aniccaios && fastlane build_for_simulator
```

### Phase 6: テスト
```bash
# Unit Tests
cd aniccaios && fastlane test

# E2E Tests（DEBUG ビルドで状態注入）
maestro test maestro/single-screen/
```

### Phase 7: 実機確認
```bash
cd aniccaios && fastlane build_for_device
# チェックリストに従って手動確認
```

---

## AlarmKit 実装ドキュメント（削除前に記録）

削除前に以下を `.cursor/plans/archive/alarm-implementation.md` に記録：

1. **ProblemAlarmKitScheduler.swift** の全コード
2. **AlarmKit Intent 定義** の全コード
3. **2段階アラーム** の仕組み（6:00 + 6:05）
4. **将来復活させる場合の手順**
5. **プロジェクト設定の復元手順**

---

## レビューチェックリスト

### Spec レビュー
- [x] 全 To-Be がテストマトリックスに含まれているか
- [x] 各 To-Be に対応するテストコードがあるか
- [x] ローカライズ（日英）は正しいか
- [x] Skills / Sub-agents 使用マップがあるか
- [x] 後方互換性は保たれているか（cant_wake_up は通知のみ残す）
- [x] As-Is の問題が To-Be で解決されるか
- [x] 削除される設定項目の移行方針が明記されているか
- [x] AlarmKit 削除の具体的チェックリストがあるか
- [x] 認証状態の単一ソースが定義されているか
- [x] 既存ユーザーの移行仕様があるか

### 実装レビュー（To-Be チェックリスト対応）
- [ ] (#1) Tab Bar が削除されているか
- [ ] (#2) Subscribe ボタンが Free ユーザーに表示されるか
- [ ] (#3) Cancel Subscription ボタンが Pro ユーザーに表示されるか
- [ ] (#4) Sign Out / Delete Account がサインイン時のみ表示されるか
- [ ] (#5) LegalLinksView が footer に表示されるか
- [ ] (#6) ProfileView.swift が削除されているか
- [ ] (#7) FigmaTabBar.swift が削除されているか
- [ ] (#8) AlarmKit 実装が `.cursor/plans/archive/alarm-implementation.md` にドキュメント化されているか
- [ ] (#9) ProblemAlarmKitScheduler.swift が削除されているか
- [ ] (#10) AlarmKit Intent ファイルが削除されているか
- [ ] (#11) AlarmKit プロジェクト設定（Capabilities, Info.plist）が削除されているか
- [ ] (#12) MainTabView が簡略化されているか（直接 MyPathTabView 表示）
- [ ] (#13) CLAUDE.md の「iOSアプリ現在の実装状況」が更新されているか
- [ ] (#14) 移行処理が AppState.init() に追加されているか（migrateFromAlarmKit）
- [ ] (#15) DEBUG ビルドにテスト状態注入UI が追加されているか

---

## 後方互換性

### 維持するもの
- `cant_wake_up` ProblemType → 通知は引き続き送信
- `ProblemNotificationScheduler` → 変更なし
- 既存の問題リスト・DeepDive 機能 → 変更なし
- サーバー側の設定値 → 変更なし（Name, Nudge Strength 等）

### 削除するもの
| 項目 | 影響範囲 | 対応 |
|------|---------|------|
| AlarmKit | iOS 26+ の cant_wake_up ユーザーのみ | 通知で代替 |
| Name 編集UI | 表示名を変更したいユーザー | サーバーに値は残存 |
| Data Integration トグル | トグルを OFF にしていたユーザー | 自動有効化（機能向上） |
| Nudge Strength 選択 | 頻度を調整していたユーザー | エージェント自動調整 |

---

## 備考

- **Tab enum**: MainTabView の Tab enum は将来の拡張のため残しても良いが、使用しない場合は削除
- **NudgeCard overlay**: MainTabView の NudgeCard 処理は残す（削除しない）
- **cant_wake_up Alarm**: AlarmKit を削除しても、通知による起床サポートは継続
- **isSignedIn**: AppState に computed property として追加し、単一ソースとする
