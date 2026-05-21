# Implementation Guide: VagusReset

Source: [Apple Developer Documentation — Xcode Project Setup](https://developer.apple.com/documentation/xcode/creating-an-xcode-project-for-an-app)
Source: [RevenueCat iOS SDK Getting Started](https://www.revenuecat.com/docs/getting-started/installation/ios) — 「Configure Purchases.shared in your app delegate or @main」
Source: [Swift Package Manager Documentation](https://www.swift.org/documentation/package-manager/) — 「Add dependencies via File > Add Package Dependencies」

---

## 1. Prerequisites

| 項目 | 要件 |
|------|------|
| Xcode | 16.0+ |
| Swift | 5.10+ |
| iOS Simulator | iPhone 15 Pro (iOS 17.x) 以上 |
| RevenueCat Account | RevenueCat dashboard でアプリ・商品設定済み（US-005b 完了後） |
| RC_PUBLIC_KEY | `.env` ファイルに保管（コードにハードコード禁止） |

### 環境セットアップ
```bash
# 1. プロジェクト作成後、xcconfig 設定
echo 'RC_PUBLIC_KEY = appl_xxxxxxxx' >> VagusReset/Config/VagusReset.xcconfig

# 2. Info.plist に追加（自動またはプロジェクト設定）
# Key: RC_PUBLIC_KEY, Value: $(RC_PUBLIC_KEY)

# 3. RevenueCat SPM 追加
# Xcode > File > Add Package Dependencies
# URL: https://github.com/RevenueCat/purchases-ios
# Package: RevenueCat のみ（RC-UI-package は選択しない）
```

### Xcode Signing 設定
```
Xcode > Signing & Capabilities
  Team: Daisuke Nakajima (Team ID: YOUR_TEAM_ID)
  Bundle Identifier: com.aniccafactory.vagusreset
  Automatically manage signing: ON
```

### RC_PUBLIC_KEY 読み込み（コードにハードコード禁止）
```swift
// App/VagusResetApp.swift で使用
let rcKey = Bundle.main.infoDictionary?["RC_PUBLIC_KEY"] as? String ?? ""
Purchases.configure(withAPIKey: rcKey)
```

---

## 2. Phase Breakdown

| Phase | Features (F-ID) | 主要ファイル | Complexity |
|-------|----------------|------------|-----------|
| Phase 1: Project Setup | — | xcconfig, PrivacyInfo.xcprivacy, Info.plist | Low |
| Phase 2: Data Layer | F-001 | Exercise.swift, ExerciseData.json, ExerciseRepository, Services Protocols | Medium |
| Phase 3: Onboarding + Paywall | F-004, F-006, F-008 | OnboardingView, PaywallView, OnboardingViewModel | Medium |
| Phase 4: Core Screens | F-002, F-003, F-005, F-007 | HomeView, SessionView, TimerView, SettingsView | High |
| Phase 5: Monetization | F-004 (deep) | SubscriptionService, RevenueCat configure | Medium |
| Phase 6: Polish | F-009, F-010 | ProgressCalendarView, completion animation | Low |
| Phase 7: Testing & Release Prep | All | Tests/, Maestro YAML | Medium |

---

## 3. Phase 1: Project Setup

### 1.1 Xcode プロジェクト作成
```
File > New > Project > iOS > App
Product Name: VagusReset
Bundle ID: com.aniccafactory.vagusreset
Interface: SwiftUI
Language: Swift
```

### 1.2 xcconfig 作成（API Key 管理）
```bash
mkdir -p VagusReset/Config
cat > VagusReset/Config/VagusReset.xcconfig << 'EOF'
// VagusReset.xcconfig
// NEVER commit real keys. Use .env for injection.
RC_PUBLIC_KEY = PLACEHOLDER
EOF
```

### 1.3 Info.plist 設定
```xml
<!-- Info.plist に追加 -->
<key>RC_PUBLIC_KEY</key>
<string>$(RC_PUBLIC_KEY)</string>
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
```

### 1.4 PrivacyInfo.xcprivacy 追加
```
File > New > File > Property List
Name: PrivacyInfo.xcprivacy
Target: VagusReset (main target)
```
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
      <array><string>CA92.1</string></array>
    </dict>
  </array>
  <key>NSPrivacyTracking</key>
  <false/>
  <key>NSPrivacyCollectedDataTypes</key>
  <array/>
</dict>
</plist>
```

### 1.5 RevenueCat SPM 追加
```
Xcode > File > Add Package Dependencies
URL: https://github.com/RevenueCat/purchases-ios
Version: Up to Next Major 4.0.0
Product: RevenueCat（RC-UI-package は絶対に選択しない — Rule 20）
```

---

## 4. Phase 2: Core Features

### 4.1 Exercise Model（F-001）
```swift
// Models/Exercise.swift
struct Exercise: Codable, Identifiable, Equatable {
    let id: String
    let title: String
    let titleJa: String
    let category: ExerciseCategory
    let durationSeconds: Int
    let description: String
    let descriptionJa: String
    let isPremium: Bool
    let iconName: String
    let order: Int
}

enum ExerciseCategory: String, Codable {
    case humming, gargling, cold, diaphragm, laughter, tapping
}
```

### 4.2 ExerciseData.json（20+エクササイズ静的コンテンツ）
```json
[
  {
    "id": "humming-01",
    "title": "Humming Breath",
    "titleJa": "ハミング呼吸",
    "category": "humming",
    "durationSeconds": 60,
    "description": "Hum for 60 seconds to stimulate the vagus nerve through vocal vibrations.",
    "descriptionJa": "60秒間哼って、声の振動で迷走神経を刺激します。",
    "isPremium": false,
    "iconName": "music.note",
    "order": 1
  },
  {
    "id": "gargling-01",
    "title": "Deep Gargle",
    "titleJa": "深いうがい",
    "category": "gargling",
    "durationSeconds": 30,
    "description": "Gargle water for 30 seconds to activate throat muscles connected to the vagus nerve.",
    "descriptionJa": "30秒間深くうがいして、迷走神経につながる喉の筋肉を活性化します。",
    "isPremium": false,
    "iconName": "drop.fill",
    "order": 2
  }
]
```
（残り18+エクササイズも同形式で追加）

### 4.3 ExerciseRepository
```swift
// Services/ExerciseRepository.swift
class ExerciseRepository {
    private let exercises: [Exercise]

    init() {
        guard let url = Bundle.main.url(forResource: "ExerciseData", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let decoded = try? JSONDecoder().decode([Exercise].self, from: data) else {
            self.exercises = []
            return
        }
        self.exercises = decoded.sorted { $0.order < $1.order }
    }

    func loadAll() -> [Exercise] { exercises }
    func loadFree() -> [Exercise] { exercises.filter { !$0.isPremium } }
    func loadPremium() -> [Exercise] { exercises.filter { $0.isPremium } }
}
```

### 4.4 StreakService（F-005）
```swift
// Services/StreakService.swift
class StreakService {
    private let defaults = UserDefaults.standard
    private let kCurrent = "vagusreset.streak.current"
    private let kLastDate = "vagusreset.streak.lastDate"
    private let kDates = "vagusreset.streak.completedDates"

    func recordSessionCompletion(date: Date = Date()) {
        let today = Calendar.current.startOfDay(for: date)
        let isoToday = ISO8601DateFormatter().string(from: today)
        var dates = defaults.stringArray(forKey: kDates) ?? []
        guard !dates.contains(isoToday) else { return }
        dates.append(isoToday)
        defaults.set(dates, forKey: kDates)
        updateStreak(today: today)
    }

    func getCurrentStreak() -> Int { defaults.integer(forKey: kCurrent) }

    func getLastSessionDate() -> Date? {
        guard let isoString = defaults.stringArray(forKey: kDates)?.last else { return nil }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        return formatter.date(from: isoString)
    }

    func getCompletedDates() -> [Date] {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withFullDate]
        return (defaults.stringArray(forKey: kDates) ?? [])
            .compactMap { formatter.date(from: $0) }
    }
}
```

### 4.5 SessionViewModel（F-002）
```swift
// ViewModels/SessionViewModel.swift
@MainActor
class SessionViewModel: ObservableObject {
    @Published var timeRemaining: Int
    @Published var isRunning = false
    @Published var isComplete = false

    private let exercise: Exercise
    private var timer: AnyCancellable?

    init(exercise: Exercise) {
        self.exercise = exercise
        self.timeRemaining = exercise.durationSeconds
    }

    func start() {
        isRunning = true
        timer = Timer.publish(every: 1, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                guard let self, self.timeRemaining > 0 else {
                    self?.complete()
                    return
                }
                self.timeRemaining -= 1
            }
    }

    func pause() { isRunning = false; timer?.cancel() }

    func resume() {
        guard !isRunning, !isComplete else { return }
        // timeRemaining はリセットしない — 一時停止した位置から再開
        start()
    }

    private func complete() {
        timer?.cancel()
        isRunning = false
        isComplete = true
    }
}
```

---

## 5. Phase 3: Monetization

### RevenueCat SDK 実装（F-004）

**🔴 必須: 自前 PaywallView — RC-UI-package は絶対禁止（Rule 20）**

```swift
// App/VagusResetApp.swift
import SwiftUI
import RevenueCat

@main
struct VagusResetApp: App {
    init() {
        let rcKey = Bundle.main.infoDictionary?["RC_PUBLIC_KEY"] as? String ?? ""
        Purchases.configure(withAPIKey: rcKey)
        Purchases.logLevel = .warn
    }
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
```

```swift
// Services/SubscriptionServiceProtocol.swift
import RevenueCat

protocol SubscriptionServiceProtocol: ObservableObject {
    var isPremium: Bool { get }
    func checkPremiumStatus() async
    func fetchOfferings() async throws -> Offerings
    func purchase(package: Package) async throws -> PurchaseResultData
    func restorePurchases() async throws -> CustomerInfo
}
```

```swift
// Services/SubscriptionService.swift
import RevenueCat

@MainActor
class SubscriptionService: SubscriptionServiceProtocol {
    @Published private(set) var isPremium = false

    func checkPremiumStatus() async {
        let info = try? await Purchases.shared.customerInfo()
        isPremium = info?.entitlements["premium"]?.isActive == true
    }

    func fetchOfferings() async throws -> Offerings {
        try await Purchases.shared.offerings()
    }

    func purchase(package: Package) async throws -> PurchaseResultData {
        try await Purchases.shared.purchase(package: package)
    }

    func restorePurchases() async throws -> CustomerInfo {
        try await Purchases.shared.restorePurchases()
    }
}
```

### Product IDs

| Product ID | Type | Price | Trial |
|-----------|------|-------|-------|
| `com.aniccafactory.vagusreset.monthly` | Auto-Renewing Subscription | $4.99/mo | 7 days |
| `com.aniccafactory.vagusreset.annual` | Auto-Renewing Subscription | $29.99/yr | 7 days |

### PaywallView（自前 SwiftUI — Rule 20）
```swift
// Views/Onboarding/PaywallView.swift
import SwiftUI
import RevenueCat

struct PaywallView: View {
    @EnvironmentObject var subscriptionService: SubscriptionService
    @State private var offerings: Offerings?
    @State private var selectedPackage: Package?
    @State private var isPurchasing = false
    @Binding var isPresented: Bool

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header: value proposition
                // Benefit bullets (5 items)
                // Pricing grid (Monthly + Annual, highlight Annual)
                // "Save 50%" badge on Annual
                // CTA button: "Start My Reset"
                // [Maybe Later] dismiss button
                // FAQ section
                // Privacy Policy + Terms links
            }
        }
        .task { await loadOfferings() }
    }

    private func loadOfferings() async {
        offerings = try? await subscriptionService.fetchOfferings()
        selectedPackage = offerings?.current?.availablePackages
            .first { $0.packageType == .annual }
    }

    private func purchase() async {
        guard let package = selectedPackage else { return }
        isPurchasing = true
        defer { isPurchasing = false }
        do {
            let result = try await subscriptionService.purchase(package: package)
            if !result.userCancelled {
                isPresented = false
            }
        } catch {
            // ARCHITECTURE.md §12: 購入失敗時はエラーアラートを表示
            errorMessage = error.localizedDescription
            showErrorAlert = true
        }
    }
}
```

---

## 6. Phase 4: Polish

### ProgressCalendarView（F-009 — 有料機能）
```swift
// Views/Settings/ProgressCalendarView.swift
struct ProgressCalendarView: View {
    let completedDates: [Date]
    // LazyVGrid カレンダー表示
    // 完了日: accent color circle
    // 未完了日: gray circle
}
```

### 完了アニメーション（F-010）
```swift
// Views/Session/SessionView.swift (completion overlay)
// .scaleEffect + .opacity で pulse animation
// withAnimation(.spring(duration: 0.6)) { isShowingCompletion = true }
```

### Localization
```
VagusReset/
└── Localizable.xcstrings  # String Catalog (Xcode 15+)
```
対応言語: en-US, ja（最低限のキー: exercise titles, UI strings, notification content）

---

## 7. Phase 5: Testing & Release Prep

| Step | Tool | Command |
|------|------|---------|
| Unit Test | XCTest | `cd VagusResetios && fastlane test` |
| E2E Test | Maestro | `maestro test maestro/` |
| Build | fastlane | `cd VagusResetios && fastlane build` |
| Greenlight | greenlight | `greenlight preflight VagusResetios/` |
| Archive & Upload | fastlane | `cd VagusResetios && fastlane release` |

**テスト優先度:**
1. `StreakServiceTests` — UserDefaults の読み書き・連続日数計算
2. `SubscriptionServiceTests` — MockSubscriptionService で purchase/restore フロー
3. `SessionViewModelTests` — タイマーの start/pause/complete

---

## 8. Build & Run

| Task | Command |
|------|---------|
| 依存関係インストール | Xcode が自動解決（SPM） |
| ビルド（シミュレータ） | `cd VagusResetios && fastlane test` |
| ビルド（実機） | `cd VagusResetios && fastlane build` |
| アーカイブ | `cd VagusResetios && fastlane archive` |
| TestFlight アップロード | `cd VagusResetios && fastlane release` |

**xcconfig RC_PUBLIC_KEY 注入:**
```bash
# .env から xcconfig に注入（fastlane pre-action）
source ~/.config/mobileapp-builder/.env
sed -i '' "s/RC_PUBLIC_KEY = PLACEHOLDER/RC_PUBLIC_KEY = $RC_PUBLIC_KEY/" \
  VagusReset/Config/VagusReset.xcconfig
```

**fastlane/Fastfile 必須 lanes:**
```ruby
lane :test do
  run_tests(scheme: "VagusReset", device: "iPhone 15 Pro")
end

lane :build do
  gym(scheme: "VagusReset", export_method: "development")
end

lane :archive do
  gym(scheme: "VagusReset", export_method: "app-store")
end

lane :upload_to_asc do
  deliver(skip_screenshots: true, skip_metadata: true)
end

lane :release do
  gym(scheme: "VagusReset", export_method: "app-store")
  upload_to_testflight
end
```
