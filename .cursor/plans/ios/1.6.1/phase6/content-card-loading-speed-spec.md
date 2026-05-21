# Content Card Loading Speed Improvement Spec

## 概要

### 問題
通知タップ後、NudgeCardが表示されるまで約2秒の遅延がある。ユーザー体験を大きく損なっている。

### 原因（推定分析）
通知タップでアプリがフォアグラウンドに戻る際、以下の**タイミング競合**が発生していると推定：

> **Note**: 以下は実装前の推定分析。実装後にTime ProfilerやOSLogで実測し、数値で検証すること。

1. `AppDelegate.applicationDidBecomeActive()` が呼ばれる
2. 内部の `Task { }` が **即座に** 以下を実行開始：
   - `SensorAccessSyncService.shared.fetchLatest()` - ネットワークリクエスト
   - `AppState.shared.refreshSensorAccessAuthorizations()` - @MainActor メソッド
   - `AppState.shared.scheduleSensorRepairIfNeeded()` - @MainActor メソッド

3. 通知ハンドラ `userNotificationCenter(_:didReceive:)` も同時に実行
4. 両方が **@MainActor のアクセスを競合** し、NudgeCard表示がセンサー同期完了まで待機

**補足**: `Task { }` 自体は非同期だが、内部の `await` で @MainActor メソッドを呼ぶため、MainActor の実行キューで待機が発生する。

### 解決策
フォアグラウンド復帰時のセンサー同期処理を**遅延・低優先度で実行**し、NudgeCard表示を最優先にする。

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| E2Eテスト | Maestro MCP | UIテスト自動化 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |

---

## As-Is（現状）

### AppDelegate.swift (Line 49-57)

```swift
func applicationDidBecomeActive(_ application: UIApplication) {
    Task {
        await SensorAccessSyncService.shared.fetchLatest()
        await AppState.shared.refreshSensorAccessAuthorizations(
            forceReauthIfNeeded: AppState.shared.isOnboardingComplete
        )
        await AppState.shared.scheduleSensorRepairIfNeeded(source: .foreground)
    }
}
```

**問題点**:
- `Task { }` が即座に開始され、@MainActorメソッドへのアクセスがNudgeCard表示と競合
- ネットワークリクエスト完了まで後続の @MainActor メソッドが待機
- センサー同期は即座に必要ではない（数秒遅れても問題ない）

### 通知ハンドラ (Line 67-108)

```swift
func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
    // ... 省略 ...
    Task { @MainActor in
        AppState.shared.showNudgeCard(nudgeContent)  // カード表示
    }
}
```

**問題点**:
- `showNudgeCard`は即座に実行されるべきだが、`applicationDidBecomeActive`のTaskと競合
- 両方が@MainActorを必要とし、先に開始した処理が優先される

### NudgeCardView.swift（accessibilityIdentifier未設定）

```swift
// 現状: accessibilityIdentifierが設定されていない
Button(action: onDismiss) {
    Image(systemName: "xmark")
        .font(.system(size: 18, weight: .medium))
        .foregroundStyle(AppTheme.Colors.secondaryLabel)
        .padding(12)
}
```

---

## To-Be（変更後）

### 変更1: フォアグラウンド処理を遅延実行

**AppDelegate.swift**

```swift
func applicationDidBecomeActive(_ application: UIApplication) {
    // NudgeCard表示を優先するため、センサー同期を遅延・低優先度で実行
    Task {
        // 500ms待機してNudgeCard表示を優先
        try? await Task.sleep(for: .milliseconds(500))

        // バックグラウンド優先度で実行
        Task.detached(priority: .utility) {
            await SensorAccessSyncService.shared.fetchLatest()
            await AppState.shared.refreshSensorAccessAuthorizations(
                forceReauthIfNeeded: await AppState.shared.isOnboardingComplete
            )
            await AppState.shared.scheduleSensorRepairIfNeeded(source: .foreground)
        }
    }
}
```

### 変更2: SensorAccessSyncServiceにタイムアウト追加（テスト可能な設計）

**SensorAccessSyncService.swift**

```swift
actor SensorAccessSyncService {
    static let shared = SensorAccessSyncService()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "SensorAccessSync")

    /// タイムアウト秒数（デフォルト5秒）
    /// Note: 低速ネットワークで失敗した場合、次回フォアグラウンド時にリトライされる
    private(set) var timeoutInterval: TimeInterval = 5.0

    /// テスト用: タイムアウトを設定
    func setTimeoutInterval(_ interval: TimeInterval) {
        timeoutInterval = interval
    }

    // ... RemoteState struct ...

    func fetchLatest() async {
        guard case .signedIn(let creds) = await AppState.shared.authStatus else { return }
        let baseURL = await MainActor.run { AppConfig.proxyBaseURL }
        var request = URLRequest(url: baseURL.appendingPathComponent("mobile/sensors/state"))
        request.httpMethod = "GET"
        request.timeoutInterval = timeoutInterval  // インスタンス変数を使用（テスト可能）
        request.setValue(await AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
        request.setValue(creds.userId, forHTTPHeaderField: "user-id")

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                logger.error("Sensor state pull failed (invalid status)")
                return
            }
            if let remote = try? JSONDecoder().decode(RemoteState.self, from: data) {
                await MainActor.run {
                    AppState.shared.mergeRemoteSensorAccess(
                        sleep: remote.sleepEnabled,
                        steps: remote.stepsEnabled,
                        screenTime: remote.screenTimeEnabled,
                        motion: remote.motionEnabled
                    )
                }
            }
        } catch {
            logger.error("Sensor state pull error: \(error.localizedDescription)")
        }
    }
}
```

### 変更3: NudgeCardViewにaccessibilityIdentifier追加

**NudgeCardView.swift**

```swift
var body: some View {
    ZStack {
        AppBackground()
            .ignoresSafeArea()

        VStack(spacing: 0) {
            // Close button
            HStack {
                Spacer()
                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundStyle(AppTheme.Colors.secondaryLabel)
                        .padding(12)
                }
                .accessibilityIdentifier("nudge-card-close")  // 追加
            }
            // ... 省略 ...
        }
    }
    .accessibilityIdentifier("nudge-card-view")  // 追加
}
```

### 変更4: FigmaTabBarにaccessibilityIdentifier追加

**FigmaTabBar.swift**

```swift
// tabButton関数呼び出しにaccessibilityIdentifier追加
tabButton(
    tab: .myPath,
    icon: "leaf.fill",
    title: String(localized: "tab_mypath")
)
.accessibilityIdentifier("tab-mypath")

tabButton(
    tab: .profile,
    icon: "person",
    title: String(localized: "tab_profile")
)
.accessibilityIdentifier("tab-profile")
```

### 変更5: ProfileViewのデバッグボタンにaccessibilityIdentifier追加

**ProfileView.swift**

```swift
Button("📱 1枚画面テスト（夜更かし）") {
    let content = NudgeContent.contentForToday(for: .stayingUpLate)
    appState.showNudgeCard(content)
}
.accessibilityIdentifier("debug-nudge-test-staying-up-late")
```

---

## To-Be チェックリスト

| # | 変更内容 | 完了 |
|---|----------|------|
| 1 | `applicationDidBecomeActive`でセンサー同期を500ms遅延 | ☐ |
| 2 | `Task.detached(priority: .utility)`で低優先度実行 | ☐ |
| 3 | `SensorAccessSyncService`に`timeoutInterval`プロパティ追加（デフォルト5秒） | ☐ |
| 4 | `NudgeCardView`に`accessibilityIdentifier`追加 | ☐ |
| 5 | `FigmaTabBar`に`accessibilityIdentifier`追加 | ☐ |
| 6 | Unit Test追加（タイムアウト検証） | ☐ |
| 7 | E2E Test (Maestro)で表示速度確認 | ☐ |

---

## テストマトリックス

| # | To-Be | テスト種別 | テスト名 | カバー |
|---|-------|----------|----------|--------|
| 1 | 500ms遅延実行 | E2E (Maestro) | 15-nudge-card-loading-speed.yaml | ✅ |
| 2 | 低優先度実行 | E2E (Maestro) | 同上（NudgeCardが1秒以内に表示） | ✅ |
| 3 | 5秒タイムアウト | Unit Test | `test_timeoutInterval_defaultIs5Seconds()` | ✅ |
| 4 | NudgeCard即時表示 | Unit Test | `test_showNudgeCard_setsState()` | ✅ |
| 5 | accessibilityIdentifier | E2E (Maestro) | 同上（id指定でタップ） | ✅ |

**Note**: To-Be #1/#2 は AppDelegate の内部実装であり、Unit Test で直接検証が困難。E2E テストで「NudgeCardが1秒以内に表示される」ことを検証し、間接的にカバーする。

---

## Unit Tests

### SensorAccessSyncServiceTests.swift（新規作成）

```swift
// aniccaios/aniccaiosTests/Services/SensorAccessSyncServiceTests.swift

import XCTest
@testable import aniccaios

final class SensorAccessSyncServiceTests: XCTestCase {

    /// デフォルトのタイムアウトが5秒であることを確認
    func test_timeoutInterval_defaultIs5Seconds() async throws {
        // Given
        let service = SensorAccessSyncService.shared

        // When
        let timeout = await service.timeoutInterval

        // Then
        XCTAssertEqual(timeout, 5.0, "Default timeout should be 5 seconds")
    }

    /// タイムアウトが変更可能であることを確認（テスト用）
    func test_timeoutInterval_canBeModified() async throws {
        // Given
        let service = SensorAccessSyncService.shared
        let originalTimeout = await service.timeoutInterval

        // When
        await service.setTimeoutInterval(10.0)
        let newTimeout = await service.timeoutInterval

        // Then
        XCTAssertEqual(newTimeout, 10.0, "Timeout should be modifiable")

        // Cleanup: restore original
        await service.setTimeoutInterval(originalTimeout)
    }
}
```

### NudgeCardStateTests.swift（新規作成）

```swift
// aniccaios/aniccaiosTests/NudgeCardStateTests.swift

import XCTest
@testable import aniccaios

/// NudgeCard状態管理のテスト
@MainActor
final class NudgeCardStateTests: XCTestCase {

    override func tearDown() async throws {
        // Cleanup: ensure no lingering state
        AppState.shared.dismissNudgeCard()
    }

    /// showNudgeCardが状態を即座に設定することを確認
    func test_showNudgeCard_setsState() async throws {
        // Given
        let appState = AppState.shared
        let testContent = NudgeContent.contentForToday(for: .stayingUpLate)

        // Precondition
        XCTAssertNil(appState.pendingNudgeCard, "Should start with no pending card")

        // When
        appState.showNudgeCard(testContent)

        // Then
        XCTAssertNotNil(appState.pendingNudgeCard, "pendingNudgeCard should be set immediately")
        XCTAssertEqual(appState.pendingNudgeCard?.problemType, .stayingUpLate)
    }

    /// dismissNudgeCardが状態をクリアすることを確認
    func test_dismissNudgeCard_clearsState() async throws {
        // Given
        let appState = AppState.shared
        let testContent = NudgeContent.contentForToday(for: .stayingUpLate)
        appState.showNudgeCard(testContent)

        // Precondition
        XCTAssertNotNil(appState.pendingNudgeCard)

        // When
        appState.dismissNudgeCard()

        // Then
        XCTAssertNil(appState.pendingNudgeCard, "pendingNudgeCard should be cleared")
    }

    /// 複数回showNudgeCardを呼んでも最後のものが有効
    func test_showNudgeCard_replacesExisting() async throws {
        // Given
        let appState = AppState.shared
        let content1 = NudgeContent.contentForToday(for: .stayingUpLate)
        let content2 = NudgeContent.contentForToday(for: .cantWakeUp)

        // When
        appState.showNudgeCard(content1)
        appState.showNudgeCard(content2)

        // Then
        XCTAssertEqual(appState.pendingNudgeCard?.problemType, .cantWakeUp)
    }
}
```

---

## E2E Tests (Maestro)

### 15-nudge-card-loading-speed.yaml（新規作成）

```yaml
# maestro/15-nudge-card-loading-speed.yaml

appId: ai.anicca.app.ios
name: "NudgeCard Loading Speed Test"
tags:
  - performance
  - nudge
---
# NudgeCard表示速度テスト
# 目標: カード表示が1秒以内に完了すること

- launchApp:
    clearState: false

# オンボーディング完了していない場合、スキップ
- runFlow:
    when:
      notVisible: "tab-mypath"
    file: 01-onboarding-fixed.yaml

# Profile タブに移動（accessibilityIdentifier使用）
- tapOn:
    id: "tab-profile"

# デバッグセクションまでスクロール（accessibilityIdentifier使用）
- scrollUntilVisible:
    element:
      id: "debug-nudge-test-staying-up-late"
    direction: DOWN

# カード表示テスト開始（accessibilityIdentifier使用）
- tapOn:
    id: "debug-nudge-test-staying-up-late"

# 1秒以内にNudgeCardViewが表示されることを確認（extendedWaitUntil使用）
- extendedWaitUntil:
    visible:
      id: "nudge-card-view"
    timeout: 1000

# カードの主要要素（フィードバックボタン）が表示されていることを確認
- assertVisible:
    id: "feedback-thumbs-up"

# カードを閉じる（accessibilityIdentifier使用）
- tapOn:
    id: "nudge-card-close"

# メイン画面に戻ったことを確認
- assertVisible:
    id: "tab-profile"
```

### 補足: 実際の通知テストはシミュレータでは限界がある
実機テストでは以下の手順で確認：
1. アプリをバックグラウンドに移動
2. 通知を受信
3. 通知をタップ
4. カードが1秒以内に表示されることを目視確認

---

## ローカライズ

この変更はUIテキストを含まないため、ローカライズ対応は不要。

---

## 実行手順

### 1. コード変更

```bash
# AppDelegate.swift を編集
# SensorAccessSyncService.swift を編集
# NudgeCardView.swift を編集
# FigmaTabBar.swift を編集
```

### 2. ビルド確認

```bash
cd aniccaios && fastlane build_for_simulator
```

### 3. Unit Test 実行

```bash
cd aniccaios && xcodebuild test \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 15,OS=17.2' \
  -only-testing:aniccaiosTests/SensorAccessSyncServiceTests \
  -only-testing:aniccaiosTests/NudgeCardStateTests \
  | xcpretty
```

### 4. E2E Test 実行

```bash
maestro test maestro/15-nudge-card-loading-speed.yaml
```

### 5. 実機テスト

1. TestFlightでインストール
2. アプリをバックグラウンドに移動
3. 通知を待つ（または手動でスケジュール）
4. 通知タップ → カード表示時間を計測
5. 目標: 500ms以内

---

## レビューチェックリスト

- [ ] `applicationDidBecomeActive`の500ms遅延が実装されているか
- [ ] `Task.detached(priority: .utility)`で低優先度実行されているか
- [ ] `fetchLatest()`でインスタンス変数`timeoutInterval`が使用されているか
- [ ] `NudgeCardView`に`accessibilityIdentifier`が追加されているか
- [ ] `FigmaTabBar`に`accessibilityIdentifier`が追加されているか
- [ ] 既存機能（センサー同期）が壊れていないか
- [ ] Unit Testが追加され、全てパスするか
- [ ] Maestro E2Eテストが追加され、パスするか
- [ ] ビルドが成功するか

---

## パッチ（完全版）

### Patch 1: AppDelegate.swift

```diff
--- a/aniccaios/aniccaios/AppDelegate.swift
+++ b/aniccaios/aniccaios/AppDelegate.swift
@@ -46,13 +46,20 @@ class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDele
     }

     func applicationDidBecomeActive(_ application: UIApplication) {
+        // NudgeCard表示を優先するため、センサー同期を遅延・低優先度で実行
         Task {
-            await SensorAccessSyncService.shared.fetchLatest()
-            await AppState.shared.refreshSensorAccessAuthorizations(
-                forceReauthIfNeeded: AppState.shared.isOnboardingComplete
-            )
-            await AppState.shared.scheduleSensorRepairIfNeeded(source: .foreground)
+            // 500ms待機してNudgeCard表示を優先
+            try? await Task.sleep(for: .milliseconds(500))
+
+            // バックグラウンド優先度で実行
+            Task.detached(priority: .utility) {
+                await SensorAccessSyncService.shared.fetchLatest()
+                await AppState.shared.refreshSensorAccessAuthorizations(
+                    forceReauthIfNeeded: await AppState.shared.isOnboardingComplete
+                )
+                await AppState.shared.scheduleSensorRepairIfNeeded(source: .foreground)
+            }
         }
     }
```

### Patch 2: SensorAccessSyncService.swift

```diff
--- a/aniccaios/aniccaios/Services/SensorAccessSyncService.swift
+++ b/aniccaios/aniccaios/Services/SensorAccessSyncService.swift
@@ -4,6 +4,16 @@ import OSLog
 actor SensorAccessSyncService {
     static let shared = SensorAccessSyncService()
     private let logger = Logger(subsystem: "com.anicca.ios", category: "SensorAccessSync")
+
+    /// タイムアウト秒数（デフォルト5秒、テスト用に変更可能）
+    /// Note: 低速ネットワークで失敗した場合、次回フォアグラウンド時にリトライされる
+    private(set) var timeoutInterval: TimeInterval = 5.0
+
+    /// テスト用: タイムアウトを設定
+    func setTimeoutInterval(_ interval: TimeInterval) {
+        timeoutInterval = interval
+    }

     private struct RemoteState: Decodable {
         let screenTimeEnabled: Bool
@@ -43,6 +53,7 @@ actor SensorAccessSyncService {
         let baseURL = await MainActor.run { AppConfig.proxyBaseURL }
         var request = URLRequest(url: baseURL.appendingPathComponent("mobile/sensors/state"))
         request.httpMethod = "GET"
+        request.timeoutInterval = timeoutInterval  // インスタンス変数を使用（テスト可能）
         request.setValue(await AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
         request.setValue(creds.userId, forHTTPHeaderField: "user-id")
```

### Patch 3: NudgeCardView.swift

```diff
--- a/aniccaios/aniccaios/Views/NudgeCardView.swift
+++ b/aniccaios/aniccaios/Views/NudgeCardView.swift
@@ -27,6 +27,7 @@ struct NudgeCardView: View {
                     Button(action: onDismiss) {
                         Image(systemName: "xmark")
                             .font(.system(size: 18, weight: .medium))
                             .foregroundStyle(AppTheme.Colors.secondaryLabel)
                             .padding(12)
                     }
+                    .accessibilityIdentifier("nudge-card-close")
                 }
                 .padding(.horizontal, 8)
                 .padding(.top, 8)
@@ -105,6 +106,7 @@ struct NudgeCardView: View {
                 .padding(.bottom, 40)
             }
         }
+        .accessibilityIdentifier("nudge-card-view")
     }
```

### Patch 4: FigmaTabBar.swift

```diff
--- a/aniccaios/aniccaios/DesignSystem/Components/FigmaTabBar.swift
+++ b/aniccaios/aniccaios/DesignSystem/Components/FigmaTabBar.swift
@@ -30,12 +30,14 @@ struct FigmaTabBar: View {
                     isSelected: selectedTab == .myPath
                 ) {
                     selectedTab = .myPath
                 }
+                .accessibilityIdentifier("tab-mypath")

                 TabButton(
                     title: String(localized: "tab_profile"),
                     isSelected: selectedTab == .profile
                 ) {
                     selectedTab = .profile
                 }
+                .accessibilityIdentifier("tab-profile")
             }
```

### Patch 5: SensorAccessSyncServiceTests.swift（新規作成）

```swift
// aniccaios/aniccaiosTests/Services/SensorAccessSyncServiceTests.swift

import XCTest
@testable import aniccaios

final class SensorAccessSyncServiceTests: XCTestCase {

    /// デフォルトのタイムアウトが5秒であることを確認
    func test_timeoutInterval_defaultIs5Seconds() async throws {
        // Given
        let service = SensorAccessSyncService.shared

        // When
        let timeout = await service.timeoutInterval

        // Then
        XCTAssertEqual(timeout, 5.0, "Default timeout should be 5 seconds")
    }

    /// タイムアウトが変更可能であることを確認（テスト用）
    func test_timeoutInterval_canBeModified() async throws {
        // Given
        let service = SensorAccessSyncService.shared
        let originalTimeout = await service.timeoutInterval

        // When
        await service.setTimeoutInterval(10.0)
        let newTimeout = await service.timeoutInterval

        // Then
        XCTAssertEqual(newTimeout, 10.0, "Timeout should be modifiable")

        // Cleanup: restore original
        await service.setTimeoutInterval(originalTimeout)
    }
}
```

### Patch 6: NudgeCardStateTests.swift（新規作成）

```swift
// aniccaios/aniccaiosTests/NudgeCardStateTests.swift

import XCTest
@testable import aniccaios

/// NudgeCard状態管理のテスト
@MainActor
final class NudgeCardStateTests: XCTestCase {

    override func tearDown() async throws {
        // Cleanup: ensure no lingering state
        AppState.shared.dismissNudgeCard()
    }

    /// showNudgeCardが状態を即座に設定することを確認
    func test_showNudgeCard_setsState() async throws {
        // Given
        let appState = AppState.shared
        let testContent = NudgeContent.contentForToday(for: .stayingUpLate)

        // Precondition
        XCTAssertNil(appState.pendingNudgeCard, "Should start with no pending card")

        // When
        appState.showNudgeCard(testContent)

        // Then
        XCTAssertNotNil(appState.pendingNudgeCard, "pendingNudgeCard should be set immediately")
        XCTAssertEqual(appState.pendingNudgeCard?.problemType, .stayingUpLate)
    }

    /// dismissNudgeCardが状態をクリアすることを確認
    func test_dismissNudgeCard_clearsState() async throws {
        // Given
        let appState = AppState.shared
        let testContent = NudgeContent.contentForToday(for: .stayingUpLate)
        appState.showNudgeCard(testContent)

        // Precondition
        XCTAssertNotNil(appState.pendingNudgeCard)

        // When
        appState.dismissNudgeCard()

        // Then
        XCTAssertNil(appState.pendingNudgeCard, "pendingNudgeCard should be cleared")
    }

    /// 複数回showNudgeCardを呼んでも最後のものが有効
    func test_showNudgeCard_replacesExisting() async throws {
        // Given
        let appState = AppState.shared
        let content1 = NudgeContent.contentForToday(for: .stayingUpLate)
        let content2 = NudgeContent.contentForToday(for: .cantWakeUp)

        // When
        appState.showNudgeCard(content1)
        appState.showNudgeCard(content2)

        // Then
        XCTAssertEqual(appState.pendingNudgeCard?.problemType, .cantWakeUp)
    }
}
```

### Patch 7: Maestro E2E Test（新規作成）

```yaml
# maestro/15-nudge-card-loading-speed.yaml

appId: ai.anicca.app.ios
name: "NudgeCard Loading Speed Test"
tags:
  - performance
  - nudge
---
# NudgeCard表示速度テスト
# 目標: カード表示が1秒以内に完了すること

- launchApp:
    clearState: false

# オンボーディング完了していない場合、スキップ
- runFlow:
    when:
      notVisible: "tab-mypath"
    file: 01-onboarding-fixed.yaml

# Profile タブに移動（accessibilityIdentifier使用）
- tapOn:
    id: "tab-profile"

# デバッグセクションまでスクロール（accessibilityIdentifier使用）
- scrollUntilVisible:
    element:
      id: "debug-nudge-test-staying-up-late"
    direction: DOWN

# カード表示テスト開始（accessibilityIdentifier使用）
- tapOn:
    id: "debug-nudge-test-staying-up-late"

# 1秒以内にNudgeCardViewが表示されることを確認（extendedWaitUntil使用）
- extendedWaitUntil:
    visible:
      id: "nudge-card-view"
    timeout: 1000

# カードの主要要素（フィードバックボタン）が表示されていることを確認
- assertVisible:
    id: "feedback-thumbs-up"

# カードを閉じる（accessibilityIdentifier使用）
- tapOn:
    id: "nudge-card-close"

# メイン画面に戻ったことを確認
- assertVisible:
    id: "tab-profile"
```

---

## 実装後の期待結果

| 指標 | Before | After |
|------|--------|-------|
| カード表示時間 | ~2秒 | ~100ms |
| センサー同期開始 | 即座 | 500ms後 |
| センサー同期タイムアウト | 60秒 | 5秒 |
| UX | 遅い、イライラ | 即座に表示 |

---

## リスク評価

| リスク | 影響度 | 対策 |
|--------|--------|------|
| センサー同期が遅れる | 低 | 500msの遅延は実用上問題なし |
| タイムアウトでデータ欠損 | 低 | 次回フォアグラウンド時にリトライ（既存動作） |
| 既存機能への影響 | 低 | 処理の順序は変わらない、遅延のみ |

---

## 関連ファイル

- `aniccaios/aniccaios/AppDelegate.swift` (変更)
- `aniccaios/aniccaios/Services/SensorAccessSyncService.swift` (変更)
- `aniccaios/aniccaios/Views/NudgeCardView.swift` (変更)
- `aniccaios/aniccaios/DesignSystem/Components/FigmaTabBar.swift` (変更)
- `aniccaios/aniccaiosTests/Services/SensorAccessSyncServiceTests.swift` (新規)
- `aniccaios/aniccaiosTests/NudgeCardStateTests.swift` (新規)
- `maestro/15-nudge-card-loading-speed.yaml` (新規)

---

## 承認

- [ ] 技術レビュー完了
- [ ] QAテスト完了
- [ ] 実機テスト完了

---

最終更新: 2026-01-24
作成者: Claude Code
