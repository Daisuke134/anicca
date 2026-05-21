# Phase 6: Hard Paywall マージ仕様書

> 作成日: 2026-01-25
> 目的: feature/hard-paywall を dev にマージする際の完全な仕様

---

## 0. 作業場所

| 項目 | パス/値 |
|------|--------|
| Worktree | `/Users/cbns03/Downloads/anicca-hard-paywall` |
| ブランチ | `feature/hard-paywall` |
| 元リポジトリ | `/Users/cbns03/Downloads/anicca-project` |
| マージ先 | `dev` |

**⚠️ 重要: 作業は必ず Worktree で行うこと**

```bash
cd /Users/cbns03/Downloads/anicca-hard-paywall/aniccaios
```

---

## 1. 背景と目的

### Hard Paywall とは

| 項目 | 説明 |
|------|------|
| 定義 | オンボーディング完了時に閉じれないPaywallを表示 |
| 効果 | 全ユーザーがトライアルまたは有料会員になる |
| 結果 | Freeプランの概念がなくなる |

### 課金モデルの変更

| Before | After |
|--------|-------|
| Free: 月10回まで通知 | ❌ なし |
| Pro: 無制限 | ✅ 全員がPro（トライアル含む） |
| 5回目/10回目でPaywall | ❌ 削除（不要） |

---

## 2. 採用方針

### UI

| 項目 | 採用元 | 理由 |
|------|--------|------|
| Single Screen UI | dev | タブなし、1画面構成 |
| ProfileView | dev（削除） | Single Screen に統合済み |
| MainTabView | dev ベース | 下記修正あり |

### ロジック

| 項目 | 採用元 | 理由 |
|------|--------|------|
| SubscriptionInfo.isActiveSubscriber | feature/hard-paywall | 通知制御に使用 |
| SubscriptionInfo.isSubscriptionExpiredOrCanceled | feature/hard-paywall | 通知制御に使用 |
| 5回目/10回目 Paywall | **削除** | 全員Subscriber前提 |

### 不採用（削除）

| 項目 | 理由 |
|------|------|
| BlockedView.swift | 不要（通知来ないだけでアプリは使える） |
| BlockedView条件（MainTabView） | 不要 |
| SuperwallPlacement.resubscribe | BlockedViewでしか使わない |
| profile_subscribe (Localizable) | BlockedViewでしか使わない |
| blocked_title, blocked_message | BlockedViewでしか使わない |

---

## 3. ユーザー体験（マージ後）

### フロー

```
オンボーディング
      ↓
  Paywall（ハード、閉じれない）
      ↓
 トライアル開始（7日間無料）
      ↓
┌─────────────────────────────────┐
│  アプリ使用中                    │
│  - 全機能使える                  │
│  - 通知が届く                    │
│  - NudgeCardが出る               │
└─────────────────────────────────┘
      ↓
   7日後
      ↓
  ┌───────────────┐
  │ キャンセル?   │
  └───────────────┘
     ↓           ↓
    No          Yes
     ↓           ↓
  Pro継続     購読切れ
     ↓           ↓
  全機能      アプリは使える
  通知届く    通知来ない
```

### 状態別の体験

| 状態 | アプリUI | 通知 | NudgeCard |
|------|---------|------|-----------|
| トライアル中 | ✅ 全部使える | ✅ 届く | ✅ 出る |
| Pro会員 | ✅ 全部使える | ✅ 届く | ✅ 出る |
| 購読切れ | ✅ 全部使える | ❌ 届かない | ❌ 出ない |

**購読切れでも:**
- アプリは開ける
- 問題の追加/削除はできる
- 設定変更はできる
- **ただし通知が来ないから価値がない**
- Single Screen UIの「Subscribe」から再購入可能

---

## 4. As-Is（Worktreeの現状）

### 4.1 MainTabView.swift（問題あり）

```swift
var body: some View {
    Group {
        // Hard Paywall: 購読なし + オンボーディング完了 → BlockedView
        if appState.subscriptionInfo.isSubscriptionExpiredOrCanceled && appState.isOnboardingComplete {
            BlockedView()  // ← 不要
        } else {
            Group {
                switch appState.selectedRootTab {  // ← タブ構成（devはSingle Screen）
                case .myPath:
                    MyPathTabView()
                case .profile:
                    ProfileView()  // ← devでは削除済み
                }
            }
        }
    }
    // ...
}
```

### 4.2 BlockedView.swift（削除対象）

```swift
struct BlockedView: View {
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "lock.fill")
            Text(String(localized: "blocked_title"))
            Text(String(localized: "blocked_message"))
            Button(String(localized: "profile_subscribe")) {
                SuperwallManager.shared.register(placement: SuperwallPlacement.resubscribe.rawValue)
            }
        }
    }
}
```

### 4.3 SuperwallManager.swift（問題あり）

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case resubscribe = "resubscribe"  // ← 削除対象
}
```

### 4.4 Localizable.strings（削除対象あり）

```
/* ========== Hard Paywall ========== */
"profile_subscribe" = "Subscribe";        // ← 削除
"blocked_title" = "Subscribe to Continue"; // ← 削除
"blocked_message" = "Subscribe to...";     // ← 削除
```

---

## 5. To-Be（修正後）

### 5.1 MainTabView.swift

devブランチのコードをベースに、5回目/10回目 Paywall ロジックを削除:

```swift
import SwiftUI
import UIKit
import Combine
import StoreKit

struct MainTabView: View {
    @EnvironmentObject private var appState: AppState

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
            .background(AppBackground())
            .ignoresSafeArea(.keyboard, edges: .bottom)
    }

    private func handleNudgeCardCompletion(content: NudgeContent) {
        appState.incrementNudgeCardCompletedCount()
        let count = appState.nudgeCardCompletedCount
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
            return
        }
        // Hard Paywall: 5回目/10回目のPaywall表示は削除（全員Subscriber前提）
    }
}
```

### 5.2 SubscriptionInfo.swift（維持）

```swift
// MARK: - Hard Paywall Properties

private static let allowedStatuses: Set<String> = [
    "active", "trialing",
    "grace", "in_grace_period", "billing_issue", "billing_retry"
]

var isActiveSubscriber: Bool {
    return !isSubscriptionExpiredOrCanceled
}

var isSubscriptionExpiredOrCanceled: Bool {
    if plan == .free { return true }
    return !Self.allowedStatuses.contains(status)
}
```

### 5.3 SuperwallManager.swift

devブランチのコードを採用（5回目/10回目のプレースメント維持は不要だが後方互換のため残す）:

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case nudgeCardComplete5 = "nudge_card_complete_5"   // 未使用だが残す
    case nudgeCardComplete10 = "nudge_card_complete_10" // 未使用だが残す
    case profilePlanTap = "profile_plan_tap"
}
```

### 5.4 削除するファイル

| ファイル | 操作 |
|---------|------|
| `BlockedView.swift` | 削除 |
| `ProfileView.swift` | devで既に削除済み（維持） |

### 5.5 削除するローカライズ

| キー | 削除 |
|-----|------|
| profile_subscribe | ✅ 削除 |
| blocked_title | ✅ 削除 |
| blocked_message | ✅ 削除 |

---

## 6. 修正パッチ

### 6.1 Worktreeでの修正

```bash
cd /Users/cbns03/Downloads/anicca-hard-paywall/aniccaios
```

#### Step 1: BlockedView.swift 削除

```bash
rm aniccaios/Views/BlockedView.swift
```

#### Step 2: MainTabView.swift を dev から復元

```bash
git checkout df7f0931 -- aniccaios/MainTabView.swift
```

その後、5回目/10回目ロジックを削除する編集を適用。

#### Step 3: ProfileView.swift を dev から復元（削除状態）

```bash
git checkout df7f0931 -- aniccaios/Views/Profile/ProfileView.swift
rm aniccaios/Views/Profile/ProfileView.swift
```

#### Step 4: SuperwallManager.swift を dev から復元

```bash
git checkout df7f0931 -- aniccaios/Services/SuperwallManager.swift
```

#### Step 5: Localizable.strings から不要キー削除

**en.lproj/Localizable.strings:**
```diff
-/* ========== Hard Paywall ========== */
-"profile_subscribe" = "Subscribe";
-"blocked_title" = "Subscribe to Continue";
-"blocked_message" = "Subscribe to continue using Anicca and start your journey of change.";
```

**ja.lproj/Localizable.strings:**
```diff
-/* ========== Hard Paywall ========== */
-"profile_subscribe" = "購読する";
-"blocked_title" = "購読して続ける";
-"blocked_message" = "購読してAniccaで変化の旅を始めましょう。";
```

#### Step 6: project.pbxproj からBlockedView参照削除

BlockedView.swiftの参照をXcodeプロジェクトから削除。

---

## 7. タスクリスト

| # | タスク | コマンド/操作 | 状態 |
|---|-------|--------------|------|
| 1 | Worktreeに移動 | `cd /Users/cbns03/Downloads/anicca-hard-paywall/aniccaios` | [ ] |
| 2 | BlockedView.swift 削除 | `rm aniccaios/Views/BlockedView.swift` | [ ] |
| 3 | MainTabView.swift 復元+修正 | devから復元、5回目/10回目ロジック削除 | [ ] |
| 4 | ProfileView.swift 削除確認 | devと同じ状態に | [ ] |
| 5 | SuperwallManager.swift 復元 | devから復元 | [ ] |
| 6 | Localizable.strings 修正 | 不要キー削除 | [ ] |
| 7 | project.pbxproj 修正 | BlockedView参照削除 | [ ] |
| 8 | ビルド確認 | Xcodeでビルド | [ ] |
| 9 | Worktreeでコミット | `git add . && git commit --amend` | [ ] |
| 10 | 再マージ | `cd /Users/cbns03/Downloads/anicca-project && git merge feature/hard-paywall` | [ ] |
| 11 | コンフリクト解決 | 下記参照 | [ ] |
| 12 | 実機テスト | ユーザーが確認 | [ ] |
| 13 | devプッシュ | `git push origin dev` | [ ] |

---

## 8. コンフリクト解決方針

マージ時に発生するコンフリクトの解決方法:

| ファイル | 解決方法 |
|---------|----------|
| MainTabView.swift | feature/hard-paywall（修正済み）を採用 |
| ProfileView.swift | dev採用（削除のまま） |
| Localizable.strings | 手動マージ（devのSingle Screen UIキー + SubscriptionInfo維持） |
| report.xml | dev採用 |

---

## 9. 実機テストチェックリスト

| # | テスト項目 | 確認 |
|---|-----------|------|
| 1 | アプリ起動・クラッシュなし | [ ] |
| 2 | オンボーディング → Paywall（ハード、閉じれない） | [ ] |
| 3 | トライアル開始 → Single Screen UI表示 | [ ] |
| 4 | 通知が届く | [ ] |
| 5 | NudgeCardが表示される | [ ] |
| 6 | 「Subscribe」タップ → Paywall表示 | [ ] |

---

## 10. 維持するもの（feature/hard-paywallから）

| ファイル | 内容 | 理由 |
|---------|------|------|
| SubscriptionInfo.swift | isActiveSubscriber, isSubscriptionExpiredOrCanceled | 通知制御に使用 |
| SubscriptionInfoTests.swift | テストコード | 維持 |

---

## 11. 注意事項

1. **Worktreeで作業すること**: `/Users/cbns03/Downloads/anicca-hard-paywall`
2. **devを直接編集しない**: マージで反映する
3. **BlockedViewは不要**: 通知が来ないだけでアプリは使える
4. **後方互換性**: nudgeCardComplete5/10のプレースメントは残すが使わない

---

最終更新: 2026-01-25

