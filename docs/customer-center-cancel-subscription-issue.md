# Customer Center Cancel Subscription 問題と解決策

## 概要

Customer CenterでCancel Subscriptionを選択した際に、アプリ内でキャンセル処理を完結させたいが、現在はApp Storeにリダイレクトされてしまう問題。

---

## 現状（As-Is）

### 問題の概要

**現象**: 
- ユーザーが「Settings → Manage Plans → 現在のプランを押して → Cancel Subscriptions」を選択すると、アプリ内でキャンセルできるはずなのに、App Storeにリダイレクトされる。

**期待される動作**:
- アプリ内でサブスクリプション管理画面を表示し、キャンセル処理を完結させる
- 特にサンドボックス環境（ステージングスキーム）では、アプリ内で完結させたい

### 現在の実装状況

**ファイル**: `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`

**問題箇所**: 68-78行目

```swift
.sheet(isPresented: $showingCustomerCenter) {
    RevenueCatUI.CustomerCenterView()
        .onCustomerCenterRestoreCompleted { customerInfo in
            Task {
                let subscription = SubscriptionInfo(info: customerInfo)
                await MainActor.run {
                    appState.updateSubscriptionInfo(subscription)
                }
            }
        }
        // ❌ 問題: onCustomerCenterShowingManageSubscriptions ハンドラーが設定されていない
}
```

### 問題の原因

**参照箇所**: `examples/purchases-ios/RevenueCatUI/CustomerCenter/ViewModels/BaseManageSubscriptionViewModel.swift:175-176`

```swift
case .cancel:
    self.actionWrapper.handleAction(.showingManageSubscriptions)
```

- Cancelオプションが選択されると、`showingManageSubscriptions`アクションが発火する
- しかし、`ManageSubscriptionSheet.swift`で`onCustomerCenterShowingManageSubscriptions`ハンドラーが設定されていない
- そのため、デフォルトの動作（App Storeへのリダイレクト）が実行される

### 環境情報

- **スキーム**: 本番スキーム（Production）
- **APIキー**: `appl_AyTtJmtNsepVIgvJovlHkYdGfqF`（Production）
- **RevenueCatダッシュボード**: Cancelオプションは既に設定済み（フィードバックプロンプト付き）
- **RevenueCat API Key**: `appl_AyTtJmtNsepVIgvJovlHkYdGfqF`

---

## 理想状態（To-Be）

### 期待される動作

#### iOS 15.0以上の場合
- Cancel Subscriptionを選択した際に、**アプリ内シート**としてサブスクリプション管理画面を表示
- App Storeアプリへのリダイレクトは発生しない
- サンドボックス環境でも同様に動作する（サンドボックステストアカウントでログインしている必要がある）

#### iOS 15.0未満の場合
- `managementURL`を外部ブラウザで開く（フォールバック）

### 実装方針

- `onCustomerCenterShowingManageSubscriptions`ハンドラーを追加
- ハンドラー内で`Purchases.shared.showManageSubscriptions()`を呼び出す
- iOS 15.0以上では、`AppStore.showManageSubscriptions(in:)`が使用され、アプリ内シートとして表示される

---

## 調査結果と根拠

### 調査したドキュメント・コード

#### 1. Cancel Subscriptionの動作フロー

**参照箇所**: `examples/purchases-ios/RevenueCatUI/CustomerCenter/ViewModels/BaseManageSubscriptionViewModel.swift:175-176`

```swift
case .cancel:
    self.actionWrapper.handleAction(.showingManageSubscriptions)
```

- Cancelオプションが選択されると、`showingManageSubscriptions`アクションが発火する

#### 2. iOS 15.0以上でのアプリ内シート表示

**参照箇所**: `examples/purchases-ios/Sources/Support/ManageSubscriptionsHelper.swift:126-152`

```swift
@MainActor
@available(iOS 15.0, *)
func showSK2ManageSubscriptions() async -> Result<Void, PurchasesError> {
    // ...
    try await AppStore.showManageSubscriptions(in: windowScene)
    // ...
}
```

**重要な発見**:
- iOS 15.0以上では、`AppStore.showManageSubscriptions(in:)`が使用される
- これは**アプリ内シート**として表示される（App Storeアプリへのリダイレクトではない）
- サンドボックス環境でも動作する（サンドボックステストアカウントでログインしている必要がある）

**参照箇所**: `examples/purchases-ios/Sources/Support/ManageSubscriptionsHelper.swift:81-95`

```swift
func showAppleManageSubscriptions(managementURL: URL,
                                  completion: @escaping (Result<Void, PurchasesError>) -> Void) {
#if os(iOS) && !targetEnvironment(macCatalyst) || VISION_OS
    if #available(iOS 15.0, *),
       !ProcessInfo().isiOSAppOnMac {
        Async.call(with: completion) {
            return await self.showSK2ManageSubscriptions()
        }
        return
    }
#endif
    openURL(managementURL, completion: completion)
}
```

- iOS 15.0以上: `showSK2ManageSubscriptions()`を呼び出す（アプリ内シート）
- iOS 15.0未満: `managementURL`を外部ブラウザで開く

#### 3. ハンドラーの設定方法

**参照箇所**: `examples/purchases-ios/RevenueCatUI/CustomerCenter/Actions/CustomerCenterView+Actions.swift:248-252`

```swift
public func onCustomerCenterShowingManageSubscriptions(
    _ handler: @escaping CustomerCenterView.ShowingManageSubscriptionsHandler
) -> some View {
    return self.modifier(CustomerCenterView.OnShowingManageSubscriptionsModifier(handler: handler))
}
```

- `onCustomerCenterShowingManageSubscriptions`でハンドラーを設定できる
- ハンドラー内で`Purchases.shared.showManageSubscriptions()`を呼び出すと、iOS 15.0以上ではアプリ内シートが表示される

**参照箇所**: `examples/purchases-ios/RevenueCatUI/CustomerCenter/Actions/CustomerCenterView+Actions.swift:235-252`

- ドキュメント例にもハンドラーの設定方法が記載されている

---

## 実装パッチ（参考）

**注意**: 実装パッチは変更される可能性があるため、参考として記載。

### ファイル: `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`

**変更箇所**: 68-78行目

```swift
.sheet(isPresented: $showingCustomerCenter) {
    RevenueCatUI.CustomerCenterView()
        .onCustomerCenterRestoreCompleted { customerInfo in
            Task {
                let subscription = SubscriptionInfo(info: customerInfo)
                await MainActor.run {
                    appState.updateSubscriptionInfo(subscription)
                }
            }
        }
        .onCustomerCenterShowingManageSubscriptions {
            // iOS 15.0以上では、AppStore.showManageSubscriptions(in:)が呼ばれ、
            // アプリ内シートとして表示される（App Storeへのリダイレクトではない）
            // サンドボックス環境でも動作する（サンドボックステストアカウントでログインが必要）
            Task {
                do {
                    try await Purchases.shared.showManageSubscriptions()
                } catch {
                    print("[ManageSubscriptionSheet] Failed to show manage subscriptions: \(error)")
                    // フォールバック: managementURLを開く
                    if let managementURL = appState.subscriptionInfo.managementURL {
                        await MainActor.run {
                            UIApplication.shared.open(managementURL)
                        }
                    }
                }
            }
        }
}
```

### 変更内容の説明

1. `onCustomerCenterShowingManageSubscriptions`ハンドラーを追加
2. ハンドラー内で`Purchases.shared.showManageSubscriptions()`を呼び出す
   - iOS 15.0以上: アプリ内シートとして表示される
   - iOS 15.0未満: `managementURL`を外部ブラウザで開く（`ManageSubscriptionsHelper`内で処理される）
3. エラーハンドリングを追加（フォールバックで`managementURL`を開く）

---

## 期待される動作

### iOS 15.0以上
- Cancel Subscriptionを選択した際に、アプリ内シートとしてサブスクリプション管理画面が表示される
- App Storeアプリへのリダイレクトは発生しない
- サンドボックス環境でも動作する（サンドボックステストアカウントでログインしている必要がある）

### iOS 15.0未満
- `managementURL`が外部ブラウザで開かれる（フォールバック）

---

## 注意事項

1. **iOS 15.0以上が前提**: `AppStore.showManageSubscriptions(in:)`はiOS 15.0以降の機能
2. **サンドボックス環境**: サンドボックステストアカウントでログインしている必要がある
3. **エラーハンドリング**: エラー時は`managementURL`をフォールバックで開く

---

## 参考: リポジトリの使い分け

### 推奨順序

1. **`/examples/revenuecat-docs`**（最優先）
   - 公式ドキュメント
   - 統合方法、設定方法、使い方の説明
   - コード例（`code_blocks/`）

2. **`/examples/purchases-ios`**（実装詳細）
   - RevenueCat iOS SDKのソースコード
   - APIの実装詳細
   - 内部動作の確認

3. **`/examples/purchases-ios-spm`**（参考程度）
   - SPM専用版（ほぼ`purchases-ios`と同じ）
   - 通常は参照不要

### 推奨ワークフロー

1. まず`/examples/revenuecat-docs`で統合方法を確認
2. 実装詳細が必要なら`/examples/purchases-ios`でソースコードを確認
3. `purchases-ios-spm`は通常は参照不要

---

## 関連ファイル

- `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift` - 修正対象ファイル
- `examples/purchases-ios/RevenueCatUI/CustomerCenter/ViewModels/BaseManageSubscriptionViewModel.swift` - Cancel処理の実装
- `examples/purchases-ios/Sources/Support/ManageSubscriptionsHelper.swift` - サブスクリプション管理の実装
- `examples/purchases-ios/RevenueCatUI/CustomerCenter/Actions/CustomerCenterView+Actions.swift` - ハンドラーの定義

---

## 更新履歴

- 2025-11-XX: 初版作成











