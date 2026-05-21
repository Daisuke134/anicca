# Anicca Soft Paywall & Onboarding 完全決定書

> **作成日**: 2026年2月6日
> **最終更新**: 2026年2月6日
> **目的**: コンバージョン改善 - Soft Paywallへの移行
> **原則**: ベストプラクティスに基づいて決定。選択肢提示は禁止。

---

## Executive Summary

| # | 決定 | 根拠 |
|---|------|------|
| 1 | **Soft Paywall（Xボタンで閉じれる）** | 14人全員離脱 = データ収集不可。まずユーザーを獲得 |
| 2 | **Free Plan: 3通知/日** | Headspace式: 価値を体験させてからアップグレード誘導 |
| 3 | **月額$9.99のみ（1週間トライアル）** | まずシンプルに。コンバージョン不良なら年額$29.99追加 |
| 4 | **LIVE DEMO NUDGE追加** | 価値体験なしにPaywall = 離脱。体験させてから提示 |

---

## 0. 実装責務ファイルマッピング（正本）

| ファイル | パス | 責務 |
|---------|------|------|
| **MainTabView.swift** | `aniccaios/aniccaios/MainTabView.swift` | NudgeCard表示（`pendingNudgeCard`）、Upgrade Paywall トリガー（3回目/7回目）、日次再スケジュール |
| **MyPathTabView.swift** | `aniccaios/aniccaios/Views/MyPathTabView.swift` | 問題一覧、Subscribeボタン、DEBUG UI |
| **OnboardingFlowView.swift** | `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift` | オンボーディング遷移、LIVE DEMO、Paywall（初回）、レビューリクエスト |
| **AppState.swift** | `aniccaios/aniccaios/AppState.swift` | 課金状態SSOT（`subscriptionInfo`）、オンボーディングStep管理 |
| **OnboardingStep.swift** | `aniccaios/aniccaios/Onboarding/OnboardingStep.swift` | enum定義、legacy migration |
| **ProblemNotificationScheduler.swift** | `aniccaios/aniccaios/Notifications/ProblemNotificationScheduler.swift` | Free/Pro分岐、通知スケジュール |
| **FreePlanService.swift** | `aniccaios/aniccaios/Services/FreePlanService.swift` | **新規作成** — Free Plan通知ロジック |
| **DemoNudgeStepView.swift** | `aniccaios/aniccaios/Onboarding/DemoNudgeStepView.swift` | **新規作成** — LIVE DEMO画面 |
| **LLMNudgeService.swift** | `aniccaios/aniccaios/Services/LLMNudgeService.swift` | LLM Nudge取得（Pro限定ガード追加） |
| **ContentView.swift** | `aniccaios/aniccaios/ContentView.swift` | ルーティング（`ContentRouterView` → `OnboardingFlowView` or `MainTabView`） |

> **注意:** `MainTabView.swift` は実在する（`ContentView.swift` L25, L29 から参照）。`MyPathTabView` は `MainTabView` の子View。

---

## 1. Soft Paywall に変更する理由

### 現状の問題

```
TikTok広告 → アプリ起動 → Paywall → 14人全員離脱
```

**問題:**
1. **データがゼロ**: 誰もアプリを使っていないので、何が悪いか分からない
2. **信頼ゼロで課金要求**: ユーザーはAniccaの価値を体験していない
3. **広告費の無駄**: 14人のCACを払って0コンバージョン

### Soft Paywallの利点

| 指標 | Hard | Soft | 決定理由 |
|------|------|------|---------|
| コンバージョン率 | 10-12% | 2-5% | 低いが、まず0%を脱出 |
| トライアル開始率 | 15% | 45% | **3x多くのユーザーがアプリを体験** |
| データ収集 | なし（全員離脱） | あり（使用データ取得可） | **何が悪いか分かる** |
| 再アプローチ機会 | なし | あり（プッシュで再誘導可） | **2回目のチャンスがある** |

**出典:** [RevenueCat: Freemium drives 3x more trial starts](https://www.revenuecat.com/state-of-subscription-apps-2025)

---

## 2. 価格戦略

### Phase 1: 月額のみ

| プラン | 価格 | トライアル | 理由 |
|--------|------|-----------|------|
| **月額** | $9.99 | 1週間無料 | シンプル。まず検証 |

**年額は今は追加しない理由:**
- まだコンバージョンデータがない
- 複雑さを増やすとテストが困難
- 「月額でコンバートしない人が年額でコンバートする」は幻想

### Phase 2: 年額追加（v1.6.1スコープ外 — 将来検討）

> **⚠️ v1.6.1では年額は実装しない。** 以下は将来の参考情報のみ。

| プラン | 価格 | 月額換算 | 割引率 |
|--------|------|---------|--------|
| 年額 | $29.99 | $2.50 | 75% |

**$29.99の理由:**
- $49.99や$85.99は高すぎる（ユーザー信頼がまだない）
- $29.99は「ランチ3回分」で心理的ハードルが低い
- アップセルで収益化、まず契約を取る

**⚠️ 年額追加時の必須migration（将来の別Spec）:**

| 項目 | 必要な作業 |
|------|-----------|
| RevenueCat Product/Package | 新product作成、Offering にPackage追加 |
| Singular SKAN CV マッピング | CV値の再定義（現行CV3=49-50との整合） |
| Mixpanel 分析軸 | 月額/年額の分離トラッキング |
| A/Bテスト設計 | 既存月額ユーザーへの影響評価 |
| ロールバック条件 | コンバージョン悪化時の切り戻し手順 |

---

## 3. Free Plan 設計（3通知/日）

### 決定: 3通知を時間帯で分散配信

| 時間帯 | 配信時刻 | 目的 |
|--------|---------|------|
| **朝** | 8:00 AM | 起床直後の意志力が高い時間 |
| **昼** | 12:30 PM | ランチ後の眠気対策 |
| **夜** | 8:00 PM | 就寝前の振り返り |

### 複数問題選択時の配信ロジック

**決定: 日替わりローテーション**

```
ユーザーが選択: [夜更かし, 反芻, 不安, 先延ばし, 自己嫌悪]（5問題）

Day 1:
  朝 8:00  → 先延ばし (procrastination)
  昼 12:30 → 不安 (anxiety)
  夜 8:00  → 夜更かし (staying_up_late)

Day 2:
  朝 8:00  → 自己嫌悪 (self_loathing)
  昼 12:30 → 反芻 (rumination)
  夜 8:00  → 先延ばし (procrastination)

Day 3:
  朝 8:00  → 不安 (anxiety)
  昼 12:30 → 夜更かし (staying_up_late)
  夜 8:00  → 自己嫌悪 (self_loathing)
```

**なぜローテーションか:**
1. **全問題を体験させる**: 1問題だけだと「他も欲しい」と思わない
2. **アップグレード動機を作る**: 「今日は夜更かしのNudgeが来なかった→もっと欲しい」
3. **飽きさせない**: 同じ問題ばかりだと通知を無視し始める

### Nudge内容の決定

| ユーザー | 使用するNudge |
|---------|-------------|
| **Free** | ルールベースNudgeのみ（LLMなし） |
| **Pro** | LLM生成Nudge（パーソナライズ） |

**なぜFreeはルールベースか:**
1. LLMはAPIコスト発生 = 無料ユーザーにはNG
2. ルールベースでも十分価値がある
3. 「もっとパーソナライズされたNudgeが欲しい」→アップグレード動機

---

## 4. Paywall 表示タイミング（全4箇所）

| # | タイミング | 対象ユーザー | 詳細 |
|---|-----------|-------------|------|
| **1** | オンボーディング完了後 | 全員（新規） | notifications → paywall（Soft、X で閉じれる） |
| **2** | メイン画面の Subscribe ボタン | Free ユーザー | 自発的にタップ |
| **3** | **3回目** PRIMARY タップ | Free ユーザー | カード完了3回目で自動表示 |
| **4** | **7回目** PRIMARY タップ | Free ユーザー | カード完了7回目で自動表示 |

**フロー図:**

```
【新規ユーザー】
welcome → struggles → LIVE DEMO → notifications → Paywall (1回目)
                                                      │
                                                      ├─ 購入 → Pro
                                                      │
                                                      └─ X で閉じる → Free Plan
                                                                         │
                                                                         ▼
【Free ユーザー（メイン画面）】

通知タップ → カード → PRIMARY タップ (1回目) → 閉じる
通知タップ → カード → PRIMARY タップ (2回目) → 閉じる
通知タップ → カード → PRIMARY タップ (3回目) → Paywall ← ここ
通知タップ → カード → PRIMARY タップ (4回目) → 閉じる
通知タップ → カード → PRIMARY タップ (5回目) → 閉じる
通知タップ → カード → PRIMARY タップ (6回目) → 閉じる
通知タップ → カード → PRIMARY タップ (7回目) → Paywall ← ここ
通知タップ → カード → PRIMARY タップ (8回目+) → 閉じる（Paywall なし）

※ いつでも Subscribe ボタンタップ → Paywall
```

---

## 5. オンボーディング再構築

### 新フロー（5画面 — Value 削除、LIVE DEMO で置き換え）

**ベストプラクティス:** 3-5画面が最適。5画面→3画面で200%コンバージョン改善の事例あり。
**出典:** [UXCam](https://uxcam.com/blog/10-apps-with-great-user-onboarding/), [Medium](https://medium.com/@ridhisingh/how-we-improved-our-onboarding-funnel-increased-conversions-by-200-9a106b238247)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. WELCOME SCREEN                                               │
├─────────────────────────────────────────────────────────────────┤
│ - "6年間、何も変われなかった人のために作った"                     │
│ - 復元ボタン（既存ユーザー用）                                   │
│ - [次へ] ボタン                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. STRUGGLES SCREEN                                             │
├─────────────────────────────────────────────────────────────────┤
│ - "あなたが変えたいことを選んでください"                         │
│ - 13問題のグリッド表示                                          │
│ - 複数選択可能                                                  │
│ - [次へ] ボタン                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ★ LIVE DEMO NUDGE ★（Value を置き換え）                     │
├─────────────────────────────────────────────────────────────────┤
│ ■ 体験フロー:                                                   │
│                                                                 │
│ Step 1: 画面表示                                                │
│   - "最初のNudgeを体験しましょう"                               │
│   - [Nudgeを受け取る] ボタン                                    │
│                                                                 │
│ Step 2: ボタンタップ後（即座にアニメーション）                   │
│   - 0.3秒待機 → カードがスライドイン（0.5秒アニメ）             │
│   - ★ カウントダウンなし（シンプルに）★                        │
│                                                                 │
│ Step 3: カード表示（NudgeCardViewを再利用）                      │
│   - 選択した問題の最初の1つに基づいてパーソナライズ              │
│   - 使用コンテンツ: variant 1（`NudgeContent.content(for:variantIndex:0)`）│
│   ┌─────────────────────────────────────────────────┐           │
│   │                                          [X]    │           │
│   │                                                 │           │
│   │                    🌙                           │           │
│   │              STAYING UP LATE                    │           │
│   │                                                 │           │
│   │         ────────────────────────                │           │
│   │         "今夜も夜更かしする？"                  │           │
│   │         ────────────────────────                │           │
│   │                                                 │           │
│   │         睡眠不足は明日の...                     │           │
│   │                                                 │           │
│   │         ────────────────────────                │           │
│   │                                                 │           │
│   │       ┌─────────────────────────┐               │           │
│   │       │   今すぐ布団に入る      │ ← PRIMARY    │           │
│   │       └─────────────────────────┘   (タップで次へ)          │
│   │                                                 │           │
│   │         ────────────────────────                │           │
│   │                                                 │           │
│   │              👍         👎       ← Feedback    │           │
│   │                                    (任意)       │           │
│   └─────────────────────────────────────────────────┘           │
│                                                                 │
│ Step 4: PRIMARYボタンタップ → notifications画面へ               │
│   - 👍/👎 はタップしてもしなくてもOK（任意のフィードバック）    │
│   - PRIMARY ボタンが「次へ進む」トリガー                        │
│                                                                 │
│ ■ 技術的詳細:                                                   │
│   - 実際のプッシュ通知は送らない（複雑すぎる）                  │
│   - アプリ内でカードをアニメーション表示                        │
│   - 既存のNudgeCardViewを再利用                                 │
│   - コンテンツ: 選択した問題の最初のものの variant 1            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. NOTIFICATION PERMISSION                                      │
├─────────────────────────────────────────────────────────────────┤
│ - "通知を許可してください"                                      │
│ - 理由説明: "Nudgeを受け取るために必要です"                     │
│ - [通知を許可] ボタン → システム許可ダイアログ                  │
│ - ★ 許可後、自動的に次の画面へ ★                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. PAYWALL (Soft - Xボタンで閉じれる)                          │
├─────────────────────────────────────────────────────────────────┤
│ - ★ 右上に「×」ボタン → 閉じてFree Planへ ★                   │
│ - 見出し: "毎日、あなたに合ったNudgeを"                         │
│ - 月額$9.99（1週間無料トライアル）                              │
│ - [1週間無料で始める] ボタン                                    │
│ - 下部: "Free Plan（3通知/日）で続ける" リンク                  │
│                                                                 │
│ ■ Xボタンタップ時:                                             │
│   - Free Planでメイン画面へ遷移                                 │
│   - 3通知/日のスケジュールを自動設定                            │
│   - "Free Planで始めました。3通知/日が届きます" トースト表示    │
│                                                                 │
│ ■ Paywall閉じた直後:                                           │
│   - レビューリクエスト表示（SKStoreReviewController）           │
│   - 購入 or X で閉じた直後 = コミットした瞬間 = 最適タイミング  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. レビューリクエストタイミング

### 変更: 3回目カードタップ → Paywall閉じた直後

| 項目 | Before | After |
|------|--------|-------|
| **タイミング** | 3回目カードPRIMARYタップ後 | **Paywall閉じた直後**（購入 or X） |
| **場所** | `MainTabView.swift` | `OnboardingFlowView.swift` |
| **受け入れ率** | ~6.7% | **~11.2%**（最高） |

**根拠:**
- Paywall を見た = アプリにコミットした瞬間
- 購入した場合 → 満足度最高
- X で閉じた場合 → それでもアプリを使い続ける意思がある

**出典:** App Store review request timing best practices 2025-2026

### 実装変更

```swift
// MainTabView.swift - 削除するコード
// 3回目: レビューリクエスト
// if count == 3 && !appState.hasRequestedReview { ... }

// OnboardingFlowView.swift - 追加するコード
private func handlePaywallDismiss() {
    if !appState.hasRequestedReview {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if let scene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene {
                SKStoreReviewController.requestReview(in: scene)
            }
        }
        appState.markReviewRequested()
    }
}
```

---

## 7. Superwall/RevenueCat 実装

### Xボタン（閉じるボタン）の実装

**決定: RevenueCatUI `displayCloseButton` パラメータで制御**

| 設定箇所 | 設定内容 |
|---------|---------|
| **RevenueCatUI API** | `PaywallView(displayCloseButton: true)` で閉じるボタンを表示 |
| **Superwall** | 本Specでは使用しない。Paywall表示はすべて RevenueCatUI `PaywallView` が担当 |

**重要:** 閉じるボタンの正本は `RevenueCatUI.PaywallView(displayCloseButton:)` パラメータ。RevenueCat Dashboard のPaywall設定はビジュアル調整用であり、閉じるボタン制御のSSOTではない。

### コード修正（OnboardingFlowView.swift）

```swift
// Before（現在のコード - 56-72行目）
.fullScreenCover(isPresented: $showPaywall) {
    paywallContent(displayCloseButton: false)  // ← false = ハードペイウォールに見える
        .interactiveDismissDisabled(true)
        .onPurchaseCompleted { customerInfo in
            AnalyticsManager.shared.track(.onboardingPaywallPurchased)
            handlePaywallSuccess()
        }
        .onRestoreCompleted { customerInfo in
            if customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true {
                handlePaywallSuccess()
            }
        }
        .onAppear {
            AnalyticsManager.shared.track(.onboardingPaywallViewed)
        }
}

// After（修正後 - 全パッチ）
// ★ dismiss検知は fullScreenCover(onDismiss:) で管理（PaywallView に .onDismiss はない）
.fullScreenCover(isPresented: $showPaywall, onDismiss: {
    // ★ Xボタンタップ → RevenueCatUI が isPresented=false → fullScreenCover が閉じる → ここが発火
    if !didPurchaseOnPaywall {
        handlePaywallDismissedAsFree()
    }
}) {
    paywallContent(displayCloseButton: true)   // ← true に変更
        .interactiveDismissDisabled(true)      // スワイプ閉じは無効（X ボタンのみ）
        .onPurchaseCompleted { customerInfo in
            AnalyticsManager.shared.track(.onboardingPaywallPurchased)
            handlePaywallSuccess(customerInfo: customerInfo)  // ★ customerInfo を渡す
        }
        .onRestoreCompleted { customerInfo in
            if customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true {
                handlePaywallSuccess(customerInfo: customerInfo)  // ★ customerInfo を渡す
            }
        }
        .onAppear {
            AnalyticsManager.shared.track(.onboardingPaywallViewed)
        }
}

// ★ 追加するプロパティ（OnboardingFlowView内）
@State private var didPurchaseOnPaywall = false  // ★ 購入経路とX閉じ経路を分離

// ★ 追加するメソッド（OnboardingFlowView内）

// 購入成功時のハンドラ（★ SSOT更新 → 通知再構成 → 完了 → UI更新）
// ★ customerInfo を受け取るように変更（onPurchaseCompleted から渡す）
private func handlePaywallSuccess(customerInfo: CustomerInfo) {
    didPurchaseOnPaywall = true  // ★ 購入フラグをセット（onDismissでFree処理を防ぐ）
    Task {
        // 1. SSOT即時更新
        appState.updateSubscriptionInfo(from: customerInfo)
        // 2. 通知再構成（free_nudge_* 削除 → Pro通知スケジュール）
        await ProblemNotificationScheduler.shared
            .scheduleNotifications(for: appState.userProfile.struggles)
        // 3. オンボーディング完了
        appState.markOnboardingComplete()
        // 4. UI更新（最後）
        showPaywall = false
        // 5. レビューリクエスト
        requestReviewIfNeeded()
    }
}

// X ボタンで閉じた時のハンドラ（★ 購入後は呼ばれない）
private func handlePaywallDismissedAsFree() {
    // ★ 購入済みなら何もしない（購入後のdismissでFree処理が走るのを防ぐ）
    guard !didPurchaseOnPaywall else { return }

    showPaywall = false
    AnalyticsManager.shared.track(.onboardingPaywallDismissedFree)

    // 1. Free Planで通知スケジュール設定
    // ★ struggles は [String] なので ProblemType に変換
    let problems = appState.userProfile.struggles.compactMap { ProblemType(rawValue: $0) }
    FreePlanService.shared.scheduleFreePlanNudges(problems: problems)

    // 2. オンボーディング完了
    appState.markOnboardingComplete()

    // 3. レビューリクエスト（Paywall閉じた直後が最適）
    requestReviewIfNeeded()
}

// 共通: レビューリクエスト（購入 or X で1回だけ）
private func requestReviewIfNeeded() {
    guard !appState.hasRequestedReview else { return }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
        if let scene = UIApplication.shared.connectedScenes
            .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene {
            SKStoreReviewController.requestReview(in: scene)
        }
    }
    appState.markReviewRequested()
}
```

### Free vs Pro 判定（SSOT: Single Source of Truth）

**決定: `appState.subscriptionInfo.isEntitled` を唯一の判定ソースとする（SSOT）**

| ルール | 詳細 |
|--------|------|
| **SSOT** | `appState.subscriptionInfo.isEntitled`（`SubscriptionInfo.swift` L18: `plan != .free && status != "expired"`） |
| **新規API追加しない** | `SubscriptionManager.checkSubscriptionTier()` のような別ソースは作らない |
| **RevenueCat callback → AppState即時反映** | `appState.updateSubscriptionInfo(from: customerInfo)` で即座に反映（★ convenience overload 新規追加 — 下記参照） |
| **通知再構成は課金状態更新の後** | `subscriptionInfo` 更新完了 → `ProblemNotificationScheduler.scheduleNotifications()` の順序を保証 |

```swift
// ★ 全箇所で統一: appState.subscriptionInfo.isEntitled
// 以下のパターンのみ許可:
if appState.subscriptionInfo.isEntitled {
    // Pro
} else {
    // Free
}

// ★ 禁止: 別のAPI/直接RevenueCat呼び出しで判定
// NG: Purchases.shared.customerInfo() を直接呼んで判定
// NG: SubscriptionManager.checkSubscriptionTier() のような別ソース
```

**★ AppState に convenience overload を新規追加（既存API `updateSubscriptionInfo(_ info: SubscriptionInfo)` はそのまま維持）:**
```swift
// AppState.swift に追加
// ★ 新規: RevenueCat CustomerInfo → SubscriptionInfo 変換 + SSOT更新を1ステップで行う
// ★ 変換ロジックは既存の SubscriptionInfo(info:) initializer に完全委譲する
//   → grace判定、trialing/canceledステータス、entitlement fallback を全てカバー
func updateSubscriptionInfo(from customerInfo: CustomerInfo) {
    let info = SubscriptionInfo(info: customerInfo)  // ★ 唯一の変換SSOT
    updateSubscriptionInfo(info)  // ★ 既存APIに委譲
}
```
> ★ 重要: `SubscriptionInfo(info: CustomerInfo)` が唯一の CustomerInfo → SubscriptionInfo 変換SSOT。
> このinitializerは `SubscriptionManager.swift:233` に既存実装があり、grace判定・trialing/canceledステータス・
> entitlement fallback（configured ID未一致時の active entitlement検出）を全てカバーしている。
> 簡略版のマッピングを新たに作成することは禁止。

**購入後の状態反映シーケンス:**
```
onPurchaseCompleted { customerInfo in
    1. appState.updateSubscriptionInfo(from: customerInfo)  // ★ convenience overload → 既存API に委譲
    2. await ProblemNotificationScheduler.shared             // ★ 通知再構成
         .scheduleNotifications(for: appState.userProfile.struggles)
    3. showPaywall = false                                    // ★ UI更新は最後
}
```

---

## 8. Upgrade Trigger（Free → Pro 誘導）

### 決定: 3回目と7回目のPRIMARYタップ時にPaywall表示

| タイミング | アクション |
|-----------|-----------|
| **3回目** PRIMARY タップ | Paywall 表示 |
| **7回目** PRIMARY タップ | Paywall 表示 |
| **8回目以降** | Paywall なし（しつこくしない） |

### 実装（MainTabView.swift）— 完全パッチ

```swift
struct MainTabView: View {
    @EnvironmentObject private var appState: AppState
    @State private var showUpgradePaywall = false  // ★ 追加: Paywall表示状態

    var body: some View {
        MyPathTabView()
            .environmentObject(appState)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .fullScreenCover(item: $appState.pendingNudgeCard) { content in
                NudgeCardView(
                    content: content,
                    onPositiveAction: {
                        handleNudgeCardCompletion(content: content)
                    },
                    onNegativeAction: {
                        handleNudgeCardCompletion(content: content)
                    },
                    onFeedback: { isPositive in
                        // 既存のフィードバック処理
                        if isPositive {
                            NudgeStatsManager.shared.recordThumbsUp(
                                problemType: content.problemType.rawValue,
                                variantIndex: content.variantIndex
                            )
                        } else {
                            NudgeStatsManager.shared.recordThumbsDown(
                                problemType: content.problemType.rawValue,
                                variantIndex: content.variantIndex
                            )
                        }
                    },
                    onDismiss: {
                        appState.dismissNudgeCard()
                    }
                )
            }
            // ★ 追加: Upgrade Paywall（3回目/7回目トリガー）
            // ★ dismiss検知は fullScreenCover(onDismiss:) で管理
            .fullScreenCover(isPresented: $showUpgradePaywall, onDismiss: {
                // Upgrade Paywall の X閉じ — 特別な処理不要（Free のまま）
            }) {
                upgradePaywallView()
            }
            .background(AppBackground())
            .ignoresSafeArea(.keyboard, edges: .bottom)
    }

    // ★ 変更: 3回目レビューリクエスト削除、3回目/7回目Paywall追加
    private func handleNudgeCardCompletion(content: NudgeContent) {
        appState.incrementNudgeCardCompletedCount()
        let count = appState.nudgeCardCompletedCount
        appState.dismissNudgeCard()

        // Free ユーザーのみ: 3回目 or 7回目に Paywall 表示
        // ★ 既存の appState.subscriptionInfo.isEntitled を使用
        if (count == 3 || count == 7) && !appState.subscriptionInfo.isEntitled {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                showUpgradePaywall = true
            }
            return
        }

        // ★ 削除: 3回目レビューリクエスト（OnboardingFlowViewに移動済み）
    }

    // ★ 追加: Upgrade Paywall View
    // ★ dismiss は fullScreenCover(onDismiss:) で管理。PaywallView に .onDismiss は不要。
    @ViewBuilder
    private func upgradePaywallView() -> some View {
        if let offering = appState.cachedOffering {
            PaywallView(offering: offering, displayCloseButton: true)
                .applyDebugIntroEligibility()
                .onPurchaseCompleted { customerInfo in
                    handleUpgradePurchase(customerInfo: customerInfo)
                }
                .onRestoreCompleted { customerInfo in
                    if customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true {
                        handleUpgradePurchase(customerInfo: customerInfo)
                    }
                }
        } else {
            PaywallView(displayCloseButton: true)
                .applyDebugIntroEligibility()
                .onPurchaseCompleted { customerInfo in
                    handleUpgradePurchase(customerInfo: customerInfo)
                }
                .onRestoreCompleted { customerInfo in
                    if customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true {
                        handleUpgradePurchase(customerInfo: customerInfo)
                    }
                }
        }
    }

    // ★ 共通メソッド: Upgrade購入/復元後の処理（順序保証を1箇所で管理）
    private func handleUpgradePurchase(customerInfo: CustomerInfo) {
        AnalyticsManager.shared.track(.upgradePaywallPurchased)
        Task {
            // 1. SSOT即時更新
            appState.updateSubscriptionInfo(from: customerInfo)
            // 2. 通知再構成（free_nudge_* 削除 → Pro通知スケジュール）
            await ProblemNotificationScheduler.shared
                .scheduleNotifications(for: appState.userProfile.struggles)
            // 3. UI更新（最後 — 再構成完了後）
            showUpgradePaywall = false
        }
    }
}
```

---

## 9. Free Plan 実装詳細

### 新規ファイル

| ファイル | 目的 |
|---------|------|
| `FreePlanService.swift` | Free Plan のNudge制限管理 |
| `DemoNudgeStepView.swift` | LIVE DEMO NUDGE 画面 |

> ★ 注: アップグレード誘導は RevenueCat PaywallView（Soft Paywall）で統一。専用UIは不要。

### FreePlanService 仕様

```swift
// ★ 新規ファイル: aniccaios/aniccaios/Services/FreePlanService.swift

import Foundation
import UserNotifications

final class FreePlanService {
    static let shared = FreePlanService()
    static let dailyLimit = 3

    // ★ テスト用依存注入（DST/TZ テスト + notification/storage モックを可能にする）
    private let calendar: Calendar
    private let nowProvider: () -> Date
    private let notificationCenter: UNUserNotificationCenter
    private let defaults: UserDefaults

    init(
        calendar: Calendar = .current,
        nowProvider: @escaping () -> Date = { Date() },
        notificationCenter: UNUserNotificationCenter = .current(),
        defaults: UserDefaults = .standard
    ) {
        self.calendar = calendar
        self.nowProvider = nowProvider
        self.notificationCenter = notificationCenter
        self.defaults = defaults
    }

    private let slots: [(hour: Int, minute: Int)] = [
        (8, 0),   // 朝
        (12, 30), // 昼
        (20, 0)   // 夜
    ]

    // ★ remainingNudgesToday() は削除（未使用。更新/リセット設計が未定義のため混乱の元）
    // 将来必要になった場合は、インクリメント箇所・リセット契機・配信失敗時の扱いを設計してから再追加

    // 次のNudge配信時刻を計算（★ 注入された calendar/nowProvider を使用）
    func nextScheduledNudgeTimes() -> [Date] {
        let now = nowProvider()
        return slots.compactMap { slot in
            var components = calendar.dateComponents([.year, .month, .day], from: now)
            components.hour = slot.hour
            components.minute = slot.minute
            return calendar.date(from: components)
        }.filter { $0 > now }
    }

    // 問題のローテーション計算（★ guard追加: 空配列対策）
    // ★ 修正: day は 1 始まり（ordinality）なので -1 して 0-indexed に変換
    // day=1, slot=0 → index=0（先頭要素）
    func problemForSlot(day: Int, slot: Int, problems: [ProblemType]) -> ProblemType? {
        guard !problems.isEmpty else { return nil }  // ★ クラッシュ防止
        let index = (day - 1 + slot) % problems.count
        return problems[index]
    }

    // ★ 便利メソッド: [String] から呼び出す場合（既存APIとの整合性）
    func scheduleFreePlanNudges(struggles: [String]) {
        let problems = struggles.compactMap { ProblemType(rawValue: $0) }
        scheduleFreePlanNudges(problems: problems)
    }

    // Free Plan通知スケジュール設定
    // ★ 重要: 日替わりローテーションを実現するため、repeats: false で「今日の分」のみスケジュール
    // アプリ起動時 or 通知受信時 に翌日分を再スケジュールする
    func scheduleFreePlanNudges(problems: [ProblemType]) {
        // ★ guard追加: 問題未選択時は何もしない
        guard !problems.isEmpty else {
            print("[FreePlanService] No problems selected, skipping schedule")
            return
        }

        // ★ 注入された notificationCenter を使用（テスト時にモック可能）
        // 既存のFree Plan通知を削除
        notificationCenter.removePendingNotificationRequests(withIdentifiers:
            (0..<Self.dailyLimit).map { "free_nudge_\($0)" }
        )

        let today = nowProvider()
        let now = today
        var scheduledCount = 0  // ★ 追加: 今日スケジュールできた通知数をカウント

        for (index, slot) in slots.enumerated() {
            // ★ 追加: 過去時刻チェック — 今日のスロットが過去なら翌日にシフト
            var targetDay = today
            var dateComponents = calendar.dateComponents([.year, .month, .day], from: targetDay)
            dateComponents.hour = slot.hour
            dateComponents.minute = slot.minute

            if let scheduledDate = calendar.date(from: dateComponents), scheduledDate <= now {
                // ★ 過去時刻: 翌日にシフト
                targetDay = calendar.date(byAdding: .day, value: 1, to: today) ?? today
                dateComponents = calendar.dateComponents([.year, .month, .day], from: targetDay)
                dateComponents.hour = slot.hour
                dateComponents.minute = slot.minute
            }

            // ★ 修正: targetDay（シフト後の日付）から dayOfYear を計算
            // 翌日にシフトされた場合は翌日の dayOfYear を使用してローテーション
            let rotationDay = calendar.ordinality(of: .day, in: .year, for: targetDay) ?? 1
            guard let problem = problemForSlot(day: rotationDay, slot: index, problems: problems) else {
                continue
            }

            let content = UNMutableNotificationContent()
            content.title = problem.notificationTitle
            content.body = NudgeContent.notificationMessages(for: problem).first ?? ""
            content.sound = .default
            content.userInfo = [
                "problemType": problem.rawValue,
                "isRuleBased": true,  // ★ Free = ルールベースのみ
                "tier": "free"
            ]

            // ★ 変更: repeats: false で当日/翌日の分のみスケジュール
            let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: false)

            let request = UNNotificationRequest(
                identifier: "free_nudge_\(index)",
                content: content,
                trigger: trigger
            )
            notificationCenter.add(request)
            scheduledCount += 1
        }

        // ★ 修正: 今日の dayOfYear を保存（翌日の rescheduleIfNeeded で日付変更を検知）
        // rotationDay はスロット毎に異なる可能性があるが、「いつスケジュールしたか」は today 基準
        let todayDayOfYear = calendar.ordinality(of: .day, in: .year, for: today) ?? 1
        defaults.set(todayDayOfYear, forKey: "freePlanLastScheduledDay")

        print("[FreePlanService] Scheduled \(scheduledCount) nudges, saved day=\(todayDayOfYear)")
    }

    // ★ 新規: 日付が変わったら再スケジュール（アプリ起動時 or BGAppRefreshTask で呼び出し）
    // ★ 注入された calendar/nowProvider を使用
    func rescheduleIfNeeded(problems: [ProblemType]) {
        let today = nowProvider()
        let currentDay = calendar.ordinality(of: .day, in: .year, for: today) ?? 1
        let lastDay = defaults.integer(forKey: "freePlanLastScheduledDay")

        if currentDay != lastDay {
            scheduleFreePlanNudges(problems: problems)
        }
    }
}
```

### 既存コードへの組み込みパッチ

#### 0. MainTabView.swift への日次再スケジュール追加

```swift
// ★ MainTabView.swift の .onAppear または .task に追加
// Free ユーザーの日替わりローテーションを実現

.task {
    // ★ 追加: 日付が変わっていたら Free Plan 通知を再スケジュール
    if !appState.subscriptionInfo.isEntitled {
        let problems = appState.userProfile.struggles.compactMap { ProblemType(rawValue: $0) }
        FreePlanService.shared.rescheduleIfNeeded(problems: problems)
    }
}
```

#### 1. ProblemNotificationScheduler.swift への分岐追加

```swift
// ★ 変更箇所: scheduleNotifications() メソッド内
// ★ 注意: 既存APIは [String] 型のまま維持

func scheduleNotifications(for problems: [String]) async {
    let center = UNUserNotificationCenter.current()

    // ★ 追加: プラン変更時の整合性確保
    // 両方の ID 名前空間を明示的にクリアしてから分岐する
    // Free → Pro / Pro → Free / struggles変更 のどれでも古い通知が残らない
    let freeIds = (0..<3).map { "free_nudge_\($0)" }
    // ★ 修正: pendingNotificationRequests() (iOS 15+ async API) で prefix-based 削除
    // 実際のID形式: PROBLEM_<type>_<hour>_<minute>_d<offset>
    let pendingRequests = await center.pendingNotificationRequests()
    let proIds = pendingRequests
        .filter { $0.identifier.hasPrefix("PROBLEM_") }
        .map { $0.identifier }
    center.removePendingNotificationRequests(withIdentifiers: freeIds + proIds)

    // ★ 追加: Free/Pro分岐（MainActor hop必須）
    let isEntitled = await MainActor.run { AppState.shared.subscriptionInfo.isEntitled }
    if !isEntitled {
        // Free ユーザー: FreePlanService に委譲（[String] を受け取り内部で変換）
        // ★ 注: FreePlanService.scheduleFreePlanNudges は同期メソッド（await不要）
        FreePlanService.shared.scheduleFreePlanNudges(struggles: problems)
        return
    }

    // Pro ユーザー: 既存の全スケジュール処理
    // ... 既存コードそのまま
}
```

#### 2. LLMNudgeService.swift への分岐追加

```swift
// ★ 変更箇所: fetchTodaysNudges() メソッド冒頭（注: メソッド名は "Today's" 複数形）

func fetchTodaysNudges() async throws -> [LLMGeneratedNudge] {
    // ★ 追加: Free ユーザーは LLM Nudge 無効（MainActor hop必須）
    let isEntitled = await MainActor.run { AppState.shared.subscriptionInfo.isEntitled }
    guard isEntitled else {
        print("[LLMNudgeService] Free user, skipping LLM fetch")
        return []  // 空配列を返す
    }

    // Pro ユーザー: 既存のLLM取得処理
    // ... 既存コードそのまま
}
```

#### 3. AppState.markOnboardingComplete() — tier判定を持たない（SSOT原則）

```swift
// ★ 変更箇所: markOnboardingComplete() メソッド末尾
// ★ SSOT原則: markOnboardingComplete() 自体は tier 判定しない
// ★ 通知スケジュールは呼び出し側（handlePaywallSuccess / handlePaywallDismissedAsFree）が責任を持つ

func markOnboardingComplete() {
    // ... 既存処理 ...
    // ★ 通知スケジュールはここでは行わない
    // ★ 理由: 購入直後は subscriptionInfo がまだ stale な可能性があるため
    // ★ 呼び出し側が「課金状態更新 → 通知再構成 → markOnboardingComplete」の順で実行する
}
```

**呼び出しシーケンス（購入経路）:**
```
handlePaywallSuccess()
    → appState.updateSubscriptionInfo(from: customerInfo)  // 1. SSOT更新
    → await ProblemNotificationScheduler.shared             // 2. Pro通知スケジュール
        .scheduleNotifications(for: struggles)
    → appState.markOnboardingComplete()                     // 3. 完了マーク
```

**呼び出しシーケンス（Free経路）:**
```
handlePaywallDismissedAsFree()
    → FreePlanService.shared.scheduleFreePlanNudges(...)    // 1. Free通知スケジュール
    → appState.markOnboardingComplete()                     // 2. 完了マーク
```

**呼び出しシーケンス（既存Proスキップ経路 — 復元等で既にisEntitled=trueのユーザー）:**
```
// ★ アプリ起動時に isEntitled==true かつ hasCompletedOnboarding==false の場合
// ★ ContentRouterView または bootstrapProfile() 内でキャッチ
completeOnboardingForExistingPro()
    → await ProblemNotificationScheduler.shared             // 1. Pro通知スケジュール
        .scheduleNotifications(for: struggles)
    → appState.markOnboardingComplete()                     // 2. 完了マーク
```
> ★ 重要: 全3経路（購入/Free dismiss/既存Proスキップ）で通知設定が保証されること。
> 受け入れ条件: 「オンボーディング完了後、通知が1件もスケジュールされていない状態にならない」

---

## 9.5 オンボーディングフロー変更パッチ（OnboardingStep enum + 遷移ロジック）

### OnboardingStep.swift の変更

```swift
// Before（現在のコード）
enum OnboardingStep: Int {
    case welcome       // 0
    case value         // 1
    case struggles     // 2
    case notifications // 3
}

// After（修正後）
enum OnboardingStep: Int {
    case welcome       // 0
    case struggles     // 1  ★ rawValue 変更（value 削除のため）
    case liveDemo      // 2  ★ 新規追加
    case notifications // 3
}

extension OnboardingStep {
    /// 旧RawValue（v1.6.1以前）から現在の enum へマップする。
    /// 現行実装（OnboardingStep.swift）との整合を保つ。
    ///
    /// ★ 呼び出し側（AppState）でバージョン判定を行い、この関数は legacy 値のみに適用する。
    /// v1.6.1 以降で保存された値は `OnboardingStep(rawValue:)` を直接使用する。
    static func migratedFromLegacyRawValue(_ rawValue: Int) -> OnboardingStep {
        // v1.6.1以前からの移行マッピング
        // ★ 現行ユーザー保護: v1.6.0 では rawValue=3 が `.notifications`
        // ★ 新rawValue（2=.liveDemo, 3=.notifications）はこの関数を通さない
        switch rawValue {
        case 0: return .welcome
        case 1: return .struggles       // ★ 旧 value/account → struggles へ（value 削除）
        case 2: return .struggles       // ★ 旧 struggles → struggles（legacy only）
        case 3: return .notifications   // ★ 修正: v1.6.0 の .notifications=3 を保護（旧 source ユーザーは稀、現行優先）
        case 5, 6, 7, 8: return .struggles  // ★ 旧 name/gender/age/ideals → struggles（未実施防止）
        case 4: return .notifications   // ★ v1.6.0の.att → notifications（ATT削除後）
        case 9, 10: return .notifications // ★ 旧 habitSetup/notifications → notifications
        case 11, 12: return .notifications // ★ 旧 att/alarmkit → notifications
        default:
            return .welcome
        }
    }
}

```

#### 4. AppState.swift のバージョン付き migration（必須パッチ — 既存キー互換 + @Published維持）

```swift
// ★ 必須実装: rawValue衝突を防ぐバージョンフラグ方式
// ★ 既存キー: "com.anicca.onboardingStep"（変更しない）
// ★ 新規キー: "com.anicca.onboardingStepVersion"（初期値0 = legacy扱い）
// ★ 重要: @Published private(set) var onboardingStep は維持し、init() で一度だけ migration

// --- 変更1: 新規バージョンキーを追加（line 63付近） ---
private let onboardingStepVersionKey = "com.anicca.onboardingStepVersion"
private static let currentOnboardingVersion = 2  // v1.6.1で2に変更

// --- 変更2: init() 内の onboardingStep 初期化を修正（line 79-85） ---
// Before:
//     let rawValue = defaults.integer(forKey: onboardingStepKey)
//     self.onboardingStep = OnboardingStep.migratedFromLegacyRawValue(rawValue)

// After:
if defaults.bool(forKey: onboardingKey) {
    let rawValue = defaults.integer(forKey: onboardingStepKey)
    let savedVersion = defaults.integer(forKey: onboardingStepVersionKey)

    if savedVersion >= Self.currentOnboardingVersion {
        // ★ v1.6.1 以降: 新rawValueをそのまま使用
        self.onboardingStep = OnboardingStep(rawValue: rawValue) ?? .welcome
    } else {
        // ★ legacy (savedVersion=0 or 1): migration関数を通す
        self.onboardingStep = OnboardingStep.migratedFromLegacyRawValue(rawValue)
    }
} else {
    defaults.removeObject(forKey: onboardingStepKey)
    self.onboardingStep = .welcome
}

// --- 変更3: setOnboardingStep() でバージョンフラグを更新（line 170付近） ---
func setOnboardingStep(_ step: OnboardingStep) {
    onboardingStep = step
    defaults.set(step.rawValue, forKey: onboardingStepKey)
    // ★ バージョンフラグを常に更新（新rawValue体系を使用中であることを記録）
    defaults.set(Self.currentOnboardingVersion, forKey: onboardingStepVersionKey)
}
```

> ★ 注: `@Published private(set) var onboardingStep: OnboardingStep` は維持。計算プロパティにしない。
> init() での一回限りの migration により、既存ユーザーのデータを壊さずに新rawValue体系に移行。

#### 5. MyPathTabView.swift への DEBUG UI 追加（Maestro E2E 検証用）

```swift
// ★ 追加: DEBUG セクション内に pending free notification count 表示
// 目的: Maestro E2E #8 で購入後に free_nudge_* が 0 件であることを assert するため

#if DEBUG
// --- debugStateInjectionSection 内に追加 ---
HStack {
    Text("📬")
    Text("Pending Free Nudges")
        .font(.subheadline)
        .foregroundStyle(.cyan)
    Spacer()
    Text("\(freePendingCount)")
        .font(.caption2)
        .foregroundStyle(.secondary)
}
.padding(.vertical, 8)
.padding(.horizontal, 12)
.background(Color.cyan.opacity(0.1))
.clipShape(RoundedRectangle(cornerRadius: 8))
.accessibilityIdentifier("debug_free_nudge_pending_count_\(freePendingCount)")  // ★ Maestro用ID

// --- @State 追加 ---
@State private var freePendingCount: Int = 0

// --- .onAppear または .task に追加 ---
.task {
    let center = UNUserNotificationCenter.current()
    let pending = await center.pendingNotificationRequests()
    freePendingCount = pending.filter { $0.identifier.hasPrefix("free_nudge_") }.count
}
#endif
```

> ★ 注: `accessibilityIdentifier("debug_free_nudge_pending_count_\(count)")` により、Maestro から `id: "debug_free_nudge_pending_count_0"` で 0 件を assert 可能。

### OnboardingFlowView.swift の遷移ロジック変更

```swift
// Before（現在のコード - 14-24行目）
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
    }
}

// After（修正後）
Group {
    switch step {
    case .welcome:
        WelcomeStepView(next: advance)
    case .struggles:
        StrugglesStepView(next: advance)
    case .liveDemo:
        DemoNudgeStepView(next: advance)  // ★ 新規画面
    case .notifications:
        NotificationPermissionStepView(next: advance)
    }
}

// advance() メソッドの変更
private func advance() {
    switch step {
    case .welcome:
        AnalyticsManager.shared.track(.onboardingWelcomeCompleted)
        step = .struggles  // ★ value をスキップ
    case .struggles:
        AnalyticsManager.shared.track(.onboardingStrugglesCompleted)
        step = .liveDemo   // ★ 新規: LIVE DEMO へ
    case .liveDemo:
        AnalyticsManager.shared.track(.onboardingLiveDemoCompleted)  // ★ 新規イベント
        step = .notifications
    case .notifications:
        AnalyticsManager.shared.track(.onboardingNotificationsCompleted)
        completeOnboarding()
        return
    }
    appState.setOnboardingStep(step)
}
```

### AnalyticsManager.swift への新規イベント追加

```swift
// ★ 追加するイベント
enum AnalyticsEvent: String {
    // ... 既存イベント ...
    case onboardingLiveDemoCompleted = "onboarding_live_demo_completed"  // ★ 新規
    case onboardingPaywallDismissedFree = "onboarding_paywall_dismissed_free"  // ★ 新規
}
```

### 削除対象ファイル

| ファイル | 理由 |
|---------|------|
| `ValueStepView.swift` | LIVE DEMO に置き換え |

### 新規作成ファイル

| ファイル | 目的 |
|---------|------|
| `DemoNudgeStepView.swift` | LIVE DEMO NUDGE 体験画面 |

---

## 10. 実装計画

### Phase 1: オンボーディング更新（P0）

| # | タスク | 工数 |
|---|--------|------|
| 1.1 | `ValueStepView` 削除 | 15分 |
| 1.2 | `DemoNudgeStepView` 新規作成 | 2時間 |
| 1.3 | オンボーディングフロー順序変更 | 30分 |

### Phase 2: Paywall更新（P0）

| # | タスク | 工数 |
|---|--------|------|
| 2.1 | `displayCloseButton: true` に修正 | 5分 |
| 2.2 | Paywall閉じ時のFree Plan遷移実装 | 1時間 |
| 2.3 | Paywall閉じ後のレビューリクエスト追加 | 30分 |

### Phase 3: Upgrade Trigger実装（P0）

| # | タスク | 工数 |
|---|--------|------|
| 3.1 | 3回目/7回目のPaywall表示ロジック追加 | 1時間 |
| 3.2 | 既存のレビューリクエストコード削除 | 15分 |

### Phase 4: Free Plan実装（P0）

| # | タスク | 工数 |
|---|--------|------|
| 4.1 | `FreePlanService.swift` 新規作成 | 2時間 |
| 4.2 | 3通知/日のスケジュールロジック | 1時間 |
| 4.3 | 問題ローテーションロジック | 1時間 |

### Phase 5: テスト（P0）

| # | タスク | 工数 |
|---|--------|------|
| 5.1 | Unit Test 作成 | 2時間 |
| 5.2 | Maestro E2Eテスト更新 | 2時間 |
| 5.3 | 実機テスト | 1時間 |
| 5.4 | Mixpanel イベント追加 | 1時間 |

---

## 10.5 テストマトリックス（TDD用）

### Unit Test 対象ファイル

| # | テストファイル | テスト対象 |
|---|---------------|-----------|
| 1 | `FreePlanServiceTests.swift` | FreePlanService |
| 2 | `UpgradeTriggerTests.swift` | 3回目/7回目トリガー判定 |
| 3 | `SubscriptionTierTests.swift` | Free/Pro分岐 |
| 4 | `PaywallDismissFlowTests.swift` | Paywall閉じ時フロー |
| 5 | `OnboardingStepMigrationTests.swift` | OnboardingStep rawValue 移行 + 新遷移フロー |
| 6 | `LLMNudgeServiceTests.swift` | LLMNudgeService Free/Pro ガード |

### テストケース一覧（Given/When/Then形式）

#### FreePlanServiceTests.swift

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_problemForSlot_emptyProblems_returnsNil` | `problems = []` | `problemForSlot(day:1, slot:0, problems:[])` | `nil` を返す（クラッシュしない） |
| 2 | `test_problemForSlot_singleProblem_returnsSame` | `problems = [.stayingUpLate]` | `problemForSlot(day:1, slot:0, problems:problems)` | `.stayingUpLate` を返す |
| 3 | `test_problemForSlot_rotates_correctly` | `problems = [.anxiety, .rumination, .procrastination]` | `problemForSlot(day:1, slot:0-2)` | `anxiety, rumination, procrastination` の順 |
| 4 | `test_scheduleFreePlanNudges_emptyProblems_noSchedule` | `problems = []` | `scheduleFreePlanNudges(problems:[])` | 通知が0件（クラッシュしない） |
| 5 | `test_scheduleFreePlanNudges_createsThreeNotifications` | `problems = [.anxiety]` | `scheduleFreePlanNudges(problems:problems)` | 3件の通知がスケジュール |
| 6 | `test_nextScheduledNudgeTimes_returnsCorrectSlots` | 現在時刻 = 7:00 AM | `nextScheduledNudgeTimes()` | `[8:00, 12:30, 20:00]` |
| 7 | `test_nextScheduledNudgeTimes_afterAllSlots_returnsEmpty` | 現在時刻 = 21:00 | `nextScheduledNudgeTimes()` | `[]` |
| 8 | `test_scheduleNotifications_clearsProIds_whenFree` | `isEntitled=false`、既存の `PROBLEM_*` 通知あり | `scheduleNotifications(for:)` | `PROBLEM_*` が削除される、`free_nudge_*` のみ残る |
| 9 | `test_scheduleNotifications_clearsFreeIds_whenPro` | `isEntitled=true`、既存の `free_nudge_*` 通知あり | `scheduleNotifications(for:)` | `free_nudge_*` が削除される、`PROBLEM_*` のみ残る |
| 10 | `test_scheduleNotifications_clearsAllProblemsIds` | 旧struggles=[.anxiety, .rumination]、新struggles=[.procrastination] | `scheduleNotifications(for:)` | 全 `PROBLEM_*` prefix通知が削除される（prefix-based削除） |
| 11 | `test_rescheduleIfNeeded_differentDay_reschedules` | `lastScheduledDay=100`、`currentDay=101` | `rescheduleIfNeeded(problems:)` | `scheduleFreePlanNudges` が呼ばれる |
| 12 | `test_rescheduleIfNeeded_sameDay_noOp` | `lastScheduledDay=100`、`currentDay=100` | `rescheduleIfNeeded(problems:)` | `scheduleFreePlanNudges` が呼ばれない |
| 13 | `test_scheduleFreePlanNudges_usesNonRepeating` | `problems=[.anxiety]` | `scheduleFreePlanNudges(problems:)` | `trigger.repeats = false`（日替わり対応） |
| 14 | `test_scheduleFreePlanNudges_afterLastSlot_schedulesTomorrow` | `problems=[.anxiety]`、現在時刻 = 21:00（全スロット過去） | `scheduleFreePlanNudges(problems:)` | 3件とも翌日の日付でスケジュール（8:00, 12:30, 20:00） |
| 15 | `test_rescheduleIfNeeded_dayBoundary_keepsThreeFutureNudges` | `problems=[.anxiety, .rumination]`、深夜0:05（日付変更直後） | `rescheduleIfNeeded(problems:)` | 新しい日付で3件スケジュール、合計3件の未来通知が存在 |
| 16 | `test_scheduleFreePlanNudges_afterLastSlot_usesTomorrowRotationIndex` | `problems=[.anxiety, .rumination]`、現在時刻 = 21:00（全スロット過去）、today=dayOfYear 100 | `scheduleFreePlanNudges(problems:)` | rotationDay=101（翌日）を使用してproblemForSlot計算、翌日分のローテーションが適用される |
| 17 | `test_scheduleFreePlanNudges_dstSpringForward_23hDay` | `problems=[.anxiety]`、DST開始日（23時間日）、TZ=America/New_York | `scheduleFreePlanNudges(problems:)` | 3件の通知が正しい時刻でスケジュール（2:00AM→3:00AMスキップでもスロットが維持） |
| 18 | `test_scheduleFreePlanNudges_dstFallBack_25hDay` | `problems=[.anxiety]`、DST終了日（25時間日）、TZ=America/New_York | `scheduleFreePlanNudges(problems:)` | 3件の通知が重複なくスケジュール |
| 19 | `test_rescheduleIfNeeded_timezoneChange_reschedules` | `lastScheduledDay=100`（JST）、端末TZ変更でcurrentDay=99（PST） | `rescheduleIfNeeded(problems:)` | 日付差異を検知して再スケジュール |

> ★ DST/TZテストは `Calendar`, `TimeZone`, `UNUserNotificationCenter`, `UserDefaults` を全て注入可能にして検証。`FreePlanService.init(calendar:nowProvider:notificationCenter:defaults:)` で全依存を注入。

#### UpgradeTriggerTests.swift

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_thirdTap_freeUser_showsPaywall` | `count=2, isEntitled=false` | `handleNudgeCardCompletion()` | `showUpgradePaywall = true` |
| 2 | `test_thirdTap_proUser_noPaywall` | `count=2, isEntitled=true` | `handleNudgeCardCompletion()` | `showUpgradePaywall = false` |
| 3 | `test_seventhTap_freeUser_showsPaywall` | `count=6, isEntitled=false` | `handleNudgeCardCompletion()` | `showUpgradePaywall = true` |
| 4 | `test_eighthTap_freeUser_noPaywall` | `count=7, isEntitled=false` | `handleNudgeCardCompletion()` | `showUpgradePaywall = false` |
| 5 | `test_firstTap_freeUser_noPaywall` | `count=0, isEntitled=false` | `handleNudgeCardCompletion()` | `showUpgradePaywall = false` |
| 6 | `test_upgradePurchase_withOffering_reschedulesNotifications` | Free、`cachedOffering` あり → 購入完了 | `onPurchaseCompleted` | `free_nudge_*` 削除、`PROBLEM_*` で再スケジュール |
| 7 | `test_upgradeRestore_withOffering_reschedulesNotifications` | Free、`cachedOffering` あり → 復元完了 | `onRestoreCompleted` | `free_nudge_*` 削除、`PROBLEM_*` で再スケジュール |
| 8 | `test_upgradePurchase_withoutOffering_reschedulesNotifications` | Free、`cachedOffering` なし → 購入完了 | `onPurchaseCompleted` | `free_nudge_*` 削除、`PROBLEM_*` で再スケジュール |
| 9 | `test_upgradeRestore_withoutOffering_reschedulesNotifications` | Free、`cachedOffering` なし → 復元完了 | `onRestoreCompleted` | `free_nudge_*` 削除、`PROBLEM_*` で再スケジュール |

> ★ 注: #6-9 は `cachedOffering` 有/無 × 購入/復元 の4経路を網羅。全経路が同一の `handleUpgradePurchase(customerInfo:)` に到達することを検証。

#### SubscriptionTierTests.swift（SSOT検証）

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_isEntitled_proActive_returnsTrue` | `plan=.pro, status="active"` | `subscriptionInfo.isEntitled` | `true` |
| 2 | `test_isEntitled_free_returnsFalse` | `plan=.free, status="active"` | `subscriptionInfo.isEntitled` | `false` |
| 3 | `test_isEntitled_proExpired_returnsFalse` | `plan=.pro, status="expired"` | `subscriptionInfo.isEntitled` | `false` |
| 4 | `test_isEntitled_grace_returnsTrue` | `plan=.grace, status="active"` | `subscriptionInfo.isEntitled` | `true`（grace期間中はPro扱い） |

> ★ 注: テストは `SubscriptionInfo` の computed property を直接検証。外部APIは不要。

#### PaywallDismissFlowTests.swift

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_dismissPaywall_schedulesFreePlanNudges` | `isEntitled=false, problems=[.anxiety]` | `handlePaywallDismissedAsFree()` | `FreePlanService.scheduleFreePlanNudges` が呼ばれる |
| 2 | `test_dismissPaywall_marksOnboardingComplete` | オンボーディング中 | `handlePaywallDismissedAsFree()` | `appState.isOnboardingComplete == true` |
| 3 | `test_dismissPaywall_requestsReview_firstTime` | `hasRequestedReview=false` | `handlePaywallDismissedAsFree()` | `SKStoreReviewController.requestReview` が呼ばれる |
| 4 | `test_dismissPaywall_noReview_alreadyRequested` | `hasRequestedReview=true` | `handlePaywallDismissedAsFree()` | `SKStoreReviewController.requestReview` が呼ばれない |
| 5 | `test_purchasePaywall_requestsReview_firstTime` | `hasRequestedReview=false` | `handlePaywallSuccess(customerInfo:)` | `SKStoreReviewController.requestReview` が呼ばれる |
| 6 | `test_purchasePaywall_noReview_alreadyRequested` | `hasRequestedReview=true` | `handlePaywallSuccess(customerInfo:)` | `SKStoreReviewController.requestReview` が呼ばれない |
| 7 | `test_onDismiss_afterPurchase_doesNotScheduleFreePlan` | `didPurchaseOnPaywall=true`、購入完了後に `fullScreenCover(onDismiss:)` 発火 | ガードで分岐 | `scheduleFreePlanNudges` が呼ばれない（★ 購入成功時はFree処理スキップ） |
| 8 | `test_onboardingPurchase_withOffering_updatesSSoT` | `cachedOffering` あり → Onboarding購入完了 | `handlePaywallSuccess(customerInfo:)` | `appState.subscriptionInfo.isEntitled == true`、通知再構成済み |
| 9 | `test_onboardingPurchase_withoutOffering_updatesSSoT` | `cachedOffering` なし → Onboarding購入完了 | `handlePaywallSuccess(customerInfo:)` | `appState.subscriptionInfo.isEntitled == true`、通知再構成済み |
| 10 | `test_onboardingRestore_withOffering_updatesSSoT` | `cachedOffering` あり → Onboarding復元完了 | `onRestoreCompleted` | `appState.subscriptionInfo.isEntitled == true`、通知再構成済み |
| 11 | `test_onboardingRestore_withoutOffering_updatesSSoT` | `cachedOffering` なし → Onboarding復元完了 | `onRestoreCompleted` | `appState.subscriptionInfo.isEntitled == true`、通知再構成済み |

> ★ 注: 購入経路 (`handlePaywallSuccess`) と X 閉じ経路 (`handlePaywallDismissedAsFree`) の両方でレビューリクエストが1回だけ呼ばれることを検証
> ★ 追記: #7 は購入成功後に `fullScreenCover(onDismiss:)` が発火しても Free Plan 処理が実行されないことを検証（`didPurchaseOnPaywall` フラグ方式）
> ★ 追記: #8-11 は Onboarding Paywall の `cachedOffering` 有/無 × 購入/復元 の4経路を網羅。Upgrade側 (#6-9 in UpgradeTriggerTests) と合わせて計8経路を全カバー。

#### OnboardingStepMigrationTests.swift

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_migration_raw0_returnsWelcome` | 旧 rawValue = 0 | `migratedFromLegacyRawValue(0)` | `.welcome` を返す |
| 2 | `test_migration_raw1_returnsStruggles` | 旧 rawValue = 1（旧 value） | `migratedFromLegacyRawValue(1)` | `.struggles` を返す（value 削除のため） |
| 3 | `test_migration_raw2_returnsStruggles` | 旧 rawValue = 2（旧 struggles） | `migratedFromLegacyRawValue(2)` | `.struggles` を返す（★ 新.liveDemoと衝突するため明示検証） |
| 4 | `test_migration_raw3_returnsNotifications` | rawValue = 3（v1.6.0 の .notifications） | `migratedFromLegacyRawValue(3)` | `.notifications` を返す（★ 現行ユーザー保護優先） |
| 5 | `test_migration_raw4_returnsNotifications` | 旧 rawValue = 4（v1.6.0の.att） | `migratedFromLegacyRawValue(4)` | `.notifications` を返す（ATT削除後） |
| 6 | `test_migration_raw5_returnsStruggles` | 旧 rawValue = 5（旧 name） | `migratedFromLegacyRawValue(5)` | `.struggles` を返す（struggles未実施防止） |
| 7 | `test_migration_raw6_returnsStruggles` | 旧 rawValue = 6（旧 gender） | `migratedFromLegacyRawValue(6)` | `.struggles` を返す |
| 8 | `test_migration_raw7_returnsStruggles` | 旧 rawValue = 7（旧 age） | `migratedFromLegacyRawValue(7)` | `.struggles` を返す |
| 9 | `test_migration_raw8_returnsStruggles` | 旧 rawValue = 8（旧 ideals） | `migratedFromLegacyRawValue(8)` | `.struggles` を返す |
| 10 | `test_migration_raw9to12_returnsNotifications` | 旧 rawValue = 9...12 | `migratedFromLegacyRawValue(9)` | `.notifications` を返す |
| 11 | `test_migration_rawNegative_returnsWelcome` | 旧 rawValue = -1（不正値） | `migratedFromLegacyRawValue(-1)` | `.welcome` を返す（安全側） |
| 12 | `test_advance_welcome_goesToStruggles` | `step = .welcome` | `advance()` | `step = .struggles` |
| 13 | `test_advance_struggles_goesToLiveDemo` | `step = .struggles` | `advance()` | `step = .liveDemo` |
| 14 | `test_advance_liveDemo_goesToNotifications` | `step = .liveDemo` | `advance()` | `step = .notifications` |
| 15 | `test_advance_notifications_completesOnboarding` | `step = .notifications` | `advance()` | `completeOnboarding()` が呼ばれる |
| 16 | `test_migration_newVersion_raw2_keepsLiveDemo` | `savedVersion=2`、rawValue=2（新 .liveDemo） | AppState onboardingStep getter | `.liveDemo` を返す（migratedFromLegacyRawValue を通さない） |
| 17 | `test_migration_newVersion_raw3_keepsNotifications` | `savedVersion=2`、rawValue=3（新 .notifications） | AppState onboardingStep getter | `.notifications` を返す（migratedFromLegacyRawValue を通さない） |

> ★ 注: 旧バージョン（v1.6.0以前）からのユーザーが正しく移行されることを検証。特に rawValue 5-8（旧 name/gender/age/ideals）は `.struggles` にマップし、struggles 未実施のまま notifications へ直行しないことを保証。
> ★ 追記: #16, #17 は v1.6.1 以降のユーザー（savedVersion >= 2）が新 rawValue を正しく保持することを検証。バージョンフラグ方式の正当性を担保。

#### LLMNudgeServiceTests.swift

| # | テストケース | Given | When | Then |
|---|-------------|-------|------|------|
| 1 | `test_fetchTodaysNudges_freeUser_returnsEmpty` | `isEntitled = false` | `fetchTodaysNudges()` | 空配列 `[]` を返す |
| 2 | `test_fetchTodaysNudges_freeUser_noNetworkCall` | `isEntitled = false`、Mock URLSession | `fetchTodaysNudges()` | ネットワークリクエストが 0 件（コスト発生なし） |
| 3 | `test_fetchTodaysNudges_proUser_callsAPI` | `isEntitled = true`、Mock URLSession | `fetchTodaysNudges()` | `/mobile/nudge/today` へリクエスト発生 |
| 4 | `test_fetchTodaysNudges_proUser_returnsNudges` | `isEntitled = true`、Mock API が Nudge 返却 | `fetchTodaysNudges()` | 非空配列を返す |
| 5 | `test_fetchTodaysNudges_proUser_error_throws` | `isEntitled = true`、Mock API がエラー | `fetchTodaysNudges()` | エラーを throw |

> ★ 注: Free ユーザーは LLM API を呼ばない（APIコスト節約）。`isEntitled` ガードは `fetchTodaysNudges()` 冒頭で早期リターン。

### Maestro E2Eテストシナリオ（Given/When/Then形式）

| # | ファイル | Given | When | Then |
|---|---------|-------|------|------|
| 1 | `maestro/onboarding/01-onboarding-free.yaml` | 新規インストール、オンボーディング完了、Paywall表示中 | Xボタンをタップ | Paywall閉じ、メイン画面（MyPathTab）表示、Free Plan通知がスケジュール済み |
| 2 | `maestro/onboarding/02-onboarding-pro.yaml` | 新規インストール、オンボーディング完了、Paywall表示中 | 購入ボタンをタップ | 購入フロー完了、メイン画面表示、Pro状態 |
| 3 | `maestro/onboarding/03-live-demo.yaml` | オンボーディング中、struggles選択完了 | 次へ進む | LIVE DEMO画面表示、Nudgeカードがアニメーション（0.8秒）、PRIMARYタップでnotificationsへ |
| 4 | `maestro/upgrade/01-third-tap-paywall.yaml` | Free ユーザー、`nudgeCardCompletedCount = 2` | 3回目PRIMARYタップ | 300ms以内にPaywall表示 |
| 5 | `maestro/upgrade/02-seventh-tap-paywall.yaml` | Free ユーザー、`nudgeCardCompletedCount = 6` | 7回目PRIMARYタップ | 300ms以内にPaywall表示 |
| 6 | `maestro/upgrade/03-eighth-plus-no-paywall.yaml` | Free ユーザー、`nudgeCardCompletedCount = 7` | 8回目PRIMARYタップ | Paywall表示なし、通常フロー継続 |
| 7 | `maestro/upgrade/04-subscribe-button-paywall.yaml` | Free ユーザー、メイン画面表示中 | Subscribeボタンタップ | 即座にPaywall表示 |
| 8 | `maestro/onboarding/04-purchase-dismiss-no-free.yaml` | 新規インストール、オンボーディング完了、Paywall表示中 | 購入完了後にPaywallが閉じる | Pro状態維持、DEBUG UI で `free_nudge_*` pending count = 0 を確認 |

> ★ 注: #8 は購入成功後に `onDismiss` が発火しても Free Plan 処理がスキップされることを E2E で検証。`didPurchaseOnPaywall` フラグ方式の退行防止。
> ★ 検証方法: DEBUG ビルドでのみ表示される pending free notification count UI 要素を assert（`debug_free_nudge_pending_count_0`）

#### Maestro #8 YAML 断片（04-purchase-dismiss-no-free.yaml）

```yaml
appId: ai.anicca.app.ios
tags:
  - smokeTest
  - onboarding
  - paywall
---
# 前提: 新規インストール、オンボーディング完了、Paywall表示中

# 1. Paywall で購入（sandbox purchase flow）
- tapOn:
    text: "1週間無料で始める"  # ローカライズ依存、実際のボタンテキストに合わせる

# 2. sandbox purchase completion（StoreKit Testing）
- waitForAnimationToEnd

# 3. Paywall が閉じてメイン画面へ遷移
- assertVisible:
    id: "mypath_tab_view"

# 4. ★ DEBUG UI で free_nudge_* pending count = 0 を検証
- assertVisible:
    id: "debug_free_nudge_pending_count_0"
```

> ★ 注: sandbox purchase はシミュレータの StoreKit Testing Configuration で設定。実際のテストでは `maestro studio` で確認しながら調整。

---

## 11. 受け入れ条件（検証可能な挙動ベース）

### 機能受け入れ条件

| # | 機能 | 受け入れ条件 | 検証方法 |
|---|------|------------|---------|
| 1 | Soft Paywall | Paywall右上にXボタンが表示される | Maestro E2E |
| 2 | Xボタン閉じ | Xタップ後、300ms以内にメイン画面へ遷移 | Maestro E2E |
| 3 | Free Plan通知 | Free ユーザーに8:00, 12:30, 20:00の3通知がスケジュールされる | Unit Test |
| 4 | 問題ローテーション | 複数問題選択時、日替わりで異なる問題のNudgeが届く | Unit Test |
| 5 | 3回目トリガー | Free ユーザーが3回目PRIMARYタップ後、300ms以内にPaywallが表示 | Unit Test + E2E |
| 6 | 7回目トリガー | Free ユーザーが7回目PRIMARYタップ後、300ms以内にPaywallが表示 | Unit Test |
| 7 | 8回目以降 | 8回目以降はPaywall表示なし | Unit Test |
| 8 | Pro スキップ | Pro ユーザーはトリガー無視（Paywall表示なし） | Unit Test |
| 9 | レビューリクエスト | Paywall閉じ直後（購入 or X）に1回だけ表示 | Unit Test |
| 10 | LIVE DEMO | struggles後にNudgeカードがアニメーション表示（0.8秒） | Maestro E2E |
| 11 | 空問題ガード | 問題未選択時もクラッシュしない | Unit Test |

### リリース判定基準

| # | 基準 | 必須/任意 |
|---|------|---------|
| 1 | 全Unit Test PASS | 必須 |
| 2 | 全Maestro E2E PASS | 必須 |
| 3 | 実機で手動確認完了 | 必須 |
| 4 | クラッシュログなし（Crashlytics） | 必須 |
| 5 | Mixpanelイベント正常送信確認 | 必須 |

## 11.5 成功指標（KPI）

| 指標 | 現状 | 目標（1週間後） | 測定方法 |
|------|------|----------------|---------|
| Paywall到達率 | 100% | 100%（維持） | Mixpanel |
| Paywall閉じ率（Free選択） | N/A | 60-70% | Mixpanel |
| 試用開始率 | 0% | 10-15% | RevenueCat |
| Free→Pro転換率 | N/A | 5-10% | RevenueCat |
| Day 7リテンション（Free） | N/A | 30% | Mixpanel |

**なぜこの目標か:**
- Soft paywall = 2-5%コンバージョンが業界平均
- 10-15%試用開始を目指す（現状0%からの改善）
- Free→Proは後でデータを見て最適化

---

## 12. 出典一覧

### Soft Paywall戦略

1. [RevenueCat: Freemium drives 3x more trial starts](https://www.revenuecat.com/state-of-subscription-apps-2025)
2. [Adapty: Freemium App Monetization](https://adapty.io/blog/freemium-app-monetization/)
3. [Headspace Case Study: 35% free-to-trial, 42% trial-to-paid](https://www.marketingcareers.ai/p/headspace)

### オンボーディング最適化

4. [UXCam - App Onboarding Guide 2025](https://uxcam.com/blog/10-apps-with-great-user-onboarding/)
5. [Medium - 200% Conversion Increase](https://medium.com/@ridhisingh/how-we-improved-our-onboarding-funnel-increased-conversions-by-200-9a106b238247)

### Free Tier設計

6. [10-70-20 Rule: Feature allocation](https://adapty.io/blog/freemium-app-monetization/)
7. [AppBot: Push Notification Best Practices 2026](https://appbot.co/blog/push-notifications-best-practices)

### RevenueCat/Superwall実装

8. [Superwall: Presenting Paywalls](https://superwall.com/docs/ios/quickstart/feature-gating)
9. [RevenueCat: Entitlements](https://www.revenuecat.com/docs/getting-started/entitlements)
10. [Superwall: Custom Paywall Presentation](https://www.superwall.com/blog/custom-paywall-presentation-in-ios-with-the-superwall-sdk/)

### レビューリクエスト

11. [MagicBell - In-App Notification Design](https://www.magicbell.com/blog/in-app-notification-design)
12. [Adapty - Mobile App Onboarding](https://adapty.io/blog/mobile-app-onboarding/)

---

## 13. 最終決定チェックリスト

| 決定事項 | 決定内容 | 確認 |
|---------|---------|------|
| Paywall種類 | **Soft（Xボタンで閉じれる）** | ✅ |
| 月額料金 | $9.99（1週間トライアル） | ✅ |
| 年額料金 | 今は追加しない（後で$29.99） | ✅ |
| Free Plan | 3通知/日、ルールベースのみ | ✅ |
| 通知配信時間 | 8:00, 12:30, 20:00 | ✅ |
| 複数問題対応 | 日替わりローテーション | ✅ |
| オンボーディング | welcome → struggles → LIVE DEMO → notifications → paywall | ✅ |
| Value画面 | **削除**（LIVE DEMOで置き換え） | ✅ |
| LIVE DEMO | アプリ内カードアニメーション（カウントダウンなし） | ✅ |
| カード内ボタン順序 | PRIMARY（上）→ 👍/👎（下） | ✅ |
| Xボタン実装 | Dashboard設定 + コード `displayCloseButton: true` | ✅ |
| Paywall表示 | オンボーディング、Subscribeボタン、3回目、7回目 | ✅ |
| レビューリクエスト | **Paywall閉じた直後**（3回目タップから移動） | ✅ |

---

**この文書に基づいて実装を開始する。不明点なし。決定完了。**
