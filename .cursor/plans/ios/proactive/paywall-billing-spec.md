# Paywall・課金・レビュー 実装仕様書

## 背景

Aniccaは「Proactive Agent」へと進化し、音声セッション（Talk Session）から**問題ベースの通知（Nudge）**を中心としたプロダクトに変わった。

これに伴い、課金モデルとPaywall表示タイミングを全面的に見直す必要がある。

### 従来の課金モデル（レガシー）
- 音声セッション分数で課金（Free: 30分/月、Pro: 300分/月）
- セッション完了時（1回目、3回目）にPaywall表示
- 音声分上限到達時（quota_exceeded）にPaywall表示

### 新しい課金モデル
- **通知回数で課金**（Free: 10回/月、Pro: 無制限）
- NudgeCard完了回数に基づいてPaywall・レビュー表示
- 通知自体が10回/月で停止（Freeプラン）

---

## As-Is（現状）

### SuperwallManager.swift

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case sessionComplete1 = "session_complete_1"     // ← 削除対象
    case sessionComplete3 = "session_complete_3"     // ← 削除対象
    case campaignAppLaunch = "campaign_app_launch"   // ← 削除対象
    case profilePlanTap = "profile_plan_tap"
    case quotaExceeded = "quota_exceeded"            // ← 削除対象
}
```

### AppState.swift

- `subscriptionHold`, `quotaHoldReason` は音声セッション分上限用
- NudgeCard完了回数、月間通知回数のカウントは**存在しない**
- レビューリクエスト済みフラグは**存在しない**

### NudgeCardView.swift

- アクションボタン押下後の処理は`onPositiveAction()`コールバックのみ
- Paywall表示やレビューリクエストのロジックは**存在しない**

### ProblemNotificationScheduler.swift

- 通知回数の制限ロジックは**存在しない**
- 月間カウントのリセットロジックは**存在しない**

---

## To-Be（あるべき姿）

### 1. SuperwallPlacement

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"   // 既存
    case nudgeCardComplete5 = "nudge_card_complete_5" // 新規
    case nudgeCardComplete10 = "nudge_card_complete_10" // 新規（月上限）
    case profilePlanTap = "profile_plan_tap"          // 既存
}
```

### 2. Paywall・レビュー表示タイミング

| NudgeCard完了回数 | 表示するもの | 条件 |
|------------------|-------------|------|
| 1回目 | なし | - |
| 2回目 | なし | - |
| **3回目** | **レビューリクエスト** | `hasRequestedReview == false` |
| 4回目 | なし | - |
| **5回目** | **Paywall** | `plan != .pro` |
| 6〜9回目 | なし | - |
| **10回目** | **Paywall**（月上限） | `plan != .pro` |
| 11回目以降 | なし（通知自体が来ない） | - |

### 3. 通知回数制限

| プラン | 月間通知回数 | 上限到達後 |
|-------|------------|----------|
| Free | 10回/月 | 通知がスケジュールされない |
| Pro | 無制限 | - |

### 4. 月初リセット

- アプリ起動時に月が変わっていたら`monthlyNudgeCount`を0にリセット

---

## 実装パッチ

### Patch 1: AppState.swift

**追加するプロパティ:**

```swift
// MARK: - Nudge Card / Paywall / Review

/// NudgeCard完了回数（累計、レビュー・Paywall表示判定用）
@Published private(set) var nudgeCardCompletedCount: Int = 0

/// 月間通知受信回数（通知制限用、月初リセット）
@Published private(set) var monthlyNudgeCount: Int = 0

/// レビューリクエスト済みフラグ
@Published private(set) var hasRequestedReview: Bool = false

// UserDefaultsキー
private let nudgeCardCompletedCountKey = "com.anicca.nudgeCardCompletedCount"
private let monthlyNudgeCountKey = "com.anicca.monthlyNudgeCount"
private let hasRequestedReviewKey = "com.anicca.hasRequestedReview"
private let lastNudgeResetMonthKey = "com.anicca.lastNudgeResetMonth"
private let lastNudgeResetYearKey = "com.anicca.lastNudgeResetYear"
```

**追加するメソッド:**

```swift
// MARK: - Nudge Card / Paywall / Review Methods

/// NudgeCard完了回数をインクリメント
func incrementNudgeCardCompletedCount() {
    nudgeCardCompletedCount += 1
    defaults.set(nudgeCardCompletedCount, forKey: nudgeCardCompletedCountKey)
}

/// 月間通知回数をインクリメント
func incrementMonthlyNudgeCount() {
    monthlyNudgeCount += 1
    defaults.set(monthlyNudgeCount, forKey: monthlyNudgeCountKey)
}

/// レビューリクエスト済みとしてマーク
func markReviewRequested() {
    hasRequestedReview = true
    defaults.set(true, forKey: hasRequestedReviewKey)
}

/// 月間通知回数をリセット
func resetMonthlyNudgeCount() {
    monthlyNudgeCount = 0
    defaults.set(0, forKey: monthlyNudgeCountKey)
}

/// Nudge受信可能かどうか
var canReceiveNudge: Bool {
    if subscriptionInfo.plan == .pro { return true }
    return monthlyNudgeCount < 10
}

/// 月初リセットチェック（アプリ起動時に呼び出す）
func checkAndResetMonthlyNudgeCountIfNeeded() {
    let calendar = Calendar.current
    let now = Date()
    let currentMonth = calendar.component(.month, from: now)
    let currentYear = calendar.component(.year, from: now)
    
    let lastMonth = defaults.integer(forKey: lastNudgeResetMonthKey)
    let lastYear = defaults.integer(forKey: lastNudgeResetYearKey)
    
    if currentYear != lastYear || currentMonth != lastMonth {
        resetMonthlyNudgeCount()
        defaults.set(currentMonth, forKey: lastNudgeResetMonthKey)
        defaults.set(currentYear, forKey: lastNudgeResetYearKey)
    }
}
```

**init()に追加:**

```swift
// 既存のinit()内に追加
self.nudgeCardCompletedCount = defaults.integer(forKey: nudgeCardCompletedCountKey)
self.monthlyNudgeCount = defaults.integer(forKey: monthlyNudgeCountKey)
self.hasRequestedReview = defaults.bool(forKey: hasRequestedReviewKey)

// 月初リセットチェック
checkAndResetMonthlyNudgeCountIfNeeded()
```

---

### Patch 2: SuperwallManager.swift

**変更:**

```swift
/// Superwall Placement イベント名
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case nudgeCardComplete5 = "nudge_card_complete_5"   // 新規
    case nudgeCardComplete10 = "nudge_card_complete_10" // 新規
    case profilePlanTap = "profile_plan_tap"
    
    // 削除:
    // case sessionComplete1 = "session_complete_1"
    // case sessionComplete3 = "session_complete_3"
    // case campaignAppLaunch = "campaign_app_launch"
    // case quotaExceeded = "quota_exceeded"
}
```

---

### Patch 3: NudgeCardView.swift

**変更:** `onPositiveAction`の呼び出し元（親View）で処理を追加

NudgeCardViewを表示している親View（MainTabViewまたはRootView）に以下のロジックを追加:

```swift
import StoreKit

// NudgeCardのアクションボタン押下後の処理
private func handleNudgeCardPositiveAction() {
    let appState = AppState.shared
    appState.incrementNudgeCardCompletedCount()
    
    let count = appState.nudgeCardCompletedCount
    let plan = appState.subscriptionInfo.plan
    
    // NudgeCardを閉じる
    appState.dismissNudgeCard()
    
    // 3回目: レビューリクエスト
    if count == 3 && !appState.hasRequestedReview {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            if let scene = UIApplication.shared.connectedScenes
                .first(where: { $0.activationState == .foregroundActive }) as? UIWindowScene {
                SKStoreReviewController.requestReview(in: scene)
            }
        }
        appState.markReviewRequested()
    }
    // 5回目: Paywall
    else if count == 5 && plan != .pro {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            SuperwallManager.shared.register(placement: SuperwallPlacement.nudgeCardComplete5.rawValue)
        }
    }
    // 10回目: Paywall（月上限）
    else if count == 10 && plan != .pro {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            SuperwallManager.shared.register(placement: SuperwallPlacement.nudgeCardComplete10.rawValue)
        }
    }
}
```

---

### Patch 4: ProblemNotificationScheduler.swift

**変更:** `scheduleNotifications`メソッドに通知回数制限を追加

```swift
/// ユーザーの選択した問題に基づいて通知をスケジュール
func scheduleNotifications(for problems: [String]) async {
    // 既存の問題通知をクリア
    await removeAllProblemNotifications()
    
    // Free プランかつ月間上限到達済みの場合はスケジュールしない
    let appState = await MainActor.run { AppState.shared }
    let canSchedule = await MainActor.run { appState.canReceiveNudge }
    
    if !canSchedule {
        logger.info("Monthly nudge limit reached. No notifications scheduled.")
        return
    }

    // ... 以下既存のロジック
}
```

**変更:** 通知がスケジュールされるたびにカウント

```swift
private func scheduleNotification(for problem: ProblemType, hour: Int, minute: Int) async {
    // ... 既存のロジック ...

    do {
        try await center.add(request)
        logger.info("Scheduled problem notification: \(problem.rawValue) at \(hour):\(minute)")
        
        // 通知スケジュール成功時にカウント（Freeプランのみ）
        await MainActor.run {
            if AppState.shared.subscriptionInfo.plan != .pro {
                AppState.shared.incrementMonthlyNudgeCount()
            }
        }
    } catch {
        logger.error("Failed to schedule problem notification: \(error.localizedDescription)")
    }
}
```

---

### Patch 5: MainTabView.swift（または該当View）

**削除:** `campaignAppLaunch`の呼び出し

```swift
// 削除
// SuperwallManager.shared.register(placement: SuperwallPlacement.campaignAppLaunch.rawValue)
```

---

### Patch 6: Superwall Dashboard設定

1. **新規Placement追加**
   - `nudge_card_complete_5`
   - `nudge_card_complete_10`

2. **Placement削除**
   - `session_complete_1`
   - `session_complete_3`
   - `campaign_app_launch`
   - `quota_exceeded`

3. **Paywall文言更新**
   - ヘッドライン: "Unlimited nudges, unlimited change."
   - バリュープロップ1: "Learns what hits you"
   - バリュープロップ2: "Catches you before you fall"
   - バリュープロップ3: "Stays one step ahead"
   - CTA: "Get unlimited nudges"

---

## 変更サマリー

| ファイル | 変更内容 |
|---------|---------|
| `AppState.swift` | `nudgeCardCompletedCount`, `monthlyNudgeCount`, `hasRequestedReview` 追加 |
| `SuperwallManager.swift` | `SuperwallPlacement` enum更新（削除・追加） |
| `NudgeCardView.swift` (親View) | アクションボタン押下後のPaywall・レビュー処理追加 |
| `ProblemNotificationScheduler.swift` | 通知回数制限ロジック追加 |
| `MainTabView.swift` | `campaignAppLaunch` 削除 |
| Superwall Dashboard | Placement追加・削除、Paywall文言更新 |

---

## テストケース

### 1. レビューリクエスト

- [ ] NudgeCard 1回目完了 → 何も出ない
- [ ] NudgeCard 2回目完了 → 何も出ない
- [ ] NudgeCard 3回目完了 → レビューリクエストが出る
- [ ] NudgeCard 4回目以降 → レビューリクエストは二度と出ない

### 2. Paywall表示

- [ ] NudgeCard 5回目完了（Freeプラン） → Paywallが出る
- [ ] NudgeCard 5回目完了（Proプラン） → Paywallは出ない
- [ ] NudgeCard 10回目完了（Freeプラン） → Paywallが出る
- [ ] NudgeCard 10回目完了（Proプラン） → Paywallは出ない

### 3. 通知回数制限

- [ ] Freeプラン: 10回の通知がスケジュールされる
- [ ] Freeプラン: 11回目以降の通知はスケジュールされない
- [ ] Proプラン: 通知回数に制限がない
- [ ] 月が変わるとカウントがリセットされる

### 4. Placement

- [ ] `onboarding_complete` → Paywall表示
- [ ] `nudge_card_complete_5` → Paywall表示
- [ ] `nudge_card_complete_10` → Paywall表示
- [ ] `profile_plan_tap` → Paywall表示
- [ ] 古いPlacement（session_complete_*, quota_exceeded, campaign_app_launch）は使用されない

---

## 注意事項

1. **レビューとPaywallは同時に出さない**: 3回目はレビューのみ、5回目・10回目はPaywallのみ

2. **11回目以降は何も出ない**: 通知自体がスケジュールされないため、NudgeCardも表示されない

3. **Proユーザーはすべて無制限**: 通知回数制限なし、Paywall表示なし

4. **月初リセット**: アプリ起動時に月が変わっていたら`monthlyNudgeCount`をリセット

---

## 日程

| フェーズ | 内容 | 目安 |
|--------|------|------|
| 1 | AppState.swift の変更 | 30分 |
| 2 | SuperwallManager.swift の変更 | 15分 |
| 3 | NudgeCard処理の追加 | 30分 |
| 4 | ProblemNotificationScheduler.swift の変更 | 30分 |
| 5 | 古いコードの削除 | 15分 |
| 6 | Superwall Dashboard設定 | 30分 |
| 7 | テスト | 1時間 |

**合計: 約3.5時間**

---

*最終更新: 2026-01-20*


