# Mixpanel ASA連携 仕様書

**作成日**: 2025-01-14
**最終更新**: 2025-01-14
**目的**: Jake Mor #51「どのキーワードが課金ユーザーを連れてくるか追跡」
**ステータス**: ✅ 実装完了

---

## 概要

Apple Search Ads (ASA) からのインストールを追跡し、どのキーワード経由のユーザーが課金するかをMixpanelで分析可能にする。

---

## As Is（実装前）

### iOSアプリ (`aniccaios/`)

| 項目 | 状態 |
|------|------|
| Mixpanel SDK | ✅ 導入済み (`AnalyticsManager.swift`) |
| AdServices Framework | ❌ 未導入 |
| ASA Attribution取得 | ❌ 未実装 |
| キーワード追跡 | ❌ 未実装 |

---

## To Be（実装後）✅ 完了

### iOSアプリ (`aniccaios/`)

| 項目 | 状態 |
|------|------|
| Mixpanel SDK | ✅ 導入済み |
| AdServices Framework | ✅ 追加済み |
| ASA Attribution取得 | ✅ アプリ初回起動時に取得 |
| キーワード追跡 | ✅ Mixpanelユーザープロパティに設定 |

### 追跡するデータ

Mixpanelユーザープロパティとして以下を設定：

| プロパティ名 | 値 | 説明 |
|-------------|-----|------|
| `asa_attribution` | `true`/`false` | ASA経由かどうか |
| `asa_campaign_id` | `542370539` | キャンペーンID |
| `asa_ad_group_id` | `542317095` | 広告グループID |
| `asa_keyword_id` | `87675432` | キーワードID（重要！） |
| `asa_country` | `US` | 国/地域 |
| `asa_conversion_type` | `Download` | コンバージョンタイプ |
| `asa_claim_type` | `Click`/`Impression` | クリック or 表示 |
| `asa_ad_id` | `12345678` | 広告ID |

---

## 実装ファイル

### 1. 新規ファイル: `ASAAttributionManager.swift` ✅

**パス**: `aniccaios/aniccaios/Services/ASAAttributionManager.swift`

```swift
import Foundation
import AdServices
import Mixpanel
import OSLog

/// Apple Search Ads Attribution Manager
/// Jake Mor #51: "Send keyword attribution to Mixpanel"
@MainActor
final class ASAAttributionManager {
    static let shared = ASAAttributionManager()
    private let logger = Logger(subsystem: "com.anicca.ios", category: "ASAAttribution")

    private let hasCheckedKey = "asa_attribution_checked"

    private init() {}

    /// 初回起動時にASAアトリビューションを取得してMixpanelに送信
    func fetchAttributionIfNeeded() async {
        guard !UserDefaults.standard.bool(forKey: hasCheckedKey) else {
            logger.debug("ASA attribution already checked, skipping")
            return
        }

        UserDefaults.standard.set(true, forKey: hasCheckedKey)

        do {
            let token = try AAAttribution.attributionToken()
            logger.info("ASA attribution token obtained")

            let attribution = try await fetchAttributionData(token: token)
            setMixpanelProperties(attribution: attribution)

        } catch {
            logger.debug("ASA attribution not available: \(error.localizedDescription)")
            AnalyticsManager.shared.setUserProperty("asa_attribution", value: false)
        }
    }

    private func fetchAttributionData(token: String) async throws -> ASAAttributionData {
        guard let url = URL(string: "https://api-adservices.apple.com/api/v1/") else {
            throw ASAError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("text/plain", forHTTPHeaderField: "Content-Type")
        request.httpBody = token.data(using: .utf8)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ASAError.invalidResponse
        }

        return try JSONDecoder().decode(ASAAttributionData.self, from: data)
    }

    private func setMixpanelProperties(attribution: ASAAttributionData) {
        var properties: [String: MixpanelType] = [
            "asa_attribution": attribution.attribution
        ]

        if let campaignId = attribution.campaignId {
            properties["asa_campaign_id"] = campaignId
        }
        if let adGroupId = attribution.adGroupId {
            properties["asa_ad_group_id"] = adGroupId
        }
        if let keywordId = attribution.keywordId {
            properties["asa_keyword_id"] = keywordId
        }
        if let countryOrRegion = attribution.countryOrRegion {
            properties["asa_country"] = countryOrRegion
        }
        if let conversionType = attribution.conversionType {
            properties["asa_conversion_type"] = conversionType
        }
        if let claimType = attribution.claimType {
            properties["asa_claim_type"] = claimType
        }
        if let adId = attribution.adId {
            properties["asa_ad_id"] = adId
        }

        AnalyticsManager.shared.setUserProperties(properties)
        logger.info("ASA attribution properties set in Mixpanel")
    }
}

struct ASAAttributionData: Codable {
    let attribution: Bool
    let orgId: Int?
    let campaignId: Int?
    let conversionType: String?
    let clickDate: String?
    let impressionDate: String?
    let claimType: String?
    let adGroupId: Int?
    let countryOrRegion: String?
    let keywordId: Int?
    let adId: Int?
}

enum ASAError: Error {
    case invalidURL
    case invalidResponse
    case decodingFailed
}
```

### 2. 変更ファイル: `AppDelegate.swift` ✅

**パス**: `aniccaios/aniccaios/AppDelegate.swift`

```diff
 SubscriptionManager.shared.configure()
 AnalyticsManager.shared.configure()
-AnalyticsManager.shared.track(.appOpened)
 SuperwallManager.shared.configure()
 SingularManager.shared.configure(launchOptions: launchOptions)
 SingularManager.shared.trackAppLaunch()
+
+// ASA Attribution取得 → app_opened トラック（この順序が重要）
+// Jake Mor #51: キーワード別の課金率を追跡するため、attributionを先に取得
+Task {
+    await ASAAttributionManager.shared.fetchAttributionIfNeeded()
+    AnalyticsManager.shared.track(.appOpened)
+}
```

### 3. Xcode設定 ✅

- ✅ `AdServices.framework` を追加済み（手動）

---

## Mixpanelでの分析方法

### ファネル分析（14日後に作成）

1. Mixpanel → Funnels
2. 以下のイベントでファネル作成：
   - `app_opened`
   - `onboarding_completed`
   - `paywall_viewed`
   - `trial_started`
   - `purchase_completed`
3. 「Breakdown by」→ `asa_keyword_id`

### キーワード→課金率レポート

1. Mixpanel → Insights
2. イベント: `purchase_completed`
3. Group by: `asa_keyword_id`
4. 14日後にこのレポートを見て、課金率の高いキーワードを特定

### ASAレポートとの突合

`asa_keyword_id` の数値は、ASAダッシュボードの「Keywords」タブでキーワード名と対応している。

---

## テスト方法

### 開発中のテスト

1. アプリをアンインストール
2. Xcodeからビルド＆実行
3. コンソールで以下を確認:

**期待するログ（Organic/開発中）:**
```
[ASAAttribution] ASA attribution not available: ...
[Analytics] Tracked event: app_opened
```

**2回目以降:**
```
[ASAAttribution] ASA attribution already checked, skipping
```

### Mixpanelで確認

1. Mixpanel → Users → Explore
2. 自分のユーザーを検索
3. User Properties に `asa_attribution: false` があることを確認

### 本番テスト（ASA広告経由）

1. ASAキャンペーンが審査通過後
2. App Storeで広告からインストール
3. Mixpanelで `asa_attribution: true` のユーザーを確認
4. `asa_keyword_id` でフィルタリング

---

## 参考リンク

- [Apple AdServices Documentation](https://developer.apple.com/documentation/adservices/aaattribution/)
- [Jake Mor #51](https://twitter.com/jakemor): "Send keyword attribution to @Mixpanel"
- [Mixpanel User Properties](https://docs.mixpanel.com/docs/tracking/how-tos/user-profiles)
