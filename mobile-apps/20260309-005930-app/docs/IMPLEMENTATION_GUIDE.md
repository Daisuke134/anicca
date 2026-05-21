# Implementation Guide: LumaRed

Source: [Apple Developer: Xcode Project Setup](https://developer.apple.com/documentation/xcode) — 「Configure build settings, signing, and capabilities in Xcode project editor.」
Source: [RevenueCat iOS Quickstart](https://www.revenuecat.com/docs/getting-started/quickstart/ios-swift) — 「Purchases.configure(withAPIKey:) at app launch.」
Source: [Apple Developer: BGTaskScheduler](https://developer.apple.com/documentation/backgroundtasks/bgtaskscheduler) — 「Register tasks in application(_:didFinishLaunchingWithOptions:) before schedule.」

---

## 1. Prerequisites

### 環境セットアップ

| 項目 | 値 |
|------|-----|
| Xcode | 16.0+ |
| Swift | 5.10+ |
| iOS Deployment Target | 17.0 |
| macOS | macOS 15+ |
| Team ID | ANICCAFACTORY |
| Bundle ID | com.aniccafactory.lumared |

### SPM Dependencies

| Package | URL | Version |
|---------|-----|---------|
| RevenueCat | https://github.com/RevenueCat/purchases-ios | ≥ 5.0 |

**禁止 SPM パッケージ:**
- RC-UI-library（Rule 20）
- tracking-SDK / third-party-analytics / アナリティクス系（Rule 17）
- third-party-AI-API / Gemini SDK（Rule 21）
- AppTrackingTransparency（Rule 20b）

### xcconfig (API Key 管理)

🔴 **RevenueCat API Key はコードにハードコード禁止。**

```
// LumaRed.xcconfig
RC_API_KEY = appl_xxxxxxxxxxxx   // .env から注入。gitignoreに追加
```

```swift
// LumaRedApp.swift
let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
Purchases.configure(withAPIKey: apiKey)
```

Info.plist に追加:
```xml
<key>RC_API_KEY</key>
<string>$(RC_API_KEY)</string>
```

### Xcode Signing

```
# secrets 読み込み
source ~/.config/mobileapp-builder/.env
security unlock-keychain -p "$KEYCHAIN_PASSWORD" ~/Library/Keychains/login.keychain-db

# Fastlane ビルド（xcodebuild直接禁止）
cd LumaRedios && fastlane build
```

---

## 2. Phase Breakdown

| Phase | Feature IDs | Files | Complexity |
|-------|------------|-------|-----------|
| Phase 1: Project Setup | — | Xcode project, xcconfig, PrivacyInfo.xcprivacy, Info.plist | Medium |
| Phase 2: Data Layer | F-001, F-003 | Models/, Services/SessionService.swift, ProtocolLibrary.swift | Low |
| Phase 3: Core Features | F-001, F-002 | Views/Home/, Views/Timer/, ViewModels/ | Medium |
| Phase 4: Monetization | F-004 | Services/SubscriptionService.swift, Views/Onboarding/PaywallView.swift | High |
| Phase 5: Notifications & Dashboard | F-005, F-006 | Services/NotificationService.swift, Views/Dashboard/ | Medium |
| Phase 6: Onboarding | F-004 | Views/Onboarding/OnboardingView.swift | Medium |
| Phase 7: Polish | — | Localizable.xcstrings, DESIGN_SYSTEM tokens適用, a11y IDs | Low |
| Phase 8: Testing & Release | — | Tests/, maestro/, fastlane | High |

---

## 3. Phase 1: Project Setup

### Xcode プロジェクト作成

```bash
# Fastlane 経由（xcodebuild直接禁止）
cd mobile-apps/20260309-005930-app
mkdir LumaRedios && cd LumaRedios
# Xcode.app で新規プロジェクト作成: iOS App, SwiftUI, Swift
# Bundle ID: com.aniccafactory.lumared
# Minimum Deployment: iOS 17.0
```

### SPM 追加

Xcode → File → Add Package Dependencies:
- `https://github.com/RevenueCat/purchases-ios` → `RevenueCat` ターゲットのみ選択（RC-UI-libraryは選択しない）

### PrivacyInfo.xcprivacy

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
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

### Info.plist 必須追加

```xml
<!-- 暗号化除外宣言 -->
<key>ITSAppUsesNonExemptEncryption</key>
<false/>
<!-- BackgroundTask識別子 -->
<key>BGTaskSchedulerPermittedIdentifiers</key>
<array>
    <string>com.aniccafactory.lumared.timer</string>
</array>
<!-- RevenueCat API Key -->
<key>RC_API_KEY</key>
<string>$(RC_API_KEY)</string>
```

---

## 4. Phase 2: Data Layer

### ProtocolLibrary.swift — 静的コンテンツ（AI不使用 — Rule 21）

```swift
// Models/ProtocolLibrary.swift
struct LightProtocol: Codable, Identifiable {
    let id: String
    let name: String
    let nameJa: String
    let bodyPart: BodyPart
    let wavelength: String
    let distance: String
    let duration: Int           // seconds
    let frequency: String
    let evidenceSummary: String
    let evidenceSummaryJa: String
    let isPremium: Bool
}

enum BodyPart: String, Codable, CaseIterable {
    case face, joint, wound, back, fullBody
}

enum ProtocolLibrary {
    static let all: [LightProtocol] = [
        LightProtocol(
            id: "face",
            name: "Face & Skin",
            nameJa: "顔・肌",
            bodyPart: .face,
            wavelength: "630–660nm (red)",
            distance: "6–12 inches",
            duration: 600,      // 10 minutes
            frequency: "Daily",
            evidenceSummary: "Stimulates collagen production. PBM shown to reduce wrinkles in RCTs.",
            evidenceSummaryJa: "コラーゲン産生を促進。RCTでシワ改善効果が確認されています。",
            isPremium: false
        ),
        LightProtocol(
            id: "joint",
            name: "Joint & Muscle",
            nameJa: "関節・筋肉",
            bodyPart: .joint,
            wavelength: "660–850nm (red + near-IR)",
            distance: "2–6 inches",
            duration: 900,      // 15 minutes
            frequency: "Daily or every other day",
            evidenceSummary: "Reduces inflammation. NASA research supports PBM for muscle recovery.",
            evidenceSummaryJa: "炎症を軽減。NASAの研究が筋肉回復への効果を支持しています。",
            isPremium: false
        ),
        LightProtocol(
            id: "wound",
            name: "Wound Healing",
            nameJa: "傷の回復",
            bodyPart: .wound,
            wavelength: "630–670nm (red)",
            distance: "1–4 inches",
            duration: 300,      // 5 minutes
            frequency: "2x daily",
            evidenceSummary: "Accelerates wound closure. Multiple clinical trials confirm efficacy.",
            evidenceSummaryJa: "傷の治癒を促進。複数の臨床試験で効果が確認されています。",
            isPremium: false
        ),
        LightProtocol(
            id: "back",
            name: "Back & Spine",
            nameJa: "背中・脊椎",
            bodyPart: .back,
            wavelength: "810–850nm (near-IR)",
            distance: "6–12 inches",
            duration: 1200,     // 20 minutes
            frequency: "Daily",
            evidenceSummary: "Near-IR penetrates deeper tissue. Clinical evidence for pain reduction.",
            evidenceSummaryJa: "近赤外線が深部組織に到達。疼痛軽減の臨床的証拠があります。",
            isPremium: true
        ),
        LightProtocol(
            id: "fullBody",
            name: "Full Body",
            nameJa: "全身",
            bodyPart: .fullBody,
            wavelength: "630–850nm (combo)",
            distance: "12–24 inches",
            duration: 1200,     // 20 minutes
            frequency: "3–5x per week",
            evidenceSummary: "Systemic benefits: energy, sleep, inflammation. Requires full-panel device.",
            evidenceSummaryJa: "全身効果：エネルギー・睡眠・炎症改善。フルパネルデバイス必要。",
            isPremium: true
        )
    ]

    static var free: [LightProtocol] { all.filter { !$0.isPremium } }
    static var premium: [LightProtocol] { all }
}
```

### SessionService.swift — Protocol + DI

```swift
// Services/SessionService.swift
protocol SessionServiceProtocol {
    func save(session: Session)
    func fetchAll() -> [Session]
    func fetchLimited(days: Int) -> [Session]
    func currentStreak() -> Int
    func totalDuration() -> Int
}

class SessionService: SessionServiceProtocol {
    private let defaults = UserDefaults.standard
    private let key = "lr_sessions"

    func save(session: Session) {
        var sessions = fetchAllRaw()
        sessions.append(session)
        let data = try? JSONEncoder().encode(sessions)
        defaults.set(data, forKey: key)
    }

    func fetchAll() -> [Session] { fetchAllRaw() }

    func fetchLimited(days: Int) -> [Session] {
        let cutoff = Calendar.current.date(byAdding: .day, value: -days, to: Date()) ?? Date()
        return fetchAllRaw().filter { $0.date >= cutoff }
    }

    func currentStreak() -> Int {
        // 連続日数計算: 昨日以前からの連続セッション日数
        let sessions = fetchAllRaw()
        var streak = 0
        var checkDate = Calendar.current.startOfDay(for: Date())
        for _ in 0..<365 {
            let hasSession = sessions.contains {
                Calendar.current.isDate($0.date, inSameDayAs: checkDate)
            }
            if hasSession {
                streak += 1
                checkDate = Calendar.current.date(byAdding: .day, value: -1, to: checkDate)!
            } else {
                break
            }
        }
        return streak
    }

    func totalDuration() -> Int {
        fetchAllRaw().reduce(0) { $0 + $1.durationCompleted }
    }

    private func fetchAllRaw() -> [Session] {
        guard let data = defaults.data(forKey: key),
              let sessions = try? JSONDecoder().decode([Session].self, from: data)
        else { return [] }
        return sessions
    }
}
```

---

## 5. Phase 3: Monetization

🔴 **Rule 20: 自前 SwiftUI PaywallView 必須。`Purchases.shared.purchase(package:)` 使用。RC-UI-library 禁止。**

### RevenueCat SDK 初期化

```swift
// LumaRedApp.swift
import RevenueCat
// ❌ import RC-UI-library — 禁止

@main
struct LumaRedApp: App {
    init() {
        let apiKey = Bundle.main.infoDictionary?["RC_API_KEY"] as? String ?? ""
        Purchases.configure(withAPIKey: apiKey)
    }
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(SubscriptionService())
        }
    }
}
```

### SubscriptionService.swift

```swift
// Services/SubscriptionService.swift
import RevenueCat

protocol SubscriptionServiceProtocol: ObservableObject {
    var isPremium: Bool { get }
    func purchase(package: Package) async throws
    func restorePurchases() async throws
    func checkEntitlement() async
    func fetchOfferings() async -> Offerings?
}

class SubscriptionService: SubscriptionServiceProtocol {
    @Published var isPremium: Bool = false

    func checkEntitlement() async {
        do {
            let info = try await Purchases.shared.customerInfo()
            await MainActor.run {
                self.isPremium = info.entitlements["premium"]?.isActive == true
            }
        } catch {
            print("[SubscriptionService] checkEntitlement error: \(error)")
        }
    }

    func purchase(package: Package) async throws {
        let result = try await Purchases.shared.purchase(package: package)
        await MainActor.run {
            self.isPremium = result.customerInfo.entitlements["premium"]?.isActive == true
        }
    }

    func restorePurchases() async throws {
        let info = try await Purchases.shared.restorePurchases()
        await MainActor.run {
            self.isPremium = info.entitlements["premium"]?.isActive == true
        }
    }

    func fetchOfferings() async -> Offerings? {
        try? await Purchases.shared.offerings()
    }
}
```

### PaywallView.swift — 自前 SwiftUI

```swift
// Views/Onboarding/PaywallView.swift
// 🔴 RC-UI-library 禁止。自前実装のみ。
import SwiftUI
import RevenueCat

struct PaywallView: View {
    @EnvironmentObject var subscriptionService: SubscriptionService
    @Environment(\.dismiss) var dismiss
    @State private var offerings: Offerings?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // ヘッドライン
                Text("Start Your Glow Journey")
                    .font(.largeTitle.bold())
                    .accessibilityIdentifier("paywall_title")

                // ベネフィット一覧
                benefitsList

                // 価格グリッド
                if let offerings {
                    pricingGrid(offerings: offerings)
                }

                // Social Proof
                socialProof

                // FAQ
                faqSection

                // Maybe Later（ソフトペイウォール — Rule 20）
                Button("Maybe Later") {
                    dismiss()
                }
                .accessibilityIdentifier("paywall_maybe_later_button")
                .foregroundColor(.secondary)

                // Privacy + Terms
                privacyLinks
            }
            .padding()
        }
        .task {
            offerings = await subscriptionService.fetchOfferings()
        }
    }

    // ... (benefitsList, pricingGrid, socialProof, faqSection, privacyLinks)
}
```

### Product IDs

| Product | ID | Type | Price | Trial |
|---------|-----|------|-------|-------|
| Monthly | `lumaRed_monthly_499` | Auto-renewable | $4.99/月 | なし |
| Annual | `lumaRed_annual_2999` | Auto-renewable | $29.99/年 | 7日間 |
| Entitlement | `premium` | — | — | — |
| Offering | `default` | — | — | — |

---

## 6. Phase 4: Timer & Background

```swift
// ViewModels/TimerViewModel.swift
import BackgroundTasks

class TimerViewModel: ObservableObject {
    @Published var remainingSeconds: Int = 0
    @Published var isRunning: Bool = false
    private var backgroundTaskId: UIBackgroundTaskIdentifier = .invalid

    func start(protocol: LightProtocol) {
        remainingSeconds = protocol.duration
        isRunning = true
        // BGProcessingTaskRequest でバックグラウンド延長
        registerBackgroundTask()
        // Timer.scheduledTimer で毎秒更新
    }

    private func registerBackgroundTask() {
        backgroundTaskId = UIApplication.shared.beginBackgroundTask {
            UIApplication.shared.endBackgroundTask(self.backgroundTaskId)
        }
    }

    func complete(protocolId: String, durationCompleted: Int, bodyPart: BodyPart, sessionService: SessionServiceProtocol) {
        let session = Session(
            id: UUID(),
            date: Date(),
            protocolId: protocolId,
            durationCompleted: durationCompleted,  // 実際のセッション秒数を受け取る
            bodyPart: bodyPart                       // 実際のボディパーツを受け取る
        )
        sessionService.save(session: session)
        isRunning = false
    }
}
```

---

## 7. Phase 5: Polish

### Localization (.xcstrings)

```json
// Localizable.xcstrings (抜粋)
{
  "sourceLanguage": "en",
  "strings": {
    "tab.home": {
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "Protocols" } },
        "ja": { "stringUnit": { "state": "translated", "value": "プロトコル" } }
      }
    },
    "paywall.maybe_later": {
      "localizations": {
        "en": { "stringUnit": { "state": "translated", "value": "Maybe Later" } },
        "ja": { "stringUnit": { "state": "translated", "value": "あとで" } }
      }
    }
  }
}
```

### accessibilityIdentifier 一覧

| ID | Screen | Element |
|----|--------|---------|
| `home_protocol_list` | HomeView | プロトコル一覧 ScrollView |
| `protocol_card_face` | HomeView | 顔プロトコルカード |
| `protocol_card_joint` | HomeView | 関節プロトコルカード |
| `protocol_detail_start_button` | TimerView | タイマー開始ボタン（UX_SPEC §7 正本） |
| `timer_countdown_label` | TimerView | 残り時間表示（UX_SPEC §7 正本） |
| `paywall_title` | PaywallView | ペイウォールタイトル |
| `paywall_maybe_later_button` | PaywallView | Maybe Later ボタン（UX_SPEC §7 正本） |
| `paywall_subscribe_monthly` | PaywallView | 月額購入ボタン |
| `paywall_subscribe_annual` | PaywallView | 年額購入ボタン |
| `dashboard_streak_value` | DashboardView | 連続日数表示（UX_SPEC §7 正本） |
| `settings_upgrade_button` | SettingsView | アップグレードボタン（UX_SPEC §7 正本） |
| `settings_restore_button` | SettingsView | 購入復元ボタン（UX_SPEC §7 正本） |

---

## 8. Build & Run

| タスク | コマンド |
|--------|---------|
| ユニットテスト | `cd LumaRedios && fastlane test` |
| デバッグビルド | `cd LumaRedios && fastlane build` |
| アーカイブ + アップロード | `cd LumaRedios && fastlane release` |
| E2E テスト | `maestro test maestro/` |
| Greenlight チェック | `greenlight preflight LumaRedios/` |

### Fastlane lanes (最低限)

```ruby
# LumaRedios/fastlane/Fastfile
lane :test do
  run_tests(scheme: "LumaRed", devices: ["iPhone 16 Pro"])
end

lane :build do
  build_ios_app(scheme: "LumaRed", export_method: "development")
end

lane :release do
  build_ios_app(scheme: "LumaRed", export_method: "app-store")
  upload_to_app_store(skip_metadata: true, skip_screenshots: true)
end
```

### Greenlight checks (CRITICAL=0 必須)

```bash
greenlight preflight LumaRedios/
# 確認項目:
# - NSPrivacyAccessedAPITypes ✅
# - No tracking SDK (tracking-SDK, third-party-analytics, etc.) ✅
# - ITSAppUsesNonExemptEncryption = NO ✅
```
