# Phase 6: UI修正 - Single Screen ボタンスタイル

## 概要

Single Screen実装のSubscribe/Account セクションのUI改善。

### 問題点
1. **「登録する」は誤訳** - "Subscribe"の直訳だが意味が違う
2. **ボタンがデカすぎ** - PrimaryButtonスタイルは設定系には過剰
3. **破壊的アクション（Sign Out/Delete Account）が目立ちすぎ**

---

## As-Is（現状）

```
┌─────────────────────────────────────────┐
│  ┌─────────────────────────────────┐    │
│  │         登録する                 │    │  ← PrimaryButton（デカい）
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │        サインアウト              │    │  ← 同サイズ（過剰）
│  └─────────────────────────────────┘    │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │       アカウントを削除           │    │  ← 同サイズ（過剰）
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## To-Be（変更後）

### 英語版 - Free + 未サインイン
```
┌─────────────────────────────────────────┐
│                                         │
│       [ Upgrade to Pro ]                │  ← セカンダリボタン
│                                         │
│     Privacy Policy · Terms of Use       │
└─────────────────────────────────────────┘
```

### 日本語版 - Free + 未サインイン
```
┌─────────────────────────────────────────┐
│                                         │
│     [ Pro にアップグレード ]              │  ← セカンダリボタン
│                                         │
│   プライバシーポリシー · 利用規約         │
└─────────────────────────────────────────┘
```

### 英語版 - Free + サインイン済み
```
┌─────────────────────────────────────────┐
│                                         │
│       [ Upgrade to Pro ]                │  ← セカンダリボタン
│                                         │
│        Sign Out                         │  ← テキストリンク（グレー）
│        Delete Account                   │  ← テキストリンク（赤）
│                                         │
│     Privacy Policy · Terms of Use       │
└─────────────────────────────────────────┘
```

### 日本語版 - Free + サインイン済み
```
┌─────────────────────────────────────────┐
│                                         │
│     [ Pro にアップグレード ]              │  ← セカンダリボタン
│                                         │
│        サインアウト                      │  ← テキストリンク（グレー）
│        アカウントを削除                  │  ← テキストリンク（赤）
│                                         │
│   プライバシーポリシー · 利用規約         │
└─────────────────────────────────────────┘
```

### 英語版 - Pro + サインイン済み
```
┌─────────────────────────────────────────┐
│                                         │
│       [ Manage Subscription ]           │  ← セカンダリボタン
│                                         │
│        Sign Out                         │  ← テキストリンク（グレー）
│        Delete Account                   │  ← テキストリンク（赤）
│                                         │
│     Privacy Policy · Terms of Use       │
└─────────────────────────────────────────┘
```

### 日本語版 - Pro + サインイン済み
```
┌─────────────────────────────────────────┐
│                                         │
│     [ サブスクリプションを管理 ]          │  ← セカンダリボタン
│                                         │
│        サインアウト                      │  ← テキストリンク（グレー）
│        アカウントを削除                  │  ← テキストリンク（赤）
│                                         │
│   プライバシーポリシー · 利用規約         │
└─────────────────────────────────────────┘
```

---

## To-Be チェックリスト

| # | 項目 | 完了 |
|---|------|------|
| 1 | Subscribe ボタンをセカンダリスタイルに変更（44pt最小タップエリア） | ☐ |
| 2 | Cancel Subscription ボタンをセカンダリスタイルに変更（44pt最小タップエリア） | ☐ |
| 3 | Sign Out をテキストリンク風（secondaryLabel）に変更（44pt最小タップエリア） | ☐ |
| 4 | Delete Account をテキストリンク風（systemRed）に変更（44pt最小タップエリア） | ☐ |
| 5 | Account セクションは `appState.isSignedIn` 時のみ表示 | ☐ |
| 6 | ローカライズ文字列を更新（EN/JP） | ☐ |

---

## 状態による表示分岐

```swift
// subscriptionSection: 常に表示
if appState.subscriptionInfo.plan == .free {
    // "Upgrade to Pro" ボタン
} else {
    // "Manage Subscription" ボタン
}

// accountSection: サインイン時のみ表示
if appState.isSignedIn {
    // Sign Out + Delete Account
}
```

---

## ローカライズ

### 既存キー（変更不要）

| Key | EN | JP | 用途 |
|-----|----|----|------|
| `common_cancel` | Cancel | キャンセル | 確認ダイアログ |
| `legal_privacy_policy` | Privacy Policy | プライバシーポリシー | Footer |
| `legal_terms_of_use` | Terms of Use (EULA) | 利用規約 | Footer |
| `sign_out_confirm_title` | Sign Out? | サインアウトしますか？ | 確認ダイアログ |
| `sign_out_confirm_message` | Are you sure you want to sign out? | 本当にサインアウトしますか？ | 確認ダイアログ |
| `delete_account_confirm_title` | Delete Account? | アカウントを削除しますか？ | 確認ダイアログ |
| `delete_account_confirm_message` | This action cannot be undone. All your data will be permanently deleted. | この操作は取り消せません。すべてのデータが完全に削除されます。 | 確認ダイアログ |

### 変更するキー

#### en.lproj/Localizable.strings

```diff
- "single_screen_subscribe" = "Subscribe";
+ "single_screen_subscribe" = "Upgrade to Pro";

- "single_screen_cancel_subscription" = "Cancel Subscription";
+ "single_screen_cancel_subscription" = "Manage Subscription";
```

#### ja.lproj/Localizable.strings

```diff
- "single_screen_subscribe" = "登録する";
+ "single_screen_subscribe" = "Pro にアップグレード";

- "single_screen_cancel_subscription" = "登録をキャンセル";
+ "single_screen_cancel_subscription" = "サブスクリプションを管理";
```

---

## パッチ

### 1. MyPathTabView.swift - subscriptionSection

```swift
// MARK: - Subscription Section

@ViewBuilder
private var subscriptionSection: some View {
    if appState.subscriptionInfo.plan == .free {
        // Free: セカンダリボタン（Upgrade to Pro）
        Button {
            SuperwallManager.shared.register(placement: SuperwallPlacement.singleScreenSubscribe.rawValue)
        } label: {
            Text(String(localized: "single_screen_subscribe"))
                .font(.subheadline.weight(.medium))
                .foregroundStyle(AppTheme.Colors.buttonSelected)
                .padding(.horizontal, 20)
                .padding(.vertical, 12)  // 44pt タップエリア確保
                .background(AppTheme.Colors.buttonUnselected)
                .clipShape(Capsule())
        }
    } else {
        // Pro: セカンダリボタン（Manage Subscription）
        Button {
            showingManageSubscription = true
        } label: {
            Text(String(localized: "single_screen_cancel_subscription"))
                .font(.subheadline.weight(.medium))
                .foregroundStyle(AppTheme.Colors.buttonSelected)
                .padding(.horizontal, 20)
                .padding(.vertical, 12)  // 44pt タップエリア確保
                .background(AppTheme.Colors.buttonUnselected)
                .clipShape(Capsule())
        }
        .sheet(isPresented: $showingManageSubscription) {
            customerCenterContent
        }
    }
}
```

### 2. MyPathTabView.swift - accountSection

**注意**: このセクションは `appState.isSignedIn` が `true` の場合のみ表示される（既存の `if appState.isSignedIn { accountSection }` で制御済み）。

```swift
// MARK: - Account Section

@ViewBuilder
private var accountSection: some View {
    VStack(spacing: 16) {
        // Sign Out: テキストリンク風（グレー）
        Button {
            showSignOutConfirm = true
        } label: {
            Text(String(localized: "single_screen_sign_out"))
                .font(.subheadline)
                .foregroundStyle(AppTheme.Colors.secondaryLabel)
                .frame(minHeight: 44)  // 44pt タップエリア確保
        }
        .alert(String(localized: "sign_out_confirm_title"), isPresented: $showSignOutConfirm) {
            Button(String(localized: "common_cancel"), role: .cancel) { }
            Button(String(localized: "single_screen_sign_out"), role: .destructive) {
                signOut()
            }
        } message: {
            Text(String(localized: "sign_out_confirm_message"))
        }

        // Delete Account: テキストリンク風（システム赤）
        Button {
            showDeleteAccountConfirm = true
        } label: {
            Text(String(localized: "single_screen_delete_account"))
                .font(.subheadline)
                .foregroundStyle(Color(.systemRed))  // ダークモード対応
                .frame(minHeight: 44)  // 44pt タップエリア確保
        }
        .alert(String(localized: "delete_account_confirm_title"), isPresented: $showDeleteAccountConfirm) {
            Button(String(localized: "common_cancel"), role: .cancel) { }
            Button(String(localized: "single_screen_delete_account"), role: .destructive) {
                deleteAccount()
            }
        } message: {
            Text(String(localized: "delete_account_confirm_message"))
        }
    }
}
```

---

## テストマトリックス

| # | To-Be | テスト方法 | カバー |
|---|-------|-----------|--------|
| 1 | Subscribe ボタンがセカンダリスタイル | 目視: Free状態でボタンがCapsule背景 | ☐ |
| 2 | Subscribe ボタンが44pt以上 | 目視: タップしやすいサイズ | ☐ |
| 3 | Manage Subscription ボタンがセカンダリスタイル | 目視: Pro状態でボタンがCapsule背景 | ☐ |
| 4 | Sign Out がグレーテキスト | 目視: secondaryLabel色 | ☐ |
| 5 | Sign Out が44pt以上 | 目視: タップしやすいサイズ | ☐ |
| 6 | Delete Account が赤テキスト | 目視: systemRed色 | ☐ |
| 7 | Delete Account が44pt以上 | 目視: タップしやすいサイズ | ☐ |
| 8 | EN: "Upgrade to Pro" 表示 | 言語切替: 英語 | ☐ |
| 9 | JP: "Pro にアップグレード" 表示 | 言語切替: 日本語 | ☐ |
| 10 | EN: "Manage Subscription" 表示 | DEBUG: Set Pro → 英語 | ☐ |
| 11 | JP: "サブスクリプションを管理" 表示 | DEBUG: Set Pro → 日本語 | ☐ |
| 12 | 未サインイン時: Account セクション非表示 | DEBUG: Reset → Sign Out/Delete Account なし | ☐ |
| 13 | サインイン時: Account セクション表示 | DEBUG: Set Signed In → Sign Out/Delete Account あり | ☐ |
| 14 | ダークモード: Delete Account が見やすい | ダークモード切替 | ☐ |

---

## 実行手順

```bash
# 1. MyPathTabView.swift の subscriptionSection を編集
# 2. MyPathTabView.swift の accountSection を編集
# 3. en.lproj/Localizable.strings を編集
# 4. ja.lproj/Localizable.strings を編集

# 5. ビルド確認
cd /Users/cbns03/Downloads/anicca-single-screen/aniccaios
xcodebuild build -project aniccaios.xcodeproj -scheme aniccaios-staging -destination 'platform=iOS Simulator,name=iPhone 16 Pro,OS=18.6' -quiet

# 6. シミュレータで目視確認（テストマトリックスに従う）
open -a Simulator
# Xcodeから Cmd+R で実行
```

---

## レビューチェックリスト

### コード品質
- [ ] `PrimaryButton` が使われていないこと
- [ ] タップエリアが44pt以上確保されていること（`padding` または `frame(minHeight:)`）
- [ ] 色がハードコードされていないこと（`AppTheme.Colors` または `Color(.system*)`）
- [ ] ダークモードで全ボタンが視認できること

### ローカライズ
- [ ] EN: "Upgrade to Pro" / "Manage Subscription" と表示
- [ ] JP: "Pro にアップグレード" / "サブスクリプションを管理" と表示
- [ ] 確認ダイアログのテキストが正しいこと

### 状態分岐
- [ ] Free + 未サインイン: Subscribe のみ
- [ ] Free + サインイン: Subscribe + Sign Out + Delete Account
- [ ] Pro + 未サインイン: Manage Subscription のみ
- [ ] Pro + サインイン: Manage Subscription + Sign Out + Delete Account

---

## 参考

- [課金UIまとめ](https://note.com/telq/n/n836e139e0a6b)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [UXライティング解説](https://blog.nijibox.jp/article/ux_writing/)
