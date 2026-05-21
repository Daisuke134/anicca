# Hard Paywall + Monthly + Free Trial - 仕様書

> 作成日: 2026-01-24
> ステータス: Draft
> バージョン: 1.3.0

---

## 目次

1. [概要](#1-概要)
2. [As-Is（現状）](#2-as-is現状)
3. [To-Be（変更後）](#3-to-be変更後)
4. [To-Be チェックリスト](#4-to-be-チェックリスト)
5. [テストマトリックス](#5-テストマトリックス)
6. [実装詳細](#6-実装詳細)
7. [Unit Tests](#7-unit-tests)
8. [手動テストチェックリスト](#8-手動テストチェックリスト👤-ユーザー)
9. [Skills / Sub-agents](#9-skills--sub-agents)
10. [ローカライズ](#10-ローカライズ)
11. [実行手順](#11-実行手順)
12. [レビューチェックリスト](#12-レビューチェックリスト)

---

## 1. 概要

### 何を解決するか

現状はソフトペイウォールで、ユーザーが無料のまま使い続けられる。無料ユーザーには10 Nudge/月の制限があるが、それでも収益化が弱い。

### なぜ必要か

- 収益化の強化（全員がSubscriberになる）
- シンプルなビジネスモデル（無料プランを廃止）
- Monthly + Free Trial で低い参入障壁を維持

### 決定事項

| 項目 | 決定 |
|------|------|
| Paywall | ハード（閉じられない） |
| プラン | Monthly のみ（Annual 廃止） |
| Free Trial | 1週間（Monthly に付与） |
| 無料ユーザー | 存在しない（全員 Subscriber） |
| Trial/Canceled | アプリ使用不可、Paywall でブロック |
| Profile Page | Cancel Subscription / Subscribe ボタン |

### 役割分担

| 担当 | タスク |
|------|--------|
| 👤 ユーザー | Superwall デザイン変更（Xボタン削除、Monthly のみ） |
| 👤 ユーザー | RevenueCat 設定（Monthly に Free Trial 追加） |
| 👤 ユーザー | 最終実機テスト（手動チェックリスト） |
| 🤖 Claude | iOS コード実装、Unit Tests |

---

## 2. As-Is（現状）

### 2.1 ProfileView - 購読 UI

```swift
// 現在: Plan表示 + タップでPaywall or CustomerCenter
Button {
    if appState.subscriptionInfo.plan == .free {
        SuperwallManager.shared.register(placement: SuperwallPlacement.profilePlanTap.rawValue)
    } else {
        showingManageSubscription = true  // CustomerCenterView
    }
} label: {
    row(label: String(localized: "profile_row_plan"), value: planDisplayValue, showsChevron: true)
}
```

**問題:**
- 「Plan: Free」「Plan: Pro (Monthly)」のように表示
- 無料ユーザーでもアプリを使い続けられる

### 2.2 Paywall 表示

```swift
// SuperwallPlacement.swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"  // ソフトペイウォール
    case nudgeCardComplete5 = "nudge_card_complete_5"
    case nudgeCardComplete10 = "nudge_card_complete_10"
    case profilePlanTap = "profile_plan_tap"
}
```

**問題:**
- 全て閉じられる（ソフトペイウォール）
- 無料ユーザーでも通知を受け取れる（10回/月まで）

### 2.3 Nudge 制限（10回/月）

```swift
// AppState.swift
var canReceiveNudge: Bool {
    if subscriptionInfo.plan == .pro { return true }
    return monthlyNudgeCount < 10  // ← 無料ユーザー制限
}
```

**問題:**
- 複雑なロジック
- 月間カウント管理が必要

### 2.4 SubscriptionInfo

```swift
struct SubscriptionInfo {
    enum Plan: String { case free, grace, pro }
    var status: String  // "free", "trialing", "active", "canceled", "expired"
    var isEntitled: Bool { plan != .free && status != "expired" }
    var shouldShowPaywall: Bool { !isEntitled }
}
```

---

## 3. To-Be（変更後）

### 3.1 ProfileView - 購読 UI

```swift
// 変更後: Cancel Subscription / Subscribe ボタン
private var subscriptionButton: some View {
    Button {
        if appState.subscriptionInfo.isActiveSubscriber {
            // アクティブ購読者 → Apple購読管理画面へ
            if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                UIApplication.shared.open(url)
            }
        } else {
            // 未購読/キャンセル済み → Paywall表示
            SuperwallManager.shared.register(placement: SuperwallPlacement.resubscribe.rawValue)
        }
    } label: {
        HStack {
            Text(appState.subscriptionInfo.isActiveSubscriber
                ? String(localized: "profile_cancel_subscription")
                : String(localized: "profile_subscribe"))
                .font(.system(size: 16))
                .foregroundStyle(appState.subscriptionInfo.isActiveSubscriber
                    ? AppTheme.Colors.secondaryLabel
                    : AppTheme.Colors.accent)
            Spacer()
            Image(systemName: "chevron.right")
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .opacity(0.6)
        }
        .padding(.vertical, 14)
    }
    .buttonStyle(.plain)
    .accessibilityIdentifier("subscription_button")
}
```

### 3.2 SubscriptionInfo 拡張

```swift
extension SubscriptionInfo {
    /// 許可されたステータス（allowlist: fail-close 設計）
    /// これ以外のステータスは全てブロック
    private static let allowedStatuses: Set<String> = [
        "active", "trialing",
        // Grace 系ステータス（後方互換）
        "grace", "in_grace_period", "billing_issue", "billing_retry"
    ]

    /// アクティブな購読者かどうか（Trial、Grace含む）
    /// isSubscriptionExpiredOrCanceled の論理否定として定義
    var isActiveSubscriber: Bool {
        return !isSubscriptionExpiredOrCanceled
    }

    /// 購読がキャンセル済み/期限切れかどうか（ブロック対象）
    /// fail-close 設計: 許可リストにないステータスは全てブロック
    /// 注: RevenueCat が grace 期間終了時に plan を .free に更新するため、
    ///     通常は plan=.grace + status=expired のような不整合は発生しない
    var isSubscriptionExpiredOrCanceled: Bool {
        // Free プランは常にブロック（セキュリティ: 最初にチェック）
        if plan == .free { return true }

        // Grace プランも Pro プランも同じ allowlist でチェック（fail-close 統一）
        // 注: .grace でも status が expired/canceled なら異常状態としてブロック
        return !Self.allowedStatuses.contains(status)
    }
}
```

### 3.3 ハードペイウォール（アプリブロック）

```swift
// MainTabView.swift または AppState
@ViewBuilder
var body: some View {
    if appState.subscriptionInfo.isSubscriptionExpiredOrCanceled && appState.hasCompletedOnboarding {
        // 購読なし → アプリをブロック、Paywall表示
        BlockedView()
    } else {
        // 購読あり → 通常のアプリ
        TabView { ... }
    }
}
```

```swift
// BlockedView.swift（新規）
struct BlockedView: View {
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "lock.fill")
                .font(.system(size: 60))
                .foregroundStyle(AppTheme.Colors.secondaryLabel)

            Text(String(localized: "blocked_title"))
                .font(.title2.bold())

            Text(String(localized: "blocked_message"))
                .font(.body)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .multilineTextAlignment(.center)

            Button(String(localized: "profile_subscribe")) {
                SuperwallManager.shared.register(placement: SuperwallPlacement.resubscribe.rawValue)
            }
            .buttonStyle(.borderedProminent)
            .accessibilityIdentifier("blocked_subscribe_button")
        }
        .padding()
    }
}
```

### 3.4 Nudge 制限の削除

```swift
// AppState.swift - 変更後
var canReceiveNudge: Bool {
    // 全員がSubscriber前提なので、常にtrue
    // 購読チェックはBlockedViewで行う
    return true
}

// 以下を削除:
// - monthlyNudgeCount
// - checkAndResetMonthlyNudgeCountIfNeeded()
// - incrementMonthlyNudgeCount()
// - 関連するUserDefaultsキー
```

### 3.5 SuperwallPlacement 追加

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"  // ハード化（Superwall側で設定）
    case resubscribe = "resubscribe"  // 再購読用（Trial なし）
    // 削除: nudgeCardComplete5, nudgeCardComplete10, profilePlanTap
}
```

---

## 4. To-Be チェックリスト

| # | To-Be | 実装箇所 |
|---|-------|----------|
| 1 | ProfileView に Cancel/Subscribe ボタン | ProfileView.swift |
| 2 | SubscriptionInfo に isActiveSubscriber 追加 | SubscriptionInfo.swift |
| 3 | SubscriptionInfo に isSubscriptionExpiredOrCanceled 追加 | SubscriptionInfo.swift |
| 4 | キャンセル済みユーザーをブロック（BlockedView） | BlockedView.swift（新規） |
| 5 | MainTabView でブロック判定 | MainTabView.swift |
| 6 | canReceiveNudge を常に true に変更 | AppState.swift |
| 7 | 月間カウントロジック削除 | AppState.swift |
| 8 | SuperwallPlacement に resubscribe 追加 | SuperwallPlacement.swift |
| 9 | 不要な Placement 削除（nudgeCardComplete5/10, profilePlanTap） | SuperwallPlacement.swift |
| 10 | ローカライズ追加 | Localizable.strings |

---

## 5. テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | isActiveSubscriber（active） | `test_isActiveSubscriber_whenActive_returnsTrue()` | ✅ |
| 2 | isActiveSubscriber（trialing） | `test_isActiveSubscriber_whenTrialing_returnsTrue()` | ✅ |
| 3 | isActiveSubscriber（canceled） | `test_isActiveSubscriber_whenCanceled_returnsFalse()` | ✅ |
| 4 | isActiveSubscriber（grace plan + grace status） | `test_isActiveSubscriber_whenGracePlanWithGraceStatus_returnsTrue()` | ✅ |
| 5 | isActiveSubscriber（grace plan + expired: fail-close） | `test_isActiveSubscriber_whenGracePlanWithExpiredStatus_returnsFalse()` | ✅ |
| 6 | isActiveSubscriber（pro + grace status） | `test_isActiveSubscriber_whenProWithGraceStatus_returnsTrue()` | ✅ |
| 7 | isActiveSubscriber（pro + expired） | `test_isActiveSubscriber_whenProExpired_returnsFalse()` | ✅ |
| 8 | isActiveSubscriber（pro + unknown: fail-close） | `test_isActiveSubscriber_whenProUnknownStatus_returnsFalse()` | ✅ |
| 9 | isSubscriptionExpiredOrCanceled（expired） | `test_isExpiredOrCanceled_whenExpired_returnsTrue()` | ✅ |
| 10 | isSubscriptionExpiredOrCanceled（free） | `test_isExpiredOrCanceled_whenFree_returnsTrue()` | ✅ |
| 11 | isSubscriptionExpiredOrCanceled（active） | `test_isExpiredOrCanceled_whenActive_returnsFalse()` | ✅ |
| 12 | isSubscriptionExpiredOrCanceled（grace plan + grace status） | `test_isExpiredOrCanceled_whenGracePlanWithGraceStatus_returnsFalse()` | ✅ |
| 13 | isSubscriptionExpiredOrCanceled（pro + grace status） | `test_isExpiredOrCanceled_whenProWithGraceStatus_returnsFalse()` | ✅ |
| 14 | isSubscriptionExpiredOrCanceled（free + grace status） | `test_isExpiredOrCanceled_whenFreeWithGraceStatus_returnsTrue()` | ✅ |
| 15 | canReceiveNudge は常に true | `test_canReceiveNudge_alwaysReturnsTrue()` | ✅ |
| 16 | 月間カウントロジック削除 | 👤 手動テスト（コード確認） | ✅ |
| 17 | SuperwallPlacement に resubscribe 追加 | 👤 手動テスト | ✅ |
| 18 | 不要な Placement 削除 | 👤 手動テスト（コード確認） | ✅ |
| 19 | BlockedView が表示される (To-Be #4, #5) | 👤 手動テスト 8.5 | ✅ |
| 20 | BlockedView ローカライズ (To-Be #10) | 👤 手動テスト 8.9 | ✅ |
| 21 | Subscribe ボタンで Paywall 表示 | 👤 手動テスト 8.5, 8.6 | ✅ |
| 22 | Cancel Subscription で Apple 設定へ (To-Be #1) | 👤 手動テスト 8.4 | ✅ |
| 23 | Profile ボタン表示切替 (To-Be #1) | 👤 手動テスト 8.4 | ✅ |

---

## 6. 実装詳細

### 6.1 変更ファイル一覧

| ファイル | 変更内容 |
|----------|----------|
| `SubscriptionInfo.swift` | isActiveSubscriber, isSubscriptionExpiredOrCanceled 追加 |
| `ProfileView.swift` | Plan行削除、Cancel/Subscribeボタン追加 |
| `BlockedView.swift` | 新規作成 |
| `MainTabView.swift` | ブロック判定追加 |
| `AppState.swift` | canReceiveNudge変更、月間カウント削除 |
| `SuperwallPlacement.swift` | resubscribe追加、不要なもの削除 |
| `Localizable.strings (en)` | 新規文字列追加 |
| `Localizable.strings (ja)` | 新規文字列追加 |

### 6.2 削除するコード

| ファイル | 削除内容 |
|----------|----------|
| `AppState.swift` | monthlyNudgeCount, checkAndResetMonthlyNudgeCountIfNeeded(), incrementMonthlyNudgeCount() |
| `AppState.swift` | monthlyNudgeCountKey, lastNudgeResetMonthKey, lastNudgeResetYearKey |
| `MainTabView.swift` | handleNudgeCardCompletion内のPaywall表示ロジック（5回、10回） |
| `SuperwallPlacement.swift` | nudgeCardComplete5, nudgeCardComplete10, profilePlanTap |

---

## 7. Unit Tests

```swift
// SubscriptionInfoTests.swift
import Testing
@testable import aniccaios

struct SubscriptionInfoTests {

    // MARK: - isActiveSubscriber Tests

    @Test
    func test_isActiveSubscriber_whenActive_returnsTrue() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "active",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: true
        )
        #expect(info.isActiveSubscriber == true)
    }

    @Test
    func test_isActiveSubscriber_whenTrialing_returnsTrue() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "trialing",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: true
        )
        #expect(info.isActiveSubscriber == true)
    }

    @Test
    func test_isActiveSubscriber_whenCanceled_returnsFalse() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "canceled",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: false
        )
        #expect(info.isActiveSubscriber == false)
    }

    @Test
    func test_isActiveSubscriber_whenProExpired_returnsFalse() {
        // plan=.pro でも status="expired" ならブロック
        let info = SubscriptionInfo(
            plan: .pro,
            status: "expired",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isActiveSubscriber == false)
    }

    @Test
    func test_isActiveSubscriber_whenProUnknownStatus_returnsFalse() {
        // fail-close: 未知のステータスはブロック
        let info = SubscriptionInfo(
            plan: .pro,
            status: "some_unknown_status",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isActiveSubscriber == false)
    }

    @Test
    func test_isActiveSubscriber_whenGracePlanWithGraceStatus_returnsTrue() {
        let info = SubscriptionInfo(
            plan: .grace,
            status: "grace",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isActiveSubscriber == true)
    }

    @Test
    func test_isActiveSubscriber_whenGracePlanWithExpiredStatus_returnsFalse() {
        // fail-close: .grace でも status が allowlist 外ならブロック
        let info = SubscriptionInfo(
            plan: .grace,
            status: "expired",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isActiveSubscriber == false)
    }

    @Test
    func test_isActiveSubscriber_whenProWithGraceStatus_returnsTrue() {
        // 後方互換: plan=.pro, status=grace のケース
        let info = SubscriptionInfo(
            plan: .pro,
            status: "in_grace_period",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isActiveSubscriber == true)
    }

    // MARK: - isSubscriptionExpiredOrCanceled Tests

    @Test
    func test_isExpiredOrCanceled_whenExpired_returnsTrue() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "expired",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isSubscriptionExpiredOrCanceled == true)
    }

    @Test
    func test_isExpiredOrCanceled_whenFree_returnsTrue() {
        let info = SubscriptionInfo.free
        #expect(info.isSubscriptionExpiredOrCanceled == true)
    }

    @Test
    func test_isExpiredOrCanceled_whenCanceled_returnsTrue() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "canceled",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: false
        )
        #expect(info.isSubscriptionExpiredOrCanceled == true)
    }

    @Test
    func test_isExpiredOrCanceled_whenActive_returnsFalse() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "active",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: true
        )
        #expect(info.isSubscriptionExpiredOrCanceled == false)
    }

    @Test
    func test_isExpiredOrCanceled_whenTrialing_returnsFalse() {
        let info = SubscriptionInfo(
            plan: .pro,
            status: "trialing",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: true
        )
        #expect(info.isSubscriptionExpiredOrCanceled == false)
    }

    @Test
    func test_isExpiredOrCanceled_whenGracePlanWithGraceStatus_returnsFalse() {
        let info = SubscriptionInfo(
            plan: .grace,
            status: "grace",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isSubscriptionExpiredOrCanceled == false)
    }

    @Test
    func test_isExpiredOrCanceled_whenProWithGraceStatus_returnsFalse() {
        // 後方互換: plan=.pro, status=billing_issue のケース
        let info = SubscriptionInfo(
            plan: .pro,
            status: "billing_issue",
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isSubscriptionExpiredOrCanceled == false)
    }

    @Test
    func test_isExpiredOrCanceled_whenFreeWithGraceStatus_returnsTrue() {
        // セキュリティ: plan=.free は status に関わらず常にブロック
        let info = SubscriptionInfo(
            plan: .free,
            status: "billing_issue",  // grace 系ステータスでも free ならブロック
            currentPeriodEnd: nil,
            managementURL: nil,
            lastSyncedAt: .now,
            productIdentifier: nil,
            planDisplayName: nil,
            priceDescription: nil,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: nil
        )
        #expect(info.isSubscriptionExpiredOrCanceled == true)
    }
}
```

---

## 8. 手動テストチェックリスト（👤 ユーザー）

実装完了後、ユーザーが実機で確認するチェックリスト。

| # | カテゴリ | テスト項目 | 確認 |
|---|---------|-----------|------|
| 1 | 基本動作 | アプリが起動する | [ ] |
| 2 | 基本動作 | クラッシュしない | [ ] |
| 3 | オンボーディング | 完了後 Paywall が表示される | [ ] |
| 4 | オンボーディング | Paywall に X ボタンがない | [ ] |
| 5 | オンボーディング | 「Try 7 Days Free」ボタンが表示される | [ ] |
| 6 | オンボーディング | Monthly のみ表示（Annual なし） | [ ] |
| 7 | Free Trial | 「Try 7 Days Free」→ 購入フロー開始 | [ ] |
| 8 | Free Trial | Sandbox で Trial 開始できる | [ ] |
| 9 | Free Trial | Trial 後アプリが使える（BlockedView 出ない） | [ ] |
| 10 | Free Trial | Profile に「Cancel Subscription」表示 | [ ] |
| 11 | Profile | 「Cancel Subscription」ボタン表示 | [ ] |
| 12 | Profile | タップ → Apple 購読管理画面が開く | [ ] |
| 13 | BlockedView | キャンセル後 BlockedView 表示（🔒 + メッセージ） | [ ] |
| 14 | BlockedView | 「Subscribe」ボタン表示 | [ ] |
| 15 | BlockedView | タップ → Paywall 表示 | [ ] |
| 16 | 再購読 | 購読 → BlockedView 消えてアプリ使える | [ ] |
| 17 | リグレッション | My Path タブ正常 | [ ] |
| 18 | リグレッション | 通知が届く（Nudge 動作） | [ ] |
| 19 | リグレッション | NudgeCard 正常表示 | [ ] |
| 20 | リグレッション | 👍👎 フィードバック動作 | [ ] |
| 21 | ローカライズ EN | 「Cancel Subscription」「Subscribe」 | [ ] |
| 22 | ローカライズ JP | 「購読をキャンセル」「購読する」 | [ ] |
| 23 | ローカライズ EN | BlockedView「Subscribe to Continue」 | [ ] |
| 24 | ローカライズ JP | BlockedView「購読して続ける」 | [ ] |

### 事前設定（Superwall / RevenueCat）

| 設定場所 | 設定内容 |
|---------|---------|
| Superwall | onboarding_complete から閉じるボタン削除 |
| Superwall | resubscribe Placement 作成（Trial なし版） |
| RevenueCat | Monthly に 1週間 Free Trial 設定 |

---

## 9. Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec作成 | `/plan` | 実装計画の作成 |
| テスト実装 | `/tdd` | TDDでテスト先行開発 |
| コードレビュー | `/code-review` | 実装後のレビュー |
| E2Eテスト | 👤 手動テスト | ユーザーが実機で確認 |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |
| リリースノート | `/changelog-generator` | リリース時のchangelog作成 |

---

## 10. ローカライズ

### 10.1 英語 (en)

```
// Profile Page
"profile_cancel_subscription" = "Cancel Subscription";
"profile_subscribe" = "Subscribe";

// Blocked View
"blocked_title" = "Subscribe to Continue";
"blocked_message" = "Subscribe to continue using Anicca and start your journey of change.";
```

### 10.2 日本語 (ja)

```
// Profile Page
"profile_cancel_subscription" = "購読をキャンセル";
"profile_subscribe" = "購読する";

// Blocked View
"blocked_title" = "購読して続ける";
"blocked_message" = "購読してAniccaで変化の旅を始めましょう。";
```

---

## 11. 実行手順

### 11.1 事前準備（👤 ユーザー）

```bash
# Superwall Dashboard で設定
1. onboarding_complete Paywall から閉じるボタンを削除
2. Monthly プランのみ表示するように Paywall を編集
3. resubscribe Placement を作成（Trial なし版）

# RevenueCat Dashboard で設定
1. Monthly プランに 1週間 Free Trial を設定
2. Offering から Annual を削除（または非アクティブ化）
```

### 11.2 実装（🤖 Claude）

```bash
# 1. Unit Tests 作成
# SubscriptionInfo のテストを先に書く（TDD）

# 2. SubscriptionInfo 拡張
# isActiveSubscriber, isSubscriptionExpiredOrCanceled を追加

# 3. テスト実行
cd aniccaios && xcodebuild test \
  -project aniccaios.xcodeproj \
  -scheme aniccaios-staging \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.2' \
  -only-testing:aniccaiosTests/SubscriptionInfoTests \
  | xcpretty

# 4. ProfileView 変更
# Plan行を削除、Cancel/Subscribeボタンを追加

# 5. BlockedView 作成
# 新規ファイル

# 6. MainTabView 変更
# ブロック判定を追加

# 7. AppState 変更
# canReceiveNudge を常に true に、月間カウント削除

# 8. ローカライズ追加

# 9. ビルド確認
cd aniccaios && fastlane build_for_device

# 10. ユーザーに手動テストチェックリストを提示
```

### 11.3 最終確認（👤 ユーザー）

**セクション 8 の手動テストチェックリストを使用して確認。**

全項目にチェックが入ったら「OK」と報告 → dev にマージ。

---

## 12. レビューチェックリスト

### Spec レビュー

- [ ] 全 To-Be がテストマトリックスに含まれているか
- [ ] 各 To-Be に対応するテストコードがあるか
- [ ] ローカライズ（日英）は正しいか
- [ ] As-Is の問題が To-Be で解決されるか

### コードレビュー

- [ ] isActiveSubscriber のロジックは正しいか
- [ ] isSubscriptionExpiredOrCanceled のロジックは正しいか
- [ ] BlockedView が正しく表示されるか
- [ ] 月間カウントロジックが完全に削除されているか
- [ ] 既存の Annual 購読者に影響がないか（RevenueCat が処理）
- [ ] アクセシビリティ識別子が設定されているか

### テストレビュー

- [ ] Unit Tests が全て PASS するか
- [ ] ビルドが成功するか
- [ ] 手動テストチェックリスト（セクション8）が全て完了するか

---

## 補足: 既存 Annual 購読者の扱い

**結論: 何もしなくていい。RevenueCat が自動で処理する。**

- 既存 Annual 購読者はそのまま Annual で継続
- 次回更新時も Annual のまま（キャンセルしない限り）
- 新規購入は Monthly のみになる
- RevenueCat の Offering から Annual を非アクティブにしても、既存購読者には影響なし

---

## 補足: Free Trial 悪用防止

**結論: Apple が自動で防いでくれる。追加実装不要。**

- Free Trial は Apple ID に紐づく（アプリアカウントではない）
- 同じ Apple ID で同じ商品の Free Trial は 1回しか使えない
- アプリ削除・再インストールしても Apple が記録している
- RevenueCat もこれを認識する
