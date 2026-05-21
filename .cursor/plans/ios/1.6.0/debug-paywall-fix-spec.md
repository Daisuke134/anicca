# Spec: DEBUGリセットボタン修正 + RevenueCat Offering/Product ID 更新

## 概要（What & Why）

**What**: 3つの修正を行う。
1. DEBUGリセットボタンがオンボーディングをリセットしないため、Paywall確認フローに入れない
2. RevenueCat Offering ID が旧値 `Anicca Monthly` のまま → 新デザインの `ofrngbf9a09cfea` に更新
3. Product ID がハードコード `ai.anicca.app.ios.monthly` → `prod8eb90326e4` に更新

**Why**: Superwall→RevenueCat マイグレーション後、新Paywallデザインを実機確認するために必要。DEBUGボタンで状態リセット → オンボーディング再開 → Paywall表示の確認フローを動かす。

## 受け入れ条件

| # | 条件 | テスト可能 |
|---|------|-----------|
| AC1 | DEBUGボタン「Reset to Free + Signed Out」タップで、オンボーディングが `.welcome` からやり直しになる | ✅ |
| AC2 | DEBUGボタンタップで RevenueCat もログアウトされる | ✅ |
| AC3 | オンボーディング完了後、DEBUGビルドでは `isEntitled` に関係なくPaywallが表示される | ✅ |
| AC4 | PaywallView が新Offering `ofrngbf9a09cfea` のデザインで表示される | ✅ |
| AC5 | Releaseビルドでは既存Proユーザーは従来通りPaywallスキップ（変更なし） | ✅ |

## As-Is / To-Be

### 変更1: DEBUGリセットボタン（MyPathTabView.swift:332-334）

**As-Is:**
```swift
Button {
    appState.setAuthStatus(.signedOut)
    appState.updateSubscriptionInfo(.free)
}
```
→ オンボーディング未リセット、RevenueCat未ログアウト。ボタン押してもメイン画面のまま。

**To-Be:**
```swift
Button {
    appState.signOutPreservingSensorAccess()
}
```
→ `signOutPreservingSensorAccess()` がオンボーディング、サブスク、RevenueCat、通知、Mixpanelを全リセット。

### 変更2: Offering ID（Production.xcconfig:5, Staging.xcconfig:5）

**As-Is:**
```
REVENUECAT_PAYWALL_ID = Anicca Monthly
```

**To-Be:**
```
REVENUECAT_PAYWALL_ID = ofrngbf9a09cfea
```

### 変更3: Product ID（SubscriptionManager.swift:262）

**As-Is:**
```swift
case "ai.anicca.app.ios.monthly":
```

**To-Be:**
```swift
case "prod8eb90326e4":
```

### 既存変更: OnboardingFlowView.swift（前ステップで実装済み）

```swift
#if DEBUG
// DEBUG: 常にPaywallを表示して確認可能にする
#else
if appState.subscriptionInfo.isEntitled {
    appState.markOnboardingComplete()
    return
}
#endif
```
→ この変更は既にdevに入っている。Specの範囲外だが、AC3の前提条件。

## テストマトリックス

| # | To-Be | テスト方法 | カバー |
|---|-------|-----------|--------|
| 1 | DEBUGリセットでオンボーディングリセット | ボタンタップ→オンボーディング画面に戻ることを確認 | ✅ |
| 2 | DEBUGリセットでRevenueCatログアウト | `signOutPreservingSensorAccess()` が `SubscriptionManager.handleLogout()` を呼ぶ | ✅ |
| 3 | 新Offering IDでPaywall表示 | オンボーディング完了後、新デザインのPaywallが表示される | ✅ |
| 4 | 新Product IDで名前表示 | サブスク情報画面でプラン名が正しく表示される | ✅ |
| 5 | Releaseビルドでは既存Proスキップ | `#if DEBUG` により本番は既存ロジック維持 | ✅ |

## 境界

### 触るファイル
- `aniccaios/aniccaios/Views/MyPathTabView.swift`（DEBUGボタン修正: 2行→1行）
- `aniccaios/Configs/Production.xcconfig`（Offering ID: 1行）
- `aniccaios/Configs/Staging.xcconfig`（Offering ID: 1行）
- `aniccaios/Services/SubscriptionManager.swift`（Product ID: 1行）

### やらないこと
- Releaseビルドのロジック変更
- 新しいテストファイル追加（変更が小さいため、実機確認で十分）
- OnboardingFlowView.swift（前ステップで修正済み）

## 実行手順

```bash
# ビルド
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane build_for_simulator

# 確認フロー
# 1. アプリ起動 → メイン画面
# 2. My Path タブ → 下スクロール → DEBUG: "Reset to Free + Signed Out" タップ
# 3. オンボーディング開始（welcome画面）を確認
# 4. welcome → value → struggles → notifications を進める
# 5. Paywall表示を確認（新デザイン、ofrngbf9a09cfea）
```
