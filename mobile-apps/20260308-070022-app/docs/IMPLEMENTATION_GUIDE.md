# Implementation Guide: LymphaFlow

Source: [RevenueCat iOS SDK Docs](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Add RevenueCat as a Swift Package Manager dependency.」
Source: [Apple Developer SwiftUI MVVM](https://developer.apple.com/documentation/swiftui/model-data) — 「Use @StateObject for view-owned models, @ObservedObject for injected models.」
Source: [Fastlane Documentation](https://docs.fastlane.tools/actions/scan/) — 「scan: Run tests using fastlane test lane.」

---

## 1. Prerequisites

### Xcode & Environment Setup

| 項目 | 値 |
|------|-----|
| Xcode | 16.0+ |
| Swift | 5.9+ |
| iOS Deployment Target | 17.0 |
| Fastlane | bundler経由（Gemfile） |
| RevenueCat SDK | SPM: `https://github.com/RevenueCat/purchases-ios` v5.x |

### Xcode Signing Setup

Source: [Apple Developer Certificates](https://developer.apple.com/support/certificates/) — 「Team ID required for provisioning profiles.」

```bash
# .env から Team ID を読み込む（コードにハードコード禁止）
source ~/.config/mobileapp-builder/.env
# TEAM_ID, RC_API_KEY, APP_BUNDLE_ID が定義されている
```

### RC API Key 管理（コードハードコード禁止）

```swift
// LymphaFlow.xcconfig に記載:
// RC_API_KEY = appl_xxxx...
//
// Info.plist に追加:
// <key>RC_API_KEY</key><string>$(RC_API_KEY)</string>
//
// LymphaFlowApp.swift での読み込み:
let rcApiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
Purchases.configure(withAPIKey: rcApiKey)
```

### SPM Dependencies

| Package | バージョン | 追加方法 |
|---------|---------|---------|
| RevenueCat | 5.x.x | File > Add Package Dependencies > https://github.com/RevenueCat/purchases-ios |

**禁止（Greenlight CRITICAL):** RC公式UIライブラリ、分析トラッキングSDK、外部AIサービスSDK、追跡許可API（Rule 17/20/20b/21）

---

## 2. Phase Breakdown

| Phase | Feature IDs | Files | 複雑度 |
|-------|------------|-------|--------|
| Phase 1: Project Setup | — | xcconfig, Info.plist, PrivacyInfo.xcprivacy, Fastfile | 低 |
| Phase 2: Data Layer | F-001, F-002 | Models/, Services/, routines.json | 中 |
| Phase 3: Core Views | F-001, F-002, F-003, F-004 | HomeView, SessionView, ProgressView | 中 |
| Phase 4: Onboarding | F-006 | OnboardingView, NotificationPermissionView | 中 |
| Phase 5: Monetization | F-005, F-008 | PaywallView, SubscriptionService, SettingsView | 高 |
| Phase 6: Notifications | F-007 | NotificationService, SettingsView | 低 |
| Phase 7: Polish | F-001〜F-008 | DesignSystem, Localizable.xcstrings, a11y IDs | 中 |
| Phase 8: Testing | — | LymphaFlowTests/, maestro/ | 中 |

---

## 3. Phase 1: Project Setup

### 3-1. Xcode プロジェクト作成

```bash
cd /Users/anicca/anicca-project/mobile-apps/20260308-070022-app
# Xcode 16 で新規プロジェクト作成:
# Template: App
# Product Name: LymphaFlow
# Bundle Identifier: com.aniccafactory.lymphaflow
# Interface: SwiftUI
# Language: Swift
# Include Tests: YES
# Deployment Target: iOS 17.0
```

### 3-2. xcconfig 設定

```
# Config/LymphaFlow.xcconfig
RC_API_KEY = appl_PLACEHOLDER  # .envから上書き
PRODUCT_BUNDLE_IDENTIFIER = com.aniccafactory.lymphaflow
DEVELOPMENT_TEAM = $(TEAM_ID)
```

```xml
<!-- Info.plist -->
<key>RC_API_KEY</key>
<string>$(RC_API_KEY)</string>
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
```

### 3-3. PrivacyInfo.xcprivacy

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
  <key>NSPrivacyAccessedAPITypes</key>
  <array>
    <dict>
      <key>NSPrivacyAccessedAPIType</key>
      <string>NSPrivacyAccessedAPICategoryUserDefaults</string>
      <key>NSPrivacyAccessedAPITypeReasons</key>
      <array>
        <string>CA92.1</string>
      </array>
    </dict>
  </array>
  <key>NSPrivacyCollectedDataTypes</key>
  <array/>
  <key>NSPrivacyTracking</key>
  <false/>
</dict>
</plist>
```

### 3-4. Fastfile

```ruby
# LymphaFlowios/fastlane/Fastfile
lane :test do
  scan(
    scheme: "LymphaFlow",
    device: "iPhone 16 Pro",
    clean: true
  )
end

lane :build do
  gym(
    scheme: "LymphaFlow",
    export_method: "app-store",
    output_directory: "./build"
  )
end
```

---

## 4. Phase 2: Data Layer

### 4-1. routines.json（静的コンテンツ — AI不使用 Rule 21）

```json
[
  {
    "id": "face",
    "titleKey": "routine.face.title",
    "descriptionKey": "routine.face.description",
    "isPro": false,
    "programType": "standard",
    "estimatedMinutes": 5,
    "steps": [
      {
        "id": "face-1",
        "titleKey": "step.forehead.title",
        "descriptionKey": "step.forehead.description",
        "illustrationName": "step_face_forehead",
        "durationSeconds": 30
      }
    ]
  }
]
```

### 4-2. RoutineDataService.swift

```swift
final class RoutineDataService {
    func loadRoutines() -> [Routine] {
        guard let url = Bundle.main.url(forResource: "routines", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let routines = try? JSONDecoder().decode([Routine].self, from: data) else {
            return []
        }
        return routines
    }

    func freeRoutines() -> [Routine] {
        loadRoutines().filter { !$0.isPro }
    }
}
```

### 4-3. SessionStore.swift

```swift
final class SessionStore {
    private let defaults = UserDefaults.standard
    private let sessionsKey = "lf.sessions"
    private let streakCountKey = "lf.streak.count"
    private let streakLastDateKey = "lf.streak.lastDate"

    func saveSession(_ record: SessionRecord) {
        var sessions = loadSessions()
        sessions.append(record)
        if let data = try? JSONEncoder().encode(sessions) {
            defaults.set(data, forKey: sessionsKey)
        }
        updateStreak()
    }

    func loadSessions() -> [SessionRecord] {
        guard let data = defaults.data(forKey: sessionsKey),
              let sessions = try? JSONDecoder().decode([SessionRecord].self, from: data) else {
            return []
        }
        return sessions
    }

    var streakCount: Int { defaults.integer(forKey: streakCountKey) }
}
```

---

## 5. Phase 3: Core Views

### 5-1. HomeViewModel.swift（F-001）

```swift
@MainActor
final class HomeViewModel: ObservableObject {
    @Published var routines: [Routine] = []
    @Published var isPro: Bool = false

    private let routineService: RoutineDataService
    private let subscriptionService: SubscriptionServiceProtocol

    init(routineService: RoutineDataService,
         subscriptionService: SubscriptionServiceProtocol) {
        self.routineService = routineService
        self.subscriptionService = subscriptionService
    }

    func loadRoutines() {
        let all = routineService.loadRoutines()
        routines = isPro ? all : all.filter { !$0.isPro }
    }
}
```

### 5-2. TimerViewModel.swift（F-002）

```swift
@MainActor
final class TimerViewModel: ObservableObject {
    @Published var currentStepIndex: Int = 0
    @Published var timeRemaining: Int = 0
    @Published var isRunning: Bool = false
    @Published var isCompleted: Bool = false

    private var timer: Timer?
    private let steps: [Step]
    private let sessionStore: SessionStore

    init(steps: [Step], sessionStore: SessionStore) {
        self.steps = steps
        self.sessionStore = sessionStore
        self.timeRemaining = steps.first?.durationSeconds ?? 30
    }

    func start() { isRunning = true; scheduleTimer() }
    func pause() { isRunning = false; timer?.invalidate() }

    private func scheduleTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    private func tick() {
        if timeRemaining > 0 {
            timeRemaining -= 1
        } else {
            advanceStep()
        }
    }

    private func advanceStep() {
        if currentStepIndex < steps.count - 1 {
            currentStepIndex += 1
            timeRemaining = steps[currentStepIndex].durationSeconds
        } else {
            isCompleted = true
            isRunning = false
            timer?.invalidate()
        }
    }
}
```

---

## 6. Phase 4: Onboarding（F-006）

### 6-1. OnboardingViewModel.swift

```swift
@MainActor
final class OnboardingViewModel: ObservableObject {
    @Published var currentPage: Int = 0
    @Published var hasCompletedOnboarding: Bool = false
    @Published var showPaywall: Bool = false

    let pages: [OnboardingPage] = [
        OnboardingPage(titleKey: "onboarding.page1.title", imageNamed: "onboarding1"),
        OnboardingPage(titleKey: "onboarding.page2.title", imageNamed: "onboarding2"),
        OnboardingPage(titleKey: "onboarding.page3.title", imageNamed: "onboarding3")
    ]

    // 最終ページ後: 通知許可 → PaywallView（Rule 20）
    func advance() {
        if currentPage < pages.count - 1 {
            currentPage += 1
        } else {
            showPaywall = true
        }
    }

    func completeOnboarding() {
        UserDefaults.standard.set(true, forKey: "lf.onboarding.completed")
        hasCompletedOnboarding = true
    }
}
```

### 6-2. 最終画面: PaywallView（Rule 20: Maybe Later 必須）

オンボーディング最終ステップは必ずPaywallViewを表示。[Maybe Later]ボタンで閉じられる（ソフトペイウォール）。

---

## 7. Phase 5: Monetization（F-005, F-008）

### 7-1. SubscriptionService.swift

Product IDテーブル:

| Product ID | Type | Price | Trial |
|-----------|------|-------|-------|
| `com.aniccafactory.lymphaflow.monthly` | auto-renewable | $4.99/month | なし |
| `com.aniccafactory.lymphaflow.annual` | auto-renewable | $29.99/year | 7-day |

```swift
import RevenueCat
// RC公式UIライブラリ は import 禁止（Rule 20）

final class SubscriptionService: SubscriptionServiceProtocol {
    @Published private(set) var isPro: Bool = false

    func configure() {
        // LymphaFlowApp.swift にて呼び出す
        // rcApiKey は Bundle.main.infoDictionary["RC_API_KEY"]
    }

    func fetchOfferings() async throws -> Offerings {
        try await Purchases.shared.offerings()
    }

    func purchase(package: Package) async throws -> CustomerInfo {
        // Rule 20: 自前PaywallViewから呼び出す
        let result = try await Purchases.shared.purchase(package: package)
        isPro = result.customerInfo.entitlements["pro"]?.isActive == true
        return result.customerInfo
    }

    func restorePurchases() async throws -> CustomerInfo {
        let info = try await Purchases.shared.restorePurchases()
        isPro = info.entitlements["pro"]?.isActive == true
        return info
    }
}
```

### 7-2. PaywallView.swift（自前SwiftUI — RC公式UIライブラリ 禁止 Rule 20）

```swift
struct PaywallView: View {
    @StateObject private var vm: PaywallViewModel
    let onDismiss: () -> Void  // Maybe Later

    var body: some View {
        ScrollView {
            VStack(spacing: DSSpacing.lg) {
                // Headline（価値訴求）
                Text("onboarding.paywall.headline")
                    .accessibilityIdentifier("paywall_headline")

                // 5箇条のベネフィット
                BenefitListView()

                // 価格グリッド（Annual: Best Value、Monthly）
                PricingGridView(selectedPackage: $vm.selectedPackage)
                    .accessibilityIdentifier("paywall_pricing_grid")

                // Save 50% バッジ
                DiscountBadgeView()

                // CTA ボタン
                Button(action: vm.subscribe) {
                    Text(vm.ctaTitle)
                        .accessibilityIdentifier("paywall_cta_button")
                }
                .buttonStyle(PrimaryButtonStyle())

                // Maybe Later（Rule 20: 必須）
                Button("paywall.maybe_later", action: onDismiss)
                    .accessibilityIdentifier("paywall_maybe_later_button")

                // Social Proof + FAQ + Privacy Links
                SocialProofView()
                FAQView()
                PrivacyLinksView()
            }
        }
    }
}
```

---

## 8. Phase 6: Notifications（F-007）

```swift
final class NotificationService {
    func requestAuthorization() async -> Bool {
        let center = UNUserNotificationCenter.current()
        let granted = try? await center.requestAuthorization(options: [.alert, .sound, .badge])
        return granted ?? false
    }

    func scheduleDailyReminder(hour: Int, minute: Int, identifier: String) {
        let content = UNMutableNotificationContent()
        content.title = NSLocalizedString("notification.reminder.title", comment: "")
        content.body = NSLocalizedString("notification.reminder.body", comment: "")
        content.sound = .default

        var dateComponents = DateComponents()
        dateComponents.hour = hour
        dateComponents.minute = minute
        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)
        let request = UNNotificationRequest(identifier: identifier, content: content, trigger: trigger)
        UNUserNotificationCenter.current().add(request)
    }
}
```

---

## 9. Phase 7: Polish（F-001〜F-008）

### 9-1. DesignSystem

```swift
// Colors.swift
enum DSColor {
    static let primary = Color("Primary")    // Teal #2EC4B6
    static let secondary = Color("Secondary") // Soft Purple #CBB8F7
    static let background = Color("Background")
    static let surface = Color("Surface")
    static let textPrimary = Color("TextPrimary")
    static let textSecondary = Color("TextSecondary")
    static let success = Color("Success")     // #2ECC71
    static let error = Color("Error")         // #E74C3C
}

// Typography.swift
enum DSFont {
    static let largeTitle: Font = .system(size: 34, weight: .bold)
    static let title1: Font = .system(size: 28, weight: .bold)
    static let title2: Font = .system(size: 22, weight: .semibold)
    static let headline: Font = .system(size: 17, weight: .semibold)
    static let body: Font = .system(size: 17, weight: .regular)
    static let caption: Font = .system(size: 12, weight: .regular)
}

// Spacing.swift
enum DSSpacing {
    static let xs:   CGFloat = 4
    static let sm:   CGFloat = 8
    static let md:   CGFloat = 12   // カード内パディング（コンパクト）
    static let base: CGFloat = 16   // 標準パディング（スクリーンマージン）
    static let lg:   CGFloat = 24
    static let xl:   CGFloat = 32
    static let xxl:  CGFloat = 48
    static let xxxl: CGFloat = 64
}
```

### 9-2. Localizable.xcstrings（en-US + ja）

主要キー（全UIテキストをLocalizableに集約）:
- `routine.face.title`, `routine.neck.title`, etc.
- `onboarding.page1.title`, `onboarding.paywall.headline`
- `notification.reminder.title`, `notification.reminder.body`
- `paywall.maybe_later`, `paywall.cta.monthly`, `paywall.cta.annual`

### 9-3. accessibilityIdentifier（Maestro E2E用）

| View | accessibilityIdentifier |
|------|------------------------|
| HomeView ルーティン一覧 | `home_routine_list` |
| RoutineCardView（F-001） | `routine_card_{id}` |
| SessionView タイマー | `session_timer_label` |
| SessionView 次へボタン | `session_next_button` |
| OnboardingView ページ | `onboarding_page_{index}` |
| PaywallView CTA | `paywall_cta_button` |
| PaywallView Maybe Later | `paywall_maybe_later_button` |
| SettingsView Upgrade | `settings_upgrade_button` |
| ProgressView ストリーク | `progress_streak_label` |

---

## 10. Phase 8: Testing & Release Prep

### Unit Tests（最低30テスト）

| テスト対象 | テスト数 | 主要検証 |
|----------|---------|---------|
| Routine model decoding | 3 | JSON decode、isPro flag |
| SessionStore CRUD | 5 | save/load/streak計算 |
| TimerViewModel | 8 | tick/advance/complete |
| SubscriptionService | 6 | purchase/restore/isPro |
| NotificationService | 4 | schedule/cancel |
| HomeViewModel | 4 | free/pro filter |

### E2E Tests（Maestro 8フロー）

| フロー | ファイル | タグ |
|-------|---------|------|
| オンボーディング完了 | `maestro/onboarding.yaml` | smokeTest |
| タイマー実行 | `maestro/timer.yaml` | smokeTest |
| 設定画面 | `maestro/settings.yaml` | — |
| 月額サブスク | `maestro/payment-monthly.yaml` | — |
| 年額サブスク | `maestro/payment-annual.yaml` | — |
| 支払い失敗 | `maestro/payment-failure.yaml` | — |

---

## 11. Build & Run

| タスク | コマンド |
|--------|---------|
| テスト実行 | `cd LymphaFlowios && fastlane test` |
| ビルド | `cd LymphaFlowios && fastlane build` |
| アーカイブ | `cd LymphaFlowios && fastlane archive` |
| Greenlight チェック | `greenlight preflight LymphaFlowios/` |

**Greenlight CRITICAL チェック（Rule 17, 20, 20b, 21）:**

```bash
# Rule 17: 分析・トラッキング系SDK禁止
# greenlight preflight で自動チェック（CRITICAL=0 必須）

# Rule 20: RC公式UIライブラリ禁止
# greenlight preflight で自動チェック（CRITICAL=0 必須）

# Rule 20b: ATT 禁止
# Rule 20b: ATT追跡API禁止
# greenlight preflight で自動チェック（CRITICAL=0 必須）

# Rule 21: AI API 禁止
# Rule 21: 外部AIサービス禁止
# greenlight preflight で自動チェック（CRITICAL=0 必須）
```
