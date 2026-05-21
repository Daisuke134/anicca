# Spec: ATT (App Tracking Transparency) 実装

**ステータス: 中止（非採用）**  
**理由:** `spec-remove-att-frontend.md` を正式採用し、ATT/Singular は削除方針に確定。

## 概要

App Store Guideline 5.1.2 リジェクト対応。ATTダイアログをオンボーディングに追加し、ユーザーの許可を得てからトラッキングを開始する。

## リジェクト内容

| 項目 | 詳細 |
|------|------|
| Guideline | 5.1.2 - Legal - Privacy - Data Use and Sharing |
| 問題 | App Store Connectで「トラッキング: Yes」と申告しているが、ATTプロンプトが表示されていない |
| デバイス | iPad Air 11-inch (M3) |
| バージョン | 1.6.0 |

## 現状分析

| 項目 | 現状 | 問題 |
|------|------|------|
| ATT Framework | リンク済み | コードで未使用 |
| ATTPermissionStepView | 削除済み | オンボーディングに存在しない |
| NSUserTrackingUsageDescription | 未設定 | Info.plistにない |
| Singular SDK | 即座に初期化 | ATT確認なしでトラッキング開始 |
| Mixpanel SDK | 即座に初期化 | ATT確認なしでトラッキング開始 |

## 修正方針

1. オンボーディングにATTステップを追加し、Apple公式のATTダイアログを表示
2. **Singular（アトリビューションSDK）はATT許可後のみ初期化**（Apple要件準拠）
3. **Mixpanel（ファーストパーティAnalytics）はATTステータスに関わらず初期化可能**（IDFAを使用しないため「トラッキング」に該当しない）

### SDK初期化ポリシー

| SDK | 役割 | ATT許可時 | ATT非許可時 |
|-----|------|-----------|-------------|
| **Singular** | アトリビューション（広告効果測定） | ✅ 初期化 | ❌ 初期化しない |
| **Mixpanel** | ファーストパーティAnalytics | ✅ 初期化 | ✅ 初期化（IDFAなし） |

**根拠**: Appleの定義では「トラッキング」はIDFAを使用した他社データとの紐付けを指す。MixpanelはIDFAを使わずにアプリ内イベントのみを記録するため、ATT許可なしでも使用可能。

### オンボーディングフロー変更

**Before:**
```
welcome → value → struggles → notifications → (paywall) → main
```

**After:**
```
welcome → value → struggles → notifications → att → (paywall) → main
```

## 変更ファイル一覧

| ファイル | 変更種別 | 内容 |
|----------|----------|------|
| `Info.plist` | 修正 | `NSUserTrackingUsageDescription` 追加 |
| `InfoPlist.strings`（全6言語） | 修正 | ローカライズ追加 |
| `OnboardingStep.swift` | 修正 | `.att` ケース追加、マイグレーション更新 |
| `OnboardingFlowView.swift` | 修正 | ATTステップのView追加、`advance()`更新 |
| `ATTPermissionStepView.swift` | 新規 | ATT許可リクエストView |
| `AppDelegate.swift` | 修正 | Singular初期化をATT許可後に遅延、storedLaunchOptions保持 |
| `AnalyticsManager.swift` | 修正 | 新規イベント（.onboardingATTCompleted）追加 |

**注**: SingularManager.swiftは変更不要（AppDelegateからの呼び出しタイミング変更のみ）。AnalyticsManager（Mixpanel）はATTステータスに関わらず初期化されるため、ATTチェックは不要。

## 詳細実装

### 1. Info.plist

```xml
<key>NSUserTrackingUsageDescription</key>
<string>We use this to measure how you discovered Anicca and improve your experience. Your data is never sold.</string>
```

### 2. InfoPlist.strings（全6言語）

**en.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "We use this to measure how you discovered Anicca and improve your experience. Your data is never sold.";
```

**ja.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "Aniccaを見つけた経緯を計測し、サービス改善に活用します。データが売却されることはありません。";
```

**de.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "Wir verwenden dies, um zu messen, wie Sie Anicca entdeckt haben, und um Ihr Erlebnis zu verbessern. Ihre Daten werden niemals verkauft.";
```

**es.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "Usamos esto para medir cómo descubriste Anicca y mejorar tu experiencia. Tus datos nunca se venden.";
```

**fr.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "Nous utilisons ceci pour mesurer comment vous avez découvert Anicca et améliorer votre expérience. Vos données ne sont jamais vendues.";
```

**pt-BR.lproj/InfoPlist.strings:**
```
"NSUserTrackingUsageDescription" = "Usamos isso para medir como você descobriu o Anicca e melhorar sua experiência. Seus dados nunca são vendidos.";
```

### 3. OnboardingStep.swift

```swift
import Foundation

enum OnboardingStep: Int {
    case welcome       // 0
    case value         // 1
    case struggles     // 2
    case notifications // 3
    case att           // 4 ← 追加
}

extension OnboardingStep {
    /// 旧RawValue（v0.2〜v0.5系）から現在の enum へマップする。
    static func migratedFromLegacyRawValue(_ rawValue: Int) -> OnboardingStep {
        if let step = OnboardingStep(rawValue: rawValue) {
            return step
        }

        // v0.5以前からのマイグレーション（旧ステップを現在のフローにマップ）
        // 旧v0.4: 0=welcome, 1=account, 2=value, 3=source, 4=name, 5=gender, 6=age,
        //         7=ideals, 8=struggles, 9=habitSetup, 10=notifications, 11=att, 12=alarmkit
        switch rawValue {
        case 0: return .welcome
        case 1, 2: return .value          // account, value → value
        case 3, 4, 5, 6, 7: return .struggles  // source〜ideals → struggles
        case 8: return .struggles
        case 9, 10: return .notifications // habitSetup, notifications → notifications
        case 11, 12: return .att          // att, alarmkit → att（ATT復活）
        default:
            return .welcome
        }
    }
}
```

### 4. ATTPermissionStepView.swift（新規作成）

```swift
import SwiftUI
import AppTrackingTransparency

struct ATTPermissionStepView: View {
    let next: () -> Void
    
    @State private var hasRequested = false
    
    var body: some View {
        VStack(spacing: AppTheme.Spacing.xl) {
            Spacer()
            
            // アイコン
            Image(systemName: "chart.bar.xaxis")
                .font(.system(size: 60))
                .foregroundColor(AppTheme.Colors.accent)
            
            // タイトル
            Text("Help Us Improve")
                .font(AppTheme.Typography.onboardingTitle)
                .foregroundColor(AppTheme.Colors.label)
            
            // 説明文（Pre-prompt）
            Text("We'd like to understand how you discovered Anicca to improve our service. This helps us reach more people who need support.")
                .font(AppTheme.Typography.bodyDynamic)
                .foregroundColor(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center)
                .padding(.horizontal, AppTheme.Spacing.xl)
            
            Spacer()
            
            // ボタン
            PrimaryButton(title: "Continue") {
                requestATT()
            }
            .accessibilityIdentifier("att_continue_button")
            .padding(.horizontal, AppTheme.Spacing.lg)
            .padding(.bottom, AppTheme.Spacing.xxl)
        }
        .background(AppTheme.Colors.background)
    }
    
    private func requestATT() {
        guard !hasRequested else {
            next()
            return
        }
        
        hasRequested = true
        
        // iOS 14.5+ のみATTリクエスト
        if #available(iOS 14.5, *) {
            ATTrackingManager.requestTrackingAuthorization { status in
                DispatchQueue.main.async {
                    // ATT完了後にトラッキングSDKを初期化
                    initializeTrackingSDKsIfAuthorized(status: status)
                    // 許可・拒否に関わらず次へ進む
                    next()
                }
            }
        } else {
            // iOS 14.5未満は即座に次へ（トラッキングSDKは既に初期化済み想定）
            next()
        }
    }
    
    private func initializeTrackingSDKsIfAuthorized(status: ATTrackingManager.AuthorizationStatus) {
        // ATT許可後のみトラッキングを有効化
        // 実際の初期化はAppDelegate/SingularManager/AnalyticsManagerで行う
        NotificationCenter.default.post(
            name: .attAuthorizationCompleted,
            object: nil,
            userInfo: ["status": status.rawValue]
        )
    }
}

extension Notification.Name {
    static let attAuthorizationCompleted = Notification.Name("attAuthorizationCompleted")
}

#Preview {
    ATTPermissionStepView {
        print("ATT completed")
    }
}
```

### 5. OnboardingFlowView.swift

```swift
import SwiftUI
import RevenueCat
import RevenueCatUI

struct OnboardingFlowView: View {
    @EnvironmentObject private var appState: AppState
    @State private var step: OnboardingStep = .welcome
    @State private var showPaywall = false

    var body: some View {
        ZStack {
            AppBackground()
            Group {
                switch step {
                case .welcome:
                    WelcomeStepView(next: advance)
                case .value:
                    ValueStepView(next: advance)
                case .struggles:
                    StrugglesStepView(next: advance)
                case .notifications:
                    NotificationPermissionStepView(next: advance)
                case .att:  // ← 追加
                    ATTPermissionStepView(next: advance)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .onAppear {
            step = appState.onboardingStep

            // Mixpanel: オンボーディング開始イベント
            if step == .welcome {
                AnalyticsManager.shared.track(.onboardingStarted)
            }

            // Prefetch Paywall offering
            Task {
                await SubscriptionManager.shared.refreshOfferings()
            }
        }
        .fullScreenCover(isPresented: $showPaywall) {
            // ... 既存のPaywall処理（変更なし）
        }
    }

    private func advance() {
        switch step {
        case .welcome:
            AnalyticsManager.shared.track(.onboardingWelcomeCompleted)
            step = .value
        case .value:
            AnalyticsManager.shared.track(.onboardingValueCompleted)
            step = .struggles
        case .struggles:
            AnalyticsManager.shared.track(.onboardingStrugglesCompleted)
            step = .notifications
        case .notifications:
            AnalyticsManager.shared.track(.onboardingNotificationsCompleted)
            step = .att  // ← 変更: ATTステップへ進む
        case .att:  // ← 追加
            AnalyticsManager.shared.track(.onboardingATTCompleted)
            completeOnboarding()
            return
        }
        appState.setOnboardingStep(step)
    }

    // ... 残りは既存のまま
}
```

### 6. AppDelegate.swift - SDK初期化の遅延

```swift
class AppDelegate: UIResponder, UIApplicationDelegate {
    
    // launchOptionsを保持（ATT後のSingular初期化に使用）
    private var storedLaunchOptions: [UIApplication.LaunchOptionsKey: Any]?
    
    func application(_ application: UIApplication, 
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // launchOptionsを保持（ATT後のSingular初期化に使用）
        storedLaunchOptions = launchOptions
        
        // Mixpanelは常に初期化（ファーストパーティAnalytics、IDFAを使用しない）
        AnalyticsManager.shared.configure()
        
        // ATT完了通知を購読
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(handleATTCompleted(_:)),
            name: .attAuthorizationCompleted,
            object: nil
        )
        
        // ATTステータスを確認し、既に許可済みならSingular初期化
        if #available(iOS 14.5, *) {
            let status = ATTrackingManager.trackingAuthorizationStatus
            if status == .authorized {
                initializeSingular()
            }
            // status == .notDetermined → オンボーディングで許可を取得してから初期化
            // status == .denied/.restricted → Singularは初期化しない
        } else {
            // iOS 14.5未満 → ATT不要、即座にSingular初期化
            initializeSingular()
        }
        
        // ... 残りの処理
        return true
    }

    @objc private func handleATTCompleted(_ notification: Notification) {
        guard let statusRaw = notification.userInfo?["status"] as? UInt32,
              let status = ATTrackingManager.AuthorizationStatus(rawValue: statusRaw) else {
            return
        }
        
        if status == .authorized {
            initializeSingular()
        }
        // ATT非許可時はSingularを初期化しない（Mixpanelは既に初期化済み）
    }
    
    private func initializeSingular() {
        // storedLaunchOptionsを使用してアトリビューション/ディープリンク情報を保持
        SingularManager.shared.configure(launchOptions: storedLaunchOptions)
        SingularManager.shared.trackAppLaunch()
    }
}
```

**ポイント:**
- `storedLaunchOptions`でlaunchOptionsを保持し、ATT許可後のSingular初期化に使用
- Mixpanelは常に初期化（ファーストパーティAnalytics）
- SingularはATT許可後のみ初期化（アトリビューションSDK）

### 7. AnalyticsManager.swift - 新規イベント追加

```swift
// AnalyticsEvent enumに追加
enum AnalyticsEvent: String {
    // ... 既存イベント
    case onboardingATTCompleted = "onboarding_att_completed"
}
```

## テスト計画

### 手動テスト

| テストケース | 条件 | 期待結果 |
|--------------|------|----------|
| 新規インストール → オンボーディング完了 | iOS 14.5+, status=notDetermined, "Allow Apps to Request to Track"=ON | ATTダイアログが表示される |
| ATT許可 → 次へ進む | 上記条件でユーザーが「許可」選択 | Mixpanel初期化済み + Singular初期化される |
| ATT拒否 → 次へ進む | 上記条件でユーザーが「拒否」選択 | Mixpanel初期化済み、Singularは初期化されない |
| "Allow Apps to Request to Track"=OFF | iOS 14.5+, 端末設定でトラッキング許可OFF | ダイアログ表示されず、status=deniedで次へ進む |
| iOS 14.4以下 | iOS 14.4以下の端末 | ATTダイアログなしで次へ進む、両SDK初期化 |
| 既存ユーザー（オンボーディング完了済み） | 任意のiOSバージョン | ATTステップは表示されない |
| 旧バージョンからアップデート（rawValue=11） | マイグレーションテスト | .attステップにマップされる |
| ATT許可後のSingular初期化 | status=authorized | launchOptions情報が保持されアトリビューション可能 |
| 再インストール後 | iOS 14.5+, "Allow Apps to Request to Track"=ON | 再インストール時はstatus=notDeterminedに戻るためダイアログ表示される |
| 再インストール後（トラッキング拒否設定） | iOS 14.5+, "Allow Apps to Request to Track"=OFF | ダイアログ表示されず、status=deniedで次へ進む |

### Maestro E2Eテスト

既存の `01-onboarding.yaml` を更新し、ATTステップを追加：

```yaml
# ATTステップ
- assertVisible:
    id: "att_continue_button"
- tapOn:
    id: "att_continue_button"
# システムダイアログはMaestroで自動処理される
```

## App Store 再提出時の Review Notes

```
ATT Permission Request Location:
The app calls ATTrackingManager.requestTrackingAuthorization() during onboarding,
after the notification permission step.

Flow: Welcome → Value → Struggles → Notifications → ATT Permission → Paywall

ATT Dialog Display Conditions:
The native iOS ATT dialog is shown ONLY when ALL of the following conditions are met:
1. iOS 14.5 or later
2. ATTrackingManager.trackingAuthorizationStatus == .notDetermined
3. User has "Allow Apps to Request to Track" enabled in Settings > Privacy > Tracking

If any condition is not met, the dialog is not shown and the app proceeds normally:
- iOS 14.4 and earlier: ATT framework not applicable, SDKs initialize immediately.
- Status already determined (.authorized/.denied/.restricted): No dialog, use existing status.
- "Allow Apps to Request to Track" is OFF: Returns .denied without showing dialog.

SDK Initialization Policy:
- Singular (attribution SDK): 
  - Initialized only when trackingAuthorizationStatus == .authorized
  - If status is .denied/.restricted/.notDetermined, Singular is NOT initialized
  - On iOS 14.4 and earlier, Singular initializes immediately (ATT not applicable)
- Mixpanel (first-party analytics): 
  - Initialized regardless of ATT status on all iOS versions
  - Does NOT access IDFA or perform cross-app tracking
  - Used solely for in-app event analytics without tracking identifiers

The app does not block access if users deny tracking or if the dialog is not shown.

Note: Existing users who completed onboarding before this update will not see the ATT step,
as they have already completed the onboarding flow.
```

## リスク・注意事項

| リスク | 対策 |
|--------|------|
| 既存ユーザーがATTステップを見逃す | 既存ユーザーはオンボーディング完了済みなので影響なし |
| ATT拒否率が高い | アプリ機能に影響なし。広告効果測定精度のみ低下 |
| SDK初期化タイミング変更による不整合 | ATT完了通知で確実に初期化、ステータス確認ロジック追加 |

## 参考資料

- [Apple ATT Framework](https://developer.apple.com/documentation/apptrackingtransparency)
- [Guideline 5.1.2 FAQ](https://developer.apple.com/app-store/user-privacy-and-data-use/)
- [Singular ATT Best Practices](https://support.singular.net/hc/en-us/articles/360049916831)

## チェックリスト

- [ ] Info.plist に NSUserTrackingUsageDescription 追加
- [ ] InfoPlist.strings（全6言語）にローカライズ追加
- [ ] OnboardingStep.swift に .att ケース追加
- [ ] OnboardingStep.migratedFromLegacyRawValue 更新（11,12 → .att）
- [ ] ATTPermissionStepView.swift 新規作成
- [ ] ATTPermissionStepView に .accessibilityIdentifier("att_continue_button") 追加
- [ ] OnboardingFlowView.swift の body に .att ケース追加
- [ ] OnboardingFlowView.swift の advance() に .att ケース追加
- [ ] AnalyticsEvent に .onboardingATTCompleted 追加
- [ ] AppDelegate.swift に storedLaunchOptions プロパティ追加
- [ ] AppDelegate.swift で Mixpanel を常に初期化
- [ ] AppDelegate.swift で Singular を ATT許可後のみ初期化
- [ ] Notification.Name.attAuthorizationCompleted 追加
- [ ] Maestro E2Eテスト更新
- [ ] Review Notes 準備
