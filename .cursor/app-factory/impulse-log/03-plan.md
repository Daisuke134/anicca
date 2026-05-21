# ImpulseLog — 技術設計（plan.md）

**作成日:** 2026-02-26

---

## アーキテクチャ

**SwiftUI MVC + SwiftData**（シンプル・テスト容易・iOS 15+互換）

```
ImpulseLogApp
├── Models/
│   ├── ImpulseLog.swift          ← SwiftData モデル
│   ├── EmotionType.swift         ← 感情タイプ enum
│   └── TriggerTag.swift          ← トリガータグ enum
├── Views/
│   ├── Onboarding/
│   │   ├── OnboardingWelcomeView.swift
│   │   ├── PainSelectionView.swift
│   │   ├── LiveDemoView.swift
│   │   └── NotificationPermissionView.swift
│   ├── Main/
│   │   ├── MainTabView.swift
│   │   ├── LogHomeView.swift
│   │   ├── QuickLogSheet.swift
│   │   └── ReportsView.swift
│   ├── Paywall/
│   │   └── PaywallView.swift
│   └── Settings/
│       └── SettingsView.swift
├── Services/
│   ├── SubscriptionManager.swift  ← RevenueCat
│   ├── NotificationService.swift  ← APNs
│   ├── MixpanelService.swift      ← 分析
│   └── LocalizationHelper.swift   ← OS言語判定
├── Localizable.strings (en/ja)
└── PrivacyInfo.xcprivacy
```

---

## データモデル

```swift
@Model
class ImpulseLog {
    var id: UUID
    var timestamp: Date
    var emotionType: String        // "anger", "anxiety", "panic", "sadness", "impulse"
    var intensity: Int             // 1-10
    var triggerTag: String         // "work", "family", "traffic", "social", "self", "other"
    var note: String?              // Pro のみ
    var isProLog: Bool             // Free制限チェック用
}
```

---

## Free/Pro 差分

| 機能 | Free | Pro |
|------|------|-----|
| 1日のログ件数 | 5件 | 無制限 |
| 履歴 | 直近7日 | 全期間 |
| 感情タグ | 5種類 | 20種類 |
| メモ追加 | ❌ | ✅ |
| 週次レポート | ❌ | ✅ |
| パターン分析 | ❌ | ✅ |
| カスタムタグ | ❌ | ✅ |
| エクスポート | ❌ | ✅ |

---

## RevenueCat 設計

| 項目 | 値 |
|------|-----|
| Monthly Product ID | com.anicca.impulselog.premium.monthly |
| Annual Product ID | com.anicca.impulselog.premium.yearly |
| Entitlement | pro |
| Offering ID | default |

---

## Mixpanel イベント一覧

| イベント | プロパティ |
|---------|-----------|
| `app_opened` | `is_pro`, `onboarding_complete` |
| `log_created` | `emotion_type`, `intensity`, `trigger_tag`, `is_free_limit_hit` |
| `paywall_viewed` | `offering_id`, `source` |
| `subscription_started` | `plan`, `offering_id` |
| `report_viewed` | `period`, `is_pro` |
| `onboarding_step_completed` | `step` |

---

## 通知設計

| 通知 | タイミング | コンテンツ |
|------|-----------|-----------|
| 夕方リマインダー | 毎日 20:00 | 「今日の感情を記録しよう」 |
| 週次レポート | 毎週月曜 09:00 | 「先週のパターンが届いています」 |
