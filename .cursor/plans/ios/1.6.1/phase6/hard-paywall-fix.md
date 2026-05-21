# Hard Paywall 修正仕様書

> 作成日: 2026-01-25
> 問題: ProfileView を変更しすぎた（CustomerCenter → Apple直リンクに変わってしまった）

---

## 0. 作業場所

| 項目 | パス/値 |
|------|--------|
| Worktree | `/Users/cbns03/Downloads/anicca-hard-paywall` |
| ブランチ | `feature/hard-paywall` |
| 元リポジトリ | `/Users/cbns03/Downloads/anicca-project` |
| マージ先 | `dev` |

**レビュー時は Worktree のコードを確認すること。**

```bash
cd /Users/cbns03/Downloads/anicca-hard-paywall/aniccaios
```

---

## 1. 問題の概要

| 項目 | 内容 |
|------|------|
| 問題 | 有料ユーザーがProfileタップ時、RevenueCat CustomerCenter ではなく Apple 購読管理画面に飛ぶ |
| 原因 | ProfileView の accountCard 内ボタンを完全に書き換えてしまった |
| 影響 | 有料ユーザーの UX が変わった（意図しない変更） |

---

## 2. As-Is（現状・問題のあるコード）

### ProfileView.swift - accountCard

```swift
private var accountCard: some View {
    CardView(cornerRadius: 32) {
        VStack(spacing: 0) {
            nameRow
            divider
            // Hard Paywall: Cancel Subscription / Subscribe ボタン
            subscriptionButton  // ← これが問題
        }
    }
}

private var subscriptionButton: some View {
    Button {
        if appState.subscriptionInfo.isActiveSubscriber {
            // アクティブ購読者 → Apple購読管理画面へ
            if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
                UIApplication.shared.open(url)
            }
        } else {
            SuperwallManager.shared.register(placement: SuperwallPlacement.resubscribe.rawValue)
        }
    } label: {
        HStack {
            Text(appState.subscriptionInfo.isActiveSubscriber
                ? String(localized: "profile_cancel_subscription")
                : String(localized: "profile_subscribe"))
            // ...
        }
    }
}
```

---

## 3. To-Be（修正後）

### ProfileView.swift - accountCard を元に戻す

```swift
private var accountCard: some View {
    CardView(cornerRadius: 32) {
        VStack(spacing: 0) {
            nameRow
            divider
            Button {
                if appState.subscriptionInfo.plan == .free {
                    SuperwallManager.shared.register(placement: SuperwallPlacement.profilePlanTap.rawValue)
                } else {
                    showingManageSubscription = true  // RevenueCat CustomerCenter
                }
            } label: {
                row(label: String(localized: "profile_row_plan"), value: planDisplayValue, showsChevron: true)
            }
            .buttonStyle(.plain)
        }
    }
}

private var planDisplayValue: String {
    appState.subscriptionInfo.displayPlanName
}
```

### SuperwallPlacement.swift - profilePlanTap を復活（resubscribe は維持）

```swift
enum SuperwallPlacement: String {
    case onboardingComplete = "onboarding_complete"
    case resubscribe = "resubscribe"           // ← 維持（BlockedView用）
    case profilePlanTap = "profile_plan_tap"   // ← 復活（ProfileView用）
}
```

---

## 4. 修正パッチ

### 4.1 ProfileView.swift

```diff
 private var accountCard: some View {
     CardView(cornerRadius: 32) {
         VStack(spacing: 0) {
             nameRow
             divider
-            // Hard Paywall: Cancel Subscription / Subscribe ボタン
-            subscriptionButton
+            Button {
+                if appState.subscriptionInfo.plan == .free {
+                    SuperwallManager.shared.register(placement: SuperwallPlacement.profilePlanTap.rawValue)
+                } else {
+                    showingManageSubscription = true
+                }
+            } label: {
+                row(label: String(localized: "profile_row_plan"), value: planDisplayValue, showsChevron: true)
+            }
+            .buttonStyle(.plain)
         }
     }
 }

-// MARK: - Hard Paywall: Subscription Button
-
-private var subscriptionButton: some View {
-    Button {
-        if appState.subscriptionInfo.isActiveSubscriber {
-            if let url = URL(string: "https://apps.apple.com/account/subscriptions") {
-                UIApplication.shared.open(url)
-            }
-        } else {
-            SuperwallManager.shared.register(placement: SuperwallPlacement.resubscribe.rawValue)
-        }
-    } label: {
-        HStack {
-            Text(appState.subscriptionInfo.isActiveSubscriber
-                ? String(localized: "profile_cancel_subscription")
-                : String(localized: "profile_subscribe"))
-                .font(.system(size: 16))
-                .foregroundStyle(appState.subscriptionInfo.isActiveSubscriber
-                    ? AppTheme.Colors.secondaryLabel
-                    : AppTheme.Colors.accent)
-            Spacer()
-            Image(systemName: "chevron.right")
-                .foregroundStyle(AppTheme.Colors.secondaryLabel)
-                .opacity(0.6)
-        }
-        .padding(.vertical, 14)
-    }
-    .buttonStyle(.plain)
-    .accessibilityIdentifier("subscription_button")
-}
+private var planDisplayValue: String {
+    appState.subscriptionInfo.displayPlanName
+}
```

### 4.2 SuperwallManager.swift

```diff
 enum SuperwallPlacement: String {
-    case onboardingComplete = "onboarding_complete"  // ハード化（Superwall側で設定）
-    case resubscribe = "resubscribe"  // 再購読用（Trial なし）
+    case onboardingComplete = "onboarding_complete"
+    case resubscribe = "resubscribe"
+    case profilePlanTap = "profile_plan_tap"
 }
```

---

## 5. 維持するもの（変更しない）

| ファイル | 内容 | 理由 |
|---------|------|------|
| BlockedView.swift | 新規作成済み | 正しい実装 |
| MainTabView.swift | BlockedView 条件分岐 | 正しい実装 |
| SubscriptionInfo.swift | isActiveSubscriber, isSubscriptionExpiredOrCanceled | 正しい実装 |
| AppState.swift | canReceiveNudge = true | 正しい実装 |
| Localizable.strings | blocked_title, blocked_message | 正しい実装 |

---

## 6. 削除するローカライズ

| キー | 削除 | 理由 |
|-----|------|------|
| profile_cancel_subscription | ✅ 削除 | 使わなくなった |
| profile_subscribe | ❌ 維持 | BlockedView で使用中 |

---

## 7. 実行手順

| # | タスク | コマンド/操作 |
|---|-------|--------------|
| 1 | ProfileView.swift 修正 | パッチ適用 |
| 2 | SuperwallManager.swift 修正 | profilePlanTap 復活 |
| 3 | 不要ローカライズ削除 | en.lproj, ja.lproj |
| 4 | ビルド確認 | `cd /Users/cbns03/Downloads/anicca-hard-paywall/aniccaios && fastlane build_for_device` |
| 5 | 手動テスト | 下記チェックリスト |
| 6 | Worktree でコミット | `git add . && git commit -m "fix: ProfileView を元に戻す"` |
| 7 | Worktree プッシュ | `git push origin feature/hard-paywall` |
| 8 | dev にマージ | `git checkout dev && git merge feature/hard-paywall` |
| 9 | dev プッシュ | `git push origin dev` |

---

## 8. 手動テストチェックリスト

| # | テスト項目 | 確認 |
|---|-----------|------|
| 1 | アプリ起動・クラッシュなし | [ ] |
| 2 | オンボーディング後 Paywall 表示 | [ ] |
| 3 | Profile「Plan: Pro」タップ → CustomerCenter 表示 | [ ] |
| 4 | キャンセル後 BlockedView 表示（🔒） | [ ] |
| 5 | BlockedView「Subscribe」→ Paywall 表示 | [ ] |
| 6 | BlockedView「Subscribe」ボタンが機能する | [ ] |

---

## 9. 変更サマリー

| 変更種別 | ファイル | 内容 |
|---------|---------|------|
| 修正 | ProfileView.swift | accountCard を元に戻す、subscriptionButton 削除 |
| 修正 | SuperwallManager.swift | profilePlanTap 復活 |
| 削除 | Localizable.strings | profile_cancel_subscription のみ |
| 維持 | BlockedView.swift | そのまま |
| 維持 | MainTabView.swift | そのまま |
| 維持 | SubscriptionInfo.swift | そのまま |
| 維持 | AppState.swift | そのまま |
