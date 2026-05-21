# Spec: Singular SDK + ATT 完全削除（プライバシーラベル変更対応）

**ステータス: 採用（ATT削除が正）**  
**補足:** `spec-att-implementation.md` は中止扱い。

## 概要

App Store Guideline 5.1.2 リジェクト対応。Singular SDKを完全に削除し、ATTフロントエンドも削除。App Store Connectのプライバシーラベルを「Tracking: No」に変更。

## 背景

- Singularは使っていない（トライアルが1回も発生していない）
- 現時点で詳細なCPA計測は不要
- SKAdNetworkでインストール計測は可能
- オンボーディング最適化が最優先、不要な画面は削除すべき
- 将来Singularが必要になったらSPMで再追加可能（5分）

## Apple Guideline 5.1.2 の要件

> "Tracking is linking data collected from your app with third-party data for advertising purposes, or sharing the collected data with a data broker."

### Mixpanel設定の検証（Tracking: No 根拠）

**現在のMixpanel初期化設定** (`AnalyticsManager.swift`):
```swift
Mixpanel.initialize(token: token, trackAutomaticEvents: false)
```

| 確認項目 | 状態 | 根拠 |
|----------|------|------|
| IDFA使用 | **No** | AdSupport.framework未リンク、`advertisingIdentifier`参照ゼロ、ATT関連API未使用 |
| 広告目的のデータ結合 | **No** | 広告SDKなし、広告配信なし |
| 広告測定目的 | **Yes（ASAのみ）** | ASA attribution（AdServices.framework）で自社広告効果測定。**Trackingには該当しない**（Apple公式API、他社データ結合なし） |
| 他社データとの結合 | **No** | ファーストパーティAnalyticsのみ |
| データブローカー共有 | **No** | Mixpanelにデータ販売契約なし |

**Mixpanel実装検証手順**:
1. **AdSupport/ATT参照なし確認**: プロジェクト全体で以下の検索結果が0件であること
   - `AdSupport`
   - `AppTrackingTransparency`
   - `ATTrackingManager`
   - `advertisingIdentifier`
   - `IDFA`
2. **Mixpanel SDK設定確認**: `trackAutomaticEvents: false` で自動イベントが無効
3. **送信イベント確認**: 広告関連プロパティ（`$ad_group`, `$campaign`, etc.）が含まれないこと

**Mixpanel公式ガイド**: Mixpanelは一般的にTrackingに該当しないが、実際の設定・利用方法次第で変わる。上記の通り本アプリではTrackingに該当する使用をしていない。

→ **Tracking: No が成立**

## 対応方針

### コード側

| 変更内容 | 詳細 |
|----------|------|
| Singular SDK完全削除 | SPMパッケージ、SingularManager.swift、全参照 |
| ATTフロントエンド削除 | ATTPermissionStepView、OnboardingStep.att |
| フレームワーク削除 | AdSupport.framework、AppTrackingTransparency.framework |
| Info.plist/xcconfig | NSUserTrackingUsageDescription、SINGULAR_SDK_KEY/SECRET削除 |

### App Store Connect側（手動）

#### 1. Tracking項目の変更

| 設定 | 変更 |
|------|------|
| ユーザID → トラッキング目的に使用 | **チェックを外す** |
| デバイスID → トラッキング目的に使用 | **チェックを外す** |

#### 2. Privacy Label全体の確認

Mixpanelで収集するデータを正確に申告:

| データ種別 | 収集 | 用途 | ユーザにリンク | Tracking |
|-----------|------|------|---------------|----------|
| User ID | Yes | Analytics | Yes | **No** |
| Device ID | Yes | Analytics | Yes | **No** |
| Product Interaction | Yes | Analytics | Yes | **No** |
| Other Usage Data | Yes | Analytics | Yes | **No** |

**確認手順**:
1. App Store Connect → アプリ → アプリのプライバシー
2. 「データタイプ」の「編集」をクリック
3. 上記の通りデータ収集項目を確認・更新
4. 「ユーザのトラッキングに使用されるデータ」から全て削除されていることを確認

#### 3. Privacy Manifest確認

**確認項目**:
- `PrivacyInfo.xcprivacy` にTracking関連の宣言がないこと
- 依存SDKのPrivacy ManifestがPrivacy Labelと一致していること
- Singular削除後、Tracking関連の宣言が残存しないこと

#### 4. SKAdNetwork確認

Info.plistに以下のSKAdNetwork IDが設定済み（TikTok広告用）:
- `22mmun2rn5.skadnetwork`
- `238da6jt44.skadnetwork`
- その他10件

SKAdNetworkはATT不要のプライバシー保護型attribution。Tracking: Noと矛盾しない。

#### 5. ASA Attribution確認

`ASAAttributionManager`はApple Search Ads attributionを取得（**AdServices.framework**）。

**現在の実装**:
- campaign_id, keyword_id, ad_group_id 等をMixpanelにuser propertyとして送信
- 用途: 自社広告キャンペーンの効果測定（どのキーワード/広告からユーザーが来たか）

**Tracking定義との関係**:
- **Trackingに該当しない**: Apple公式API経由、他社データ結合なし、データブローカー共有なし
- **AdServices.framework**: ATT不要のプライバシー保護型attribution API

**Privacy Label申告**:
- 現行: User ID / Device ID は「Analytics」用途で申告済み
- **追加必要**: ASA attribution データ（campaign_id, keyword_id, ad_group_id等）は広告効果測定に使用
- **データ型**: 「Advertising Data」（AppleのPrivacy Label分類に準拠）
- **用途**: 「Developer's Advertising or Marketing」

**App Store Connect設定（追加）**:
| データ種別 | 収集 | 用途 | ユーザにリンク | Tracking |
|-----------|------|------|---------------|----------|
| Advertising Data | Yes | **Developer's Advertising or Marketing** | Yes | **No** |

**補足**: AppleのPrivacy Label分類では、campaign/ad_group/keyword等の広告関連データは「Advertising Data」に分類される。「Other Usage Data」ではない点に注意。

**重要: Trackingには該当しない理由**:
- Apple Search Adsの効果測定はApple公式API（AdServices.framework）を使用
- ファーストパーティのマーケティング分析であり、他社データとの結合なし
- データブローカー共有なし
- IDFAアクセスなし（ATT不要）

---

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|----------|----------|------|
| `Services/SingularManager.swift` | **削除** | ファイルごと削除 |
| `Onboarding/ATTPermissionStepView.swift` | **削除** | ファイルごと削除 |
| `Onboarding/OnboardingStep.swift` | 修正 | `.att`ケース削除 |
| `Onboarding/OnboardingFlowView.swift` | 修正 | `.att`ケース削除 |
| `AppDelegate.swift` | 修正 | ATT/Singular関連全削除 |
| `Config.swift` | 修正 | Singular設定削除 |
| `Services/SubscriptionManager.swift` | 修正 | `import Singular`とSingular呼び出し削除 |
| `Authentication/AuthCoordinator.swift` | 修正 | `SingularManager.shared.trackLogin()`削除 |
| `Services/AnalyticsManager.swift` | 修正 | `.onboardingATTCompleted`削除 |
| `aniccaios-Bridging-Header.h` | 修正 | Singular import削除 |
| `Info.plist` | 修正 | NSUserTrackingUsageDescription、SINGULAR_SDK_KEY/SECRET削除 |
| `Resources/*/InfoPlist.strings`（6言語） | 修正 | ATT説明文削除 |
| `Configs/Staging.xcconfig` | 修正 | Singular設定削除 |
| `Configs/Production.xcconfig` | 修正 | Singular設定削除 |
| `project.pbxproj` | 修正 | Singular SPM、AdSupport、AppTrackingTransparency削除 |

---

## 詳細パッチ

### 1. SingularManager.swift - 削除

```
aniccaios/aniccaios/Services/SingularManager.swift → 削除
```

### 2. ATTPermissionStepView.swift - 削除

```
aniccaios/aniccaios/Onboarding/ATTPermissionStepView.swift → 削除
```

### 3. OnboardingStep.swift

**変更前:**
```swift
enum OnboardingStep: Int {
    case welcome       // 0
    case value         // 1
    case struggles     // 2
    case notifications // 3
    case att           // 4
}

// マイグレーション
case 11, 12: return .att          // att, alarmkit → att
```

**変更後:**
```swift
enum OnboardingStep: Int {
    case welcome       // 0
    case value         // 1
    case struggles     // 2
    case notifications // 3
}

// マイグレーション
// rawValue 4, 11, 12 は削除された.attなので、.notificationsに戻す
// ※ OnboardingFlowView.onAppear で通知許可が既に決定済みの場合はスキップする（下記参照）
case 4: return .notifications     // 削除された.att → notifications
case 11, 12: return .notifications // att, alarmkit → notifications
```

**重要**: rawValue 4/11/12（ATTステップにいたユーザー）は .notifications にマップされるが、OnboardingFlowView の onAppear で通知許可が既に決定済み（authorized/denied）の場合は即座に `completeOnboarding()` を呼んでオンボーディングを完了させる。

### 4. OnboardingFlowView.swift

**変更前:**
```swift
case .notifications:
    NotificationPermissionStepView(next: advance)
case .att:
    ATTPermissionStepView(next: advance)

// advance()
case .notifications:
    AnalyticsManager.shared.track(.onboardingNotificationsCompleted)
    step = .att
case .att:
    AnalyticsManager.shared.track(.onboardingATTCompleted)
    completeOnboarding()
    return
```

**変更後:**
```swift
// body
case .notifications:
    NotificationPermissionStepView(next: advance)
// case .att 削除

// onAppear（マイグレーション対応追加）
.onAppear {
    step = appState.onboardingStep

    // ATTステップから移行したユーザー: 通知許可が既に決定済みなら即完了
    // .authorized, .denied, .provisional, .ephemeral は全て「決定済み」扱い
    // .notDetermined のみ通知画面を表示
    if step == .notifications {
        Task {
            let settings = await UNUserNotificationCenter.current().notificationSettings()
            if settings.authorizationStatus != .notDetermined {
                await MainActor.run {
                    completeOnboarding()
                }
                return
            }
        }
    }

    // Mixpanel: オンボーディング開始イベント
    if step == .welcome {
        AnalyticsManager.shared.track(.onboardingStarted)
    }

    // Prefetch Paywall offering
    Task {
        await SubscriptionManager.shared.refreshOfferings()
    }
}

// advance()
case .notifications:
    AnalyticsManager.shared.track(.onboardingNotificationsCompleted)
    completeOnboarding()
    return
// case .att 削除
```

**paywall表示の流れ**: `completeOnboarding()` 内で `showPaywall = true` が設定され、fullScreenCover でPaywallが表示される。未課金ユーザーはPaywall完了後に `markOnboardingComplete()` が呼ばれてメイン画面へ遷移する。

### 5. AppDelegate.swift

**変更前:**
```swift
import AppTrackingTransparency

class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    private var storedLaunchOptions: [UIApplication.LaunchOptionsKey: Any]?
    private var singularInitialized = false

    func application(...) -> Bool {
        // ...
        storedLaunchOptions = launchOptions
        // ...
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleATTCompleted(_:)),
            name: .attAuthorizationCompleted,
            object: nil
        )
        
        if #available(iOS 14.5, *) {
            let status = ATTrackingManager.trackingAuthorizationStatus
            if status == .authorized {
                initializeSingular()
            }
        } else {
            initializeSingular()
        }
        // ...
    }
    
    @objc private func handleATTCompleted(_ notification: Notification) { ... }
    private func initializeSingular() { ... }
}
```

**変更後:**
```swift
// import AppTrackingTransparency 削除

class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    // storedLaunchOptions 削除
    // singularInitialized 削除

    func application(_ application: UIApplication, 
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let proxy = Bundle.main.object(forInfoDictionaryKey: "ANICCA_PROXY_BASE_URL") as? String ?? "nil"
        print("ANICCA_PROXY_BASE_URL =", proxy)

        let resetFlag = (Bundle.main.object(forInfoDictionaryKey: "RESET_ON_LAUNCH") as? NSString)?.boolValue == true
        let shouldReset = resetFlag || ProcessInfo.processInfo.arguments.contains("-resetOnLaunch")
        if shouldReset {
            UserDefaults.standard.removePersistentDomain(forName: Bundle.main.bundleIdentifier ?? "")
            UserDefaults.standard.synchronize()
            AppState.shared.resetState()
        }

        // storedLaunchOptions = launchOptions 削除

        UNUserNotificationCenter.current().delegate = self
        NotificationScheduler.shared.registerCategories()
        SubscriptionManager.shared.configure()
        AnalyticsManager.shared.configure()
        
        // ATT NotificationCenter.default.addObserver 削除
        // ATTステータスチェック・Singular初期化ロジック 全削除

        Task {
            await ASAAttributionManager.shared.fetchAttributionIfNeeded()
            AnalyticsManager.shared.track(.appOpened)
        }

        Task {
            if AppState.shared.isOnboardingComplete {
                _ = await NotificationScheduler.shared.requestAuthorizationIfNeeded()
            }
            await SubscriptionManager.shared.refreshOfferings()
            await AuthHealthCheck.shared.warmBackend()
        }
        return true
    }
    
    // handleATTCompleted 削除
    // initializeSingular 削除
    
    // 残りのメソッドはそのまま維持
}
```

### 6. Config.swift

**変更前:**
```swift
private static let singularSDKKeyKey = "SINGULAR_SDK_KEY"
private static let singularSDKSecretKey = "SINGULAR_SDK_SECRET"
// ...
static var singularSDKKey: String { infoValue(for: singularSDKKeyKey) }
static var singularSDKSecret: String { infoValue(for: singularSDKSecretKey) }
```

**変更後:**
```swift
// singularSDKKeyKey 削除
// singularSDKSecretKey 削除
// ...
// singularSDKKey 削除
// singularSDKSecret 削除
```

### 7. SubscriptionManager.swift

**変更前:**
```swift
import Singular
// ...
// 2. Singularへ購入イベント送信（新規購入の場合のみ）
if subscription.plan == .pro,
   let productId = subscription.productIdentifier {
    // ...
    SingularManager.shared.trackPurchase(productId: productId, price: price, currency: currency)
    AnalyticsManager.shared.trackPurchaseCompleted(productId: productId, revenue: price)
}
```

**変更後:**
```swift
// import Singular 削除
// ...
// Singularコード削除、Mixpanelのみ残す
if subscription.plan == .pro,
   let productId = subscription.productIdentifier {
    let price: Double
    let currency: String
    if let offering = AppState.shared.cachedOffering,
       let package = offering.availablePackages.first(where: { $0.storeProduct.productIdentifier == productId }) {
        price = package.storeProduct.price as? Double ?? 9.99
        currency = package.storeProduct.currencyCode ?? "USD"
    } else {
        price = 9.99
        currency = "USD"
    }
    // SingularManager.shared.trackPurchase 削除
    AnalyticsManager.shared.trackPurchaseCompleted(productId: productId, revenue: price)
}
```

### 8. AuthCoordinator.swift

**変更前:**
```swift
SingularManager.shared.trackLogin()
```

**変更後:**
```swift
// SingularManager.shared.trackLogin() 削除
```

### 9. AnalyticsManager.swift

**変更前:**
```swift
case onboardingATTCompleted = "onboarding_att_completed"
```

**変更後:**
```swift
// case onboardingATTCompleted 削除
```

### 10. aniccaios-Bridging-Header.h

**変更前:**
```objc
#ifndef aniccaios_Bridging_Header_h
#define aniccaios_Bridging_Header_h

#import <Singular/Singular.h>

#endif
```

**変更後:**
```objc
#ifndef aniccaios_Bridging_Header_h
#define aniccaios_Bridging_Header_h

// Singular削除 - 空のBridging Header

#endif
```

### 11. Info.plist

**削除するキー:**
```xml
<key>SINGULAR_SDK_KEY</key>
<string>$(INFOPLIST_KEY_SINGULAR_SDK_KEY)</string>
<key>SINGULAR_SDK_SECRET</key>
<string>$(INFOPLIST_KEY_SINGULAR_SDK_SECRET)</string>
<!-- ... -->
<key>NSUserTrackingUsageDescription</key>
<string>We use this to measure how you discovered Anicca and improve your experience. Your data is never sold.</string>
```

### 12. InfoPlist.strings（6言語）

**削除する行:**
```
/* App Tracking Transparency permission description */
"NSUserTrackingUsageDescription" = "...";
```

対象ファイル:
- `Resources/en.lproj/InfoPlist.strings`
- `Resources/ja.lproj/InfoPlist.strings`
- `Resources/de.lproj/InfoPlist.strings`
- `Resources/es.lproj/InfoPlist.strings`
- `Resources/fr.lproj/InfoPlist.strings`
- `Resources/pt-BR.lproj/InfoPlist.strings`

### 13. Staging.xcconfig

**削除する行:**
```
// Singular MMP
SINGULAR_SDK_KEY = aniccaai_e8e6f239
SINGULAR_SDK_SECRET = <REDACTED_SINGULAR_SECRET>
INFOPLIST_KEY_SINGULAR_SDK_KEY = $(SINGULAR_SDK_KEY)
INFOPLIST_KEY_SINGULAR_SDK_SECRET = $(SINGULAR_SDK_SECRET)
```

### 14. Production.xcconfig

**削除する行:**
```
// Singular MMP
SINGULAR_SDK_KEY = aniccaai_e8e6f239
SINGULAR_SDK_SECRET = <REDACTED_SINGULAR_SECRET>
INFOPLIST_KEY_SINGULAR_SDK_KEY = $(SINGULAR_SDK_KEY)
INFOPLIST_KEY_SINGULAR_SDK_SECRET = $(SINGULAR_SDK_SECRET)
```

### 15. project.pbxproj（Xcode操作）

**削除対象:**
1. **Package Dependencies**: Singular SPMパッケージ
2. **Frameworks**: 
   - `Singular in Frameworks`
   - `AdSupport.framework in Frameworks`
   - `AppTrackingTransparency.framework in Frameworks`

**手順:**
1. Xcode → Project → Package Dependencies → Singular削除
2. Xcode → aniccaios target → Build Phases → Link Binary With Libraries:
   - AdSupport.framework 削除
   - AppTrackingTransparency.framework 削除

### 16. Package.resolved（自動更新）

SPM削除後、以下のエントリが自動的に削除される:
```json
{
  "identity" : "singular-ios-sdk",
  "kind" : "remoteSourceControl",
  "location" : "https://github.com/singular-labs/Singular-iOS-SDK",
  "state" : {
    "revision" : "f8b2d5ba562ad23795ac597d24482ef55fecc762",
    "version" : "12.10.0"
  }
}
```

**確認手順:**
1. Xcode: File → Packages → Reset Package Caches
2. `Package.resolved`に`singular-ios-sdk`が含まれていないことを確認
3. `DerivedData`をクリーン: `rm -rf ~/Library/Developer/Xcode/DerivedData`

### 17. Singular Links設定（確認済み: 未使用）

**確認結果:**
- Associated Domains: Singular関連の設定なし
- URL Types: `anicca://`スキームのみ（Singular Linksではない）
- Singular Linksは使用していない → **削除不要**

---

## オンボーディングフロー（変更後）

```
welcome → value → struggles → notifications → paywall → main
```

4ステップ + Paywall

---

## App Reviewへの返信文

```
Thank you for your feedback regarding Guideline 5.1.2.

We have reviewed our data collection practices and removed all tracking functionality:

1. Removed Singular SDK (attribution/tracking) from the app binary
2. Removed App Tracking Transparency framework
3. Removed AdSupport framework
4. Updated App Privacy Information in App Store Connect:
   - User ID: Tracking → No
   - Device ID: Tracking → No

Our app now uses ONLY:
- Mixpanel for first-party analytics (no IDFA access, no cross-app tracking)
- SKAdNetwork for aggregate attribution (no user consent required)
- AdServices.framework for Apple Search Ads attribution (first-party, ATT not required)

Regarding AdServices.framework:
- We use Apple's official AdServices API to measure our own Apple Search Ads campaign performance
- This is NOT "Tracking" as defined by Apple (no linking with third-party data, no data broker sharing)
- We have updated our Privacy Label to include "Developer's Advertising or Marketing" purpose for this data

We do NOT:
- Link user data with third-party data for advertising
- Share collected data with data brokers
- Access IDFA or any device advertising identifier

Please proceed with the current submission, or let us know if you need
us to resubmit with these changes.

Thank you.
```

---

## テスト計画

| テストケース | 期待結果 |
|--------------|----------|
| 新規インストール → オンボーディング完了 | ATTダイアログなし、4ステップで完了 |
| .notifications完了後 | 直接paywallへ遷移 |
| Mixpanel初期化 | 正常に動作 |
| Singular関連コード | コンパイルエラーなし（削除済み） |
| ビルド | 成功（AdSupport/ATT不要） |
| **既存ユーザー: rawValue 4（ATT中断）** | .notificationsにマイグレーション、オンボーディング完了 |
| **既存ユーザー: rawValue 11, 12** | .notificationsにマイグレーション、オンボーディング完了 |
| **既存ユーザー: 通知許可 authorized** | 通知画面スキップ、即座にpaywall表示 |
| **既存ユーザー: 通知許可 denied** | 通知画面スキップ、即座にpaywall表示 |
| **既存ユーザー: 通知許可 provisional** | 通知画面スキップ、即座にpaywall表示（許可済み扱い） |
| **既存ユーザー: 通知許可 ephemeral** | 通知画面スキップ、即座にpaywall表示（許可済み扱い） |
| **既存ユーザー: 通知許可 notDetermined** | 通知画面表示、許可/拒否後にpaywall表示 |
| **ASA attribution: 広告流入ユーザー** | campaign_id/keyword_id がMixpanelに送信される |
| **ASA attribution: Organicユーザー** | asa_attribution=false がMixpanelに設定される |
| **App Store Connect: Privacy Label更新** | Advertising Data + Developer's Advertising or Marketing が設定されている |

---

## チェックリスト

### コード変更
- [ ] SingularManager.swift 削除
- [ ] ATTPermissionStepView.swift 削除
- [ ] OnboardingStep.swift から .att 削除
- [ ] OnboardingFlowView.swift から .att 関連削除
- [ ] AppDelegate.swift から ATT/Singular関連全削除
- [ ] Config.swift からSingular設定削除
- [ ] SubscriptionManager.swift からSingular参照削除
- [ ] AuthCoordinator.swift からSingular参照削除
- [ ] AnalyticsManager.swift から .onboardingATTCompleted 削除
- [ ] aniccaios-Bridging-Header.h からSingular import削除
- [ ] Info.plist から NSUserTrackingUsageDescription、SINGULAR_SDK_KEY/SECRET削除
- [ ] InfoPlist.strings（6言語）から ATT説明文削除
- [ ] Staging.xcconfig からSingular設定削除
- [ ] Production.xcconfig からSingular設定削除
- [ ] Xcode: Singular SPMパッケージ削除
- [ ] Xcode: AdSupport.framework削除
- [ ] Xcode: AppTrackingTransparency.framework削除
- [ ] Package.resolved: singular-ios-sdkが削除されていることを確認
- [ ] DerivedDataクリーン

### App Store Connect（手動）
- [ ] ユーザID → トラッキング目的に使用 → チェックを外す
- [ ] デバイスID → トラッキング目的に使用 → チェックを外す
- [ ] Privacy Label全体を確認（Analytics用途を正確に申告）
- [ ] App Reviewに返信

### 残存参照チェック（必須）
プロジェクト全体（**メインアプリ + AniccaNotificationService拡張**）で以下の検索結果が**0件**であること:
- [ ] `ATTrackingManager`
- [ ] `AppTrackingTransparency`
- [ ] `AdSupport`
- [ ] `Singular`（import, class, method, コメント以外）
- [ ] `NSUserTrackingUsageDescription`
- [ ] `attAuthorizationCompleted`

### 拡張ターゲット確認
- [ ] `AniccaNotificationService/Info.plist` にATT/AdSupport関連設定がないこと
- [ ] `AniccaNotificationService` のBuild PhasesにATT/AdSupportフレームワークがないこと

### 確認
- [ ] ビルド成功
- [ ] オンボーディングフロー確認（4ステップ）
- [ ] Package.resolvedにSingular残存なし
- [ ] Privacy Manifest確認
- [ ] devにpush
