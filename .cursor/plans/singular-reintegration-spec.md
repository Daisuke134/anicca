# Singular SDK 再統合 + RevenueCat→Singular→TikTok SAN パイプライン構築

**Version:** 1.8.2
**Date:** 2026-04-04
**Branch:** `feature/singular-reintegration` (dev から切る)
**Status:** SPEC REVIEW

---

## 開発環境

| 項目 | 値 |
|------|-----|
| ワークツリーパス | `../anicca-singular` |
| ブランチ | `feature/singular-reintegration` |
| ベース | `dev`（release/1.8.0 をマージ後） |
| 触るファイル | 下記「変更ファイル一覧」参照 |

---

## 背景・目的

TikTok 広告キャンペーン（JP: Install 最適化、EN: Purchase 最適化）を運用中だが、TikTok Business SDK の直接統合では Install / Purchase イベントが TikTok Ads Manager に反映されず、広告費が無駄になっている。

### TikTok SDK が動かなかった原因（確定済み）

| 原因 | 詳細 |
|------|------|
| automaticTracking 設定の矛盾 | `automaticTrackingEnabled = true` + `disablePaymentTracking()` でサーバー設定が override → 偽 Subscribe 大量発火 |
| IDFA ゼロ運用 | ATT なしで probabilistic matching の精度が極低 |
| Events Manager ↔ Ads Manager 分離 | Events Manager にデータがあっても Ads Manager のキャンペーンにマッピングされていなかった |

### 解決策

Singular を MMP（Mobile Measurement Partner）として再統合し、以下のデータフローを構築:

```
Install:  ユーザー起動 → Singular SDK（自動） → TikTok SAN → TikTok Ads Manager「Install」
Purchase: ユーザー購入 → RevenueCat（自動検知） → Singular API（S2S） → TikTok SAN → TikTok Ads Manager「Subscribe」
```

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│                    iOS App (Anicca)                  │
│                                                     │
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │  Singular SDK    │    │  RevenueCat SDK         │  │
│  │  (Install attr.) │    │  (Subscription管理)     │  │
│  │  SKAN 自動管理   │    │  collectDeviceIds()     │  │
│  └────────┬────────┘    └───────────┬────────────┘  │
│           │                         │                │
│  ┌────────────────────┐             │                │
│  │  Mixpanel + PostHog │             │                │
│  │  (自社Analytics)    │             │                │
│  └────────────────────┘             │                │
└───────────┬─────────────────────────┤                │
            │                         │                │
            ▼                         ▼                │
   ┌─────────────────┐    ┌─────────────────────────┐ │
   │  Singular Server  │◄──│  RevenueCat Server       │ │
   │  (Attribution)    │   │  (rc_initial_purchase等) │ │
   └────────┬──────────┘   └─────────────────────────┘ │
            │                                          │
            ▼                                          │
   ┌──────────────────────────────────────────────────┐│
   │  TikTok Ads (SAN Partner)                        ││
   │  Install = Singular 自動                          ││
   │  Subscribe = Revenue Postback (__REVENUE__→Subscribe) │
   └──────────────────────────────────────────────────┘│
```

---

## Singular SDK 設定

| 項目 | 値 |
|------|-----|
| SDK Key | `aniccaai_e8e6f239` |
| SDK Secret | `<REDACTED_SINGULAR_SECRET>` |
| ATT | なし（IDFV + SKAN 運用） |
| SKAN | SDK 12.0.6+ 自動有効 |
| Deep Links | 不要（現時点） |
| waitForTrackingAuthorization | 設定しない |

---

## Dashboard 設定（コード外、ダイスが実施済み）

### Singular Partner Config → TikTok Ads

| 設定 | 値 | 状態 |
|------|-----|------|
| App Site | Anicca (6755129214) | ✅ 設定済み |
| Revenue Events Postbacks | **Send all revenue events** | MUST 変更 |
| `__REVENUE__*` → Event | **Subscribe** | MUST 変更 |
| Send All | All Users | MUST |
| Include Revenue | ✅ | MUST |
| Events Postbacks | 既存のまま（LaunchAPP, Purchase, Subscribe） | 変更不要 |

### Singular Settings → Apps → Anicca

| 設定 | 値 | 状態 |
|------|-----|------|
| Reject IAP without Receipt | **OFF** | MUST 確認 |
| Bundle ID | ai.anicca.app.ios | ✅ |

### Singular SKAN Conversion Model

| 設定 | 値 | 状態 |
|------|-----|------|
| Model | SKAN 4 | ✅ 設定済み |
| Type | In App Purchase Revenue | ✅ |
| CV 0 | No Purchase | ✅ |
| CV 1 | $0-$10 (月額 $9.99) | ✅ |
| CV 2 | $10-$50 (年額 $49.99) | ✅ |
| CV 3 | $50-∞ | ✅ |

### RevenueCat → Singular Integration

| 設定 | 値 | 状態 |
|------|-----|------|
| SDK key | aniccaai_e8e6f239 | ✅ 設定済み |
| SDK key (sandbox) | 要確認 | MUST |
| Event names | デフォルト（rc_* プレフィックス） | ✅ |
| Sales Reporting | gross | ✅ |

### TikTok Ads Manager

| キャンペーン | 最適化イベント | 変更 |
|------------|-------------|------|
| JP (Install) | Install | 変更不要 |
| EN (Purchase) | Subscribe | 変更不要（Revenue Postback が Subscribe で送信されるため一致） |

### TikTok Events Manager

| 設定 | アクション |
|------|-----------|
| SKAdNetwork Configuration | **触らない**（Singular が SKAN 管理） |
| Data Connection | 変更不要 |

---

## 変更ファイル一覧

| # | ファイル | 変更内容 | 行数目安 |
|---|---------|---------|---------|
| 1 | `aniccaios/aniccaios/aniccaios-Bridging-Header.h` | `#import <Singular/Singular.h>` 追加 | +1行 |
| 2 | `aniccaios/aniccaios/Services/SingularManager.swift` | **新規作成** — SDK 初期化のみ | ~30行 |
| 3 | `aniccaios/aniccaios/AppDelegate.swift` | Singular 初期化追加 + TikTok SDK 削除 | ~-20/+5行 |
| 4 | `aniccaios/aniccaios/Services/SubscriptionManager.swift` | `collectDeviceIdentifiers()` 追加 + `import AdSupport` | +3行 |
| 5 | `aniccaios/aniccaios/Services/AnalyticsManager.swift` | TikTok イベント送信コード削除、`import TikTokBusinessSDK` 削除 | ~-30行 |
| 6 | `aniccaios/aniccaios.xcodeproj/project.pbxproj` | TikTok SPM 削除 + Singular SPM 追加（Xcode 手動操作） | Xcode |

---

## コードパッチ

### PATCH 1: Bridging Header

**File:** `aniccaios/aniccaios/aniccaios-Bridging-Header.h`

```diff
 #ifndef aniccaios_Bridging_Header_h
 #define aniccaios_Bridging_Header_h

-// v1.6.1: ATT/Singular削除 - Bridging Header は空になりました
-// 今後他のObjective-Cライブラリを使用する場合はここにインポートを追加
+// v1.8.2: Singular SDK 再統合（ATT なし、IDFV + SKAN 運用）
+#import <Singular/Singular.h>

 #endif /* aniccaios_Bridging_Header_h */
```

### PATCH 2: SingularManager.swift（新規）

**File:** `aniccaios/aniccaios/Services/SingularManager.swift`

```swift
import Foundation
import UIKit
import OSLog

@MainActor
final class SingularManager {
    static let shared = SingularManager()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "Singular")
    private var isConfigured = false

    private init() {}

    func configure(launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) {
        guard !isConfigured else { return }

        guard let config = SingularConfig(
            apiKey: "aniccaai_e8e6f239",
            andSecret: "<REDACTED_SINGULAR_SECRET>"
        ) else {
            logger.error("Singular config creation failed")
            return
        }

        // ATT なし: waitForTrackingAuthorization は設定しない
        // SKAN は SDK 12.0.6+ で自動有効（Singular Dashboard で Managed Mode）
        config.launchOptions = launchOptions

        Singular.start(config)
        isConfigured = true
        logger.info("Singular SDK initialized (IDFV + SKAN, no ATT)")
    }
}
```

### PATCH 3: AppDelegate.swift

**File:** `aniccaios/aniccaios/AppDelegate.swift`

```diff
-// v1.6.1 — ATT/Singular削除
-// v1.8.0 — TikTok Business SDK追加（ATTなし、IDFAゼロ運用）
+// v1.8.2 — Singular SDK 再統合 + RevenueCat→Singular→TikTok SAN

 func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
     SubscriptionManager.shared.configure()
     AnalyticsManager.configure()

     // PostHog setup（既存のまま）
     // ...

+    // Singular SDK（Install attribution + SKAN 管理）
+    SingularManager.shared.configure(launchOptions: launchOptions)

-    // TikTok Business SDK
-    if let ttConfig = TikTokConfig(
-        accessToken: "<REDACTED_DEAD_2026-05-21>",
-        appId: "6755129214",
-        tiktokAppId: "7593741049791217671"
-    ) {
-        ttConfig.automaticTrackingEnabled = true
-        ttConfig.setLogLevel(TikTokLogLevelSuppress)
-        ttConfig.disablePaymentTracking()
-        TikTokBusiness.initializeSdk(ttConfig)
-    }

     // Apple Search Ads attribution（既存のまま）
     // ...

     return true
 }
```

### PATCH 4: SubscriptionManager.swift

**File:** `aniccaios/aniccaios/Services/SubscriptionManager.swift`

```diff
 import Foundation
 import RevenueCat
+import AdSupport
 import OSLog

 func configure() {
     // ... 既存の Purchases.configure コード ...

     Purchases.shared.delegate = self

+    // RevenueCat → Singular 連携に必須
+    // $idfa（ATT なしの場合は all-zeros）と $idfv を RevenueCat に渡す
+    // これがないと RevenueCat → Singular にイベントが送信されない
+    Purchases.shared.attribution.collectDeviceIdentifiers()

     // 起動直後にSDKキャッシュのOfferingをAppStateへプリロード
     // ... 既存コード ...
 }
```

### PATCH 5: AnalyticsManager.swift

**File:** `aniccaios/aniccaios/Services/AnalyticsManager.swift`

```diff
 import Foundation
 import Mixpanel
 import PostHog
-import TikTokBusinessSDK
 import StoreKit
 import OSLog

 func trackPurchaseCompleted(productId: String, revenue: Double) {
     track(.purchaseCompleted, properties: [
         "product_id": productId,
         "revenue": revenue
     ])

     // Revenue tracking
     Mixpanel.mainInstance().people.trackCharge(amount: revenue)

-    // TikTok: Subscribe event for purchase optimization campaigns
-    let ttEvent = TikTokBaseEvent(eventName: "Subscribe")
-    ttEvent.addProperty(withKey: "currency", value: "USD")
-    ttEvent.addProperty(withKey: "value", value: String(format: "%.2f", revenue))
-    ttEvent.addProperty(withKey: "description", value: productId)
-    TikTokBusiness.trackTTEvent(ttEvent)
-    logger.debug("TikTok Subscribe event sent: \(productId) $\(revenue)")
+    // Purchase イベントは RevenueCat → Singular → TikTok SAN で自動送信
+    // アプリ側から手動送信は不要（二重カウント防止）

     updateSKANConversionValue(3)
 }

 func trackPaywallViewed() {
     track(.paywallPlanSelectionViewed)

-    // TikTok: ViewContent event
-    let ttEvent = TikTokBaseEvent(eventName: "ViewContent")
-    ttEvent.addProperty(withKey: "content_type", value: "paywall")
-    TikTokBusiness.trackTTEvent(ttEvent)
-    logger.debug("TikTok ViewContent event sent")

     updateSKANConversionValue(2)
 }

 func trackOnboardingCompleted() {
     track(.onboardingCompleted)

-    // TikTok: CompleteRegistration event
-    let ttEvent = TikTokBaseEvent(eventName: "CompleteRegistration")
-    TikTokBusiness.trackTTEvent(ttEvent)
-    logger.debug("TikTok CompleteRegistration event sent")

     updateSKANConversionValue(1)
 }
```

### PATCH 6: SPM 依存（Claude Code が xcodeproj gem で実行）

**ダイスの手動作業なし。** `xcodeproj` Ruby gem（CocoaPods/fastlane が使う公式ライブラリ）で pbxproj を安全に編集。

Source: https://github.com/CocoaPods/Xcodeproj

| 操作 | 対象 |
|------|------|
| **削除** | TikTokBusinessSDK（SPM） |
| **追加** | Singular-iOS-SDK v12.9.2（`https://github.com/singular-labs/Singular-iOS-SDK`） |

**Step 1: xcodeproj gem で pbxproj を編集**

```ruby
/opt/homebrew/opt/ruby/bin/ruby <<'RUBY'
require 'xcodeproj'
project = Xcodeproj::Project.open('aniccaios/aniccaios.xcodeproj')
target = project.targets.find { |t| t.name == 'aniccaios' }

# TikTokBusinessSDK 削除
tiktok_dep = target.package_product_dependencies.find { |d| d.product_name == 'TikTokBusinessSDK' }
tiktok_dep.remove_from_project if tiktok_dep
tiktok_ref = project.root_object.package_references.find { |r| r.repositoryURL.include?('tiktok-business-ios-sdk') }
tiktok_ref.remove_from_project if tiktok_ref

# Singular 追加
singular_ref = project.new(Xcodeproj::Project::Object::XCRemoteSwiftPackageReference)
singular_ref.repositoryURL = 'https://github.com/singular-labs/Singular-iOS-SDK'
singular_ref.requirement = { 'kind' => 'upToNextMajorVersion', 'minimumVersion' => '12.9.2' }
project.root_object.package_references << singular_ref

singular_dep = project.new(Xcodeproj::Project::Object::XCSwiftPackageProductDependency)
singular_dep.product_name = 'Singular'
singular_dep.package = singular_ref
target.package_product_dependencies << singular_dep

project.save
puts 'Done: TikTokBusinessSDK removed, Singular added.'
RUBY
```

**Step 2: Package.resolved 削除 + 依存解決**

```bash
rm -f aniccaios/aniccaios.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
cd aniccaios && xcodebuild -resolvePackageDependencies -project aniccaios.xcodeproj -scheme aniccaios
```

**安全策:**
- 実行前: `cp -r aniccaios.xcodeproj aniccaios.xcodeproj.bak`
- 失敗時: `git checkout -- aniccaios/aniccaios.xcodeproj` で即復元

追加時に Link Binary with Libraries で以下を確認:
- AdSupport.framework
- AdServices.framework（Optional マーク）
- StoreKit.framework（既にある）
- その他（SystemConfiguration, Security, Libz, Libsqlite3.0, WebKit）は Singular SDK が自動リンク

---

## テスト検証

### 検証フェーズ: TestFlight（App Store 提出前）

TestFlight で**パイプラインが動作すること**を100%確認してから App Store に出す。

| Step | 検証内容 | 方法 | 確認場所 |
|------|---------|------|---------|
| T1 | TestFlight ビルド配布 | fastlane | App Store Connect |
| T2 | デバイス IDFV を取得 | Xcode コンソール or Settings → General → About | メモ |
| T3 | Testing Console にデバイス登録 | Singular Dashboard → Developer Tools → Testing Console → IDFV 入力 | Singular |
| T4 | Install（session）確認 | アプリ起動 → Testing Console にリアルタイム表示 | Singular Testing Console |
| T5 | Purchase 確認 | sandbox 購入 → RevenueCat Dashboard で `$idfv` 属性が設定されていること確認 → Singular に `rc_initial_purchase_event` が届く | RevenueCat + Singular |

### 検証フェーズ: App Store 提出後

| Step | 検証内容 | 方法 |
|------|---------|------|
| P1 | TikTok Events Manager で「Subscribe」イベント表示 | Events Manager → Overview |
| P2 | TikTok Ads Manager でコンバージョン列に数値表示 | Ads Manager → キャンペーン一覧 |
| P3 | 反映待ち | App Store 配布後 24-48 時間 |

### なぜ App Store 提出が必要か

| 理由 | 詳細 |
|------|------|
| 現ビルド（1.8.1）に Singular SDK がない | TikTok SDK のまま。MMP 経由の attribution が発生しない |
| `collectDeviceIdentifiers()` がない | RevenueCat → Singular にイベントが一切送信されない |
| TikTok SAN attribution | 実広告クリック → App Store DL → Singular attribution → TikTok Ads Manager。この流れは App Store ビルドでのみ発生 |

**TestFlight でパイプライン検証 → OK → App Store 提出 → 実広告ユーザーでコンバージョン確認**

---

## ブランチフロー

```
1. release/1.8.0 を dev にマージ（TikTok SDK 等の変更を dev に戻す）
2. dev から worktree 作成: ../anicca-singular (feature/singular-reintegration)
3. worktree で PATCH 1-6 全て実装（Claude Code が SPM 操作含めて全実行）
4. feature/singular-reintegration → dev マージ
5. dev → main マージ（ダイス確認後）
6. main から release/1.8.2 ブランチ作成
7. fastlane ビルド → TestFlight
8. TestFlight テスト（T1-T5）→ 全パス確認
9. App Store 提出
```

**ダイスの手動作業:** Dashboard 設定（D1-D3）のみ。コード/ビルド/提出は全て Claude Code が実行。

---

## E2E 判定

| 項目 | 判定 |
|------|------|
| E2E テスト必要か | ⚠️ 部分的に必要 |
| Maestro E2E | 不要（UI 変更なし） |
| 手動テスト | MUST — Singular Testing Console + 実購入でデータフロー確認 |
| 自動テスト | 不要（外部 SDK 統合のため unit test の価値が低い） |

---

## リスク

| リスク | 対策 |
|--------|------|
| Singular SDK が App Store rejection を引き起こす | ATT なし + IDFA 使用宣言なし → v1.6.1 の rejection 原因を回避済み |
| RevenueCat → Singular のイベント遅延 | サーバー間通信のため数秒〜数分の遅延あり。リアルタイム性は不要 |
| TikTok Ads Manager にデータが表示されない | App Store 配布後 24-48 時間以内に確認。表示されなければ Singular Partner Config を再確認 |
| collectDeviceIdentifiers() の IDFA が all-zeros | ATT なし運用のため想定通り。IDFV + SKAN でカバー |
