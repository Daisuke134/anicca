# App Review Rejection - November 24, 2025

## 概要

2025年11月24日にApp Store審査で4つの指摘を受け、リジェクトされました。本ドキュメントは、すべての対応内容を詳細に記録したものです。

## 審査指摘事項

### 1. Guideline 3.1.2 - Business - Payments - Subscriptions（価格表記の強調順）

**指摘内容:**
> We noticed that one or more of your auto-renewable subscriptions is marketed in the purchase flow in a manner that may mislead or confuse users about the subscription terms or pricing. Specifically:
> - Your auto-renewable subscription displays the monthly calculated pricing for your subscription more clearly and conspicuously than the billed amount.

**問題点:**
- 請求額（billed amount、例: $69.99/yr）よりも月額換算価格（例: $5.83/mo）が目立っていた
- Appleの要件では、請求額が最も明確で目立つ要素である必要がある

### 2. Guideline 2.1 - Performance - App Completeness

**指摘内容:**
> The app exhibited one or more bugs that would negatively impact users.
> Bug description: Aniccaと話す feature did not load properly and finish instantly.
> Review device details:
> - Device type: iPad Air (5th generation)
> - OS version: iPadOS 26.1

**問題点:**
- iPadで音声セッションが即座に終了するバグ

### 3. Guideline 5.1.1(v) - Data Collection and Storage

**指摘内容:**
> The app supports account creation but does not include an option to initiate account deletion. Apps that support account creation must also offer account deletion to give users more control of the data they've shared while using an app.

**問題点:**
- アカウント作成機能があるが、アカウント削除機能がない

### 4. Guideline 3.1.2 - Business - Payments - Subscriptions（法的リンク不足）

**指摘内容:**
> The submission did not include all the required information for apps offering auto-renewable subscriptions.
> The app's binary is missing the following required information:
> - A functional link to the Terms of Use (EULA)
> - A functional link to the privacy policy
> The app's metadata is missing the following required information:
> - A functional link to the Terms of Use (EULA). If you are using the standard Apple Terms of Use (EULA), include a link to the Terms of Use in the App Description.

**問題点:**
- アプリ内にPrivacy PolicyとEULAへの機能的なリンクがない
- App Store Connectのメタデータにもリンクが不足

---

## 対応内容

### 1. Guideline 3.1.2（価格表記の強調順）対応

#### 1.1 新規ファイル作成: `PricingDisclosureBanner.swift`

**ファイルパス:** `aniccaios/aniccaios/Views/PricingDisclosureBanner.swift`

**実装内容:**
- 請求額を特大・太字で表示するバナーコンポーネント
- 月額換算は副次的な表示（小さく、薄い色）
- RevenueCatの`Package`型から請求額テキストを生成するヘルパーメソッド

**主要コード:**
```swift
import SwiftUI
import StoreKit
import RevenueCat

struct PricingDisclosureBanner: View {
    let billedAmountText: String
    let perMonthText: String?
    let noteText: String
    
    var body: some View {
        VStack(spacing: 6) {
            Text(billedAmountText)
                .font(.largeTitle)  // 最も目立つフォントサイズ
                .bold()              // 太字
                .multilineTextAlignment(.center)
            if let perMonthText {
                Text(perMonthText)
                    .font(.subheadline)  // 副次的なサイズ
                    .foregroundColor(.secondary)  // 薄い色
            }
            Text(noteText)
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal)
        .padding(.vertical, 12)
    }
}

extension PricingDisclosureBanner {
    static func billedText(for package: Package) -> String {
        let price = package.storeProduct.localizedPriceString
        if let period = package.storeProduct.subscriptionPeriod {
            switch period.unit {
            case .year:
                return "\(price)/yr (auto-renewing)"
            case .month:
                return "\(price)/mo (auto-renewing)"
            case .week:
                return "\(price)/wk (auto-renewing)"
            default:
                return "\(price) (auto-renewing)"
            }
        }
        return price
    }
    
    static func perMonthText(for package: Package) -> String? {
        guard let period = package.storeProduct.subscriptionPeriod,
              period.unit == .year else {
            return nil
        }
        let price = package.storeProduct.price
        let perMonth = price / 12
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = package.storeProduct.priceLocale?.currencyCode
        formatter.locale = package.storeProduct.priceLocale
        formatter.maximumFractionDigits = 2
        if let formatted = formatter.string(from: NSDecimalNumber(decimal: perMonth)) {
            return "≈ \(formatted)/mo (for comparison)"  // 比較情報として明示
        }
        return nil
    }
}
```

#### 1.2 新規ファイル作成: `LegalLinksView.swift`

**ファイルパス:** `aniccaios/aniccaios/Views/LegalLinksView.swift`

**実装内容:**
- Privacy PolicyとApple Standard EULAへのリンクを常設表示するコンポーネント
- 画面下部に固定表示（safeAreaInset使用）

**主要コード:**
```swift
import SwiftUI

struct LegalLinksView: View {
    var body: some View {
        VStack(spacing: 8) {
            Link("Privacy Policy", destination: URL(string: "https://aniccaai.com/privacy")!)
            Link("Terms of Use (EULA)", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
        }
        .font(.footnote)
        .foregroundColor(.secondary)
        .multilineTextAlignment(.center)
        .padding(.vertical, 8)
        .frame(maxWidth: .infinity)
        .background(.ultraThinMaterial)
    }
}
```

**重要な決定:**
- Apple Standard EULAを採用（`https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`）
- 自社の`/terms`ページではなく、Apple公式のStandard EULAへのリンクを使用

#### 1.3 ファイル修正: `PaywallContainerView.swift`

**ファイルパス:** `aniccaios/aniccaios/Components/PaywallContainerView.swift`

**変更内容:**
- PaywallViewの上部に`PricingDisclosureBanner`を追加
- PaywallViewの下部に`LegalLinksView`をsafeAreaInsetで追加
- RevenueCatUIのPaywallViewはそのまま使用（ラッパーで包む形）

**変更箇所:**
```swift
// 32-69行目付近
} else if let offeringToDisplay = offering
            ?? appState.cachedOffering
            ?? Purchases.shared.cachedOfferings?.offering(identifier: AppConfig.revenueCatPaywallId)
            ?? Purchases.shared.cachedOfferings?.current,
          offeringToDisplay.isSafeToDisplay,
          !offeringToDisplay.availablePackages.isEmpty {
    // Guideline 3.1.2対応: 請求額を最強調、法的リンクを常設
    VStack(spacing: 0) {
        // 上部: 請求額を最も目立つ形で表示
        if let primaryPackage = offeringToDisplay.availablePackages.first {
            PricingDisclosureBanner(
                billedAmountText: PricingDisclosureBanner.billedText(for: primaryPackage),
                perMonthText: PricingDisclosureBanner.perMonthText(for: primaryPackage),
                noteText: "Cancel anytime. Price may vary by region and currency."
            )
        }
        
        // RevenueCatUIのPaywallViewを使用
        PaywallView(offering: offeringToDisplay)
            // ... 既存のコールバック処理 ...
    }
    .safeAreaInset(edge: .bottom) {
        // 下部: 法的リンクを常設
        LegalLinksView()
    }
}
```

#### 1.4 ファイル修正: `ManageSubscriptionSheet.swift`

**ファイルパス:** `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`

**変更内容:**
- サブスクリプション管理画面の下部に`LegalLinksView`を追加

**変更箇所:**
```swift
// 167-200行目付近のactionsSection内
private var actionsSection: some View {
    VStack(spacing: 12) {
        // ... 既存のボタン ...
        
        // Legal links (Guideline 3.1.2)
        LegalLinksView()
    }
}
```

---

### 2. Guideline 2.1（iPad即終了バグ）対応

#### 2.1 ファイル修正: `VoiceSessionController.swift`

**ファイルパス:** `aniccaios/aniccaios/VoiceSessionController.swift`

**変更内容:**
- マイク権限の事前確認を強化（未決定時はリクエストを実行）
- 402エラー（利用上限到達）時の処理を改善
- 接続失敗時も即終了せず、再試行可能な状態にする

**変更箇所:**
```swift
// 91-151行目付近のestablishSessionメソッド
@MainActor
private func establishSession(resumeImmediately: Bool) async {
    // マイクロフォン権限チェック（WebRTC初期化前に必須）
    // Guideline 2.1対応: iPadでの即終了バグ修正のため、権限チェックを強化
    let hasPermission: Bool
    if #available(iOS 17.0, *) {
        let status = AVAudioApplication.shared.recordPermission
        if status == .undetermined {
            // 未決定の場合はリクエスト
            let granted = await withCheckedContinuation { continuation in
                AVAudioApplication.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
            hasPermission = granted
        } else {
            hasPermission = status == .granted
        }
    } else {
        let status = AVAudioSession.sharedInstance().recordPermission
        if status == .undetermined {
            let granted = await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
            hasPermission = granted
        } else {
            hasPermission = status == .granted
        }
    }
    
    guard hasPermission else {
        logger.error("Microphone permission not granted")
        setStatus(.disconnected)
        return
    }
    
    setStatus(.connecting)
    
    do {
        let secret = try await obtainClientSecret()
        try AudioSessionCoordinator.shared.configureForRealtime(reactivating: resumeImmediately)
        setupPeerConnection()
        setupLocalAudio()
        try await negotiateWebRTC(using: secret)
        sendSessionUpdate()
    } catch VoiceSessionError.quotaExceeded {
        // 402エラー時はPaywallを表示してセッションを終了
        logger.warning("Quota exceeded, showing paywall")
        await MainActor.run {
            AppState.shared.markQuotaHold(plan: nil)
        }
        setStatus(.disconnected)
    } catch {
        logger.error("Failed to establish session: \(error.localizedDescription, privacy: .public)")
        // 接続失敗時はユーザーに再試行可能な状態にする（即終了しない）
        setStatus(.disconnected)
    }
}
```

**改善点:**
- 権限未決定時に自動的にリクエストを実行
- 402エラー時は適切にPaywallを表示
- その他のエラー時も即終了せず、`.disconnected`状態にして再試行可能に

---

### 3. Guideline 5.1.1(v)（アカウント削除）対応

#### 3.1 ファイル修正: `SettingsView.swift`

**ファイルパス:** `aniccaios/aniccaios/SettingsView.swift`

**変更内容:**
- アカウント削除ボタンを追加
- 確認ダイアログを追加
- 削除API呼び出しとエラーハンドリングを実装

**変更箇所:**

**State変数の追加:**
```swift
@State private var isShowingDeleteAlert = false
@State private var isDeletingAccount = false
@State private var deleteAccountError: Error?
```

**UIの追加:**
```swift
// List内のSection追加
Section {
    Button(role: .destructive) {
        isShowingDeleteAlert = true
    } label: {
        Text("Delete Account")
    }
}
```

**アラートの追加:**
```swift
.alert("Delete Account", isPresented: $isShowingDeleteAlert) {
    Button("Cancel", role: .cancel) {}
    Button("Delete", role: .destructive) {
        Task {
            await deleteAccount()
        }
    }
} message: {
    Text("This action cannot be undone. All your data, including purchase history and usage data, will be permanently deleted.")
}
.alert("Error", isPresented: Binding(
    get: { deleteAccountError != nil },
    set: { if !$0 { deleteAccountError = nil } }
)) {
    Button("OK") {
        deleteAccountError = nil
    }
} message: {
    if let error = deleteAccountError {
        Text(error.localizedDescription)
    }
}
```

**削除処理の実装:**
```swift
private func deleteAccount() async {
    isDeletingAccount = true
    deleteAccountError = nil
    
    guard case .signedIn(let credentials) = appState.authStatus else {
        await MainActor.run {
            deleteAccountError = NSError(domain: "AccountDeletionError", code: 1, userInfo: [NSLocalizedDescriptionKey: "Not signed in"])
            isDeletingAccount = false
        }
        return
    }
    
    var request = URLRequest(url: AppConfig.proxyBaseURL.appendingPathComponent("mobile/account"))
    request.httpMethod = "DELETE"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    request.setValue(AppState.shared.resolveDeviceId(), forHTTPHeaderField: "device-id")
    request.setValue(credentials.userId, forHTTPHeaderField: "user-id")
    
    do {
        let (_, response) = try await NetworkSessionManager.shared.session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NSError(domain: "AccountDeletionError", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
        }
        
        if httpResponse.statusCode == 204 {
            // 削除成功: RevenueCatからログアウトしてアプリ状態をリセット
            await SubscriptionManager.shared.handleLogout()
            await MainActor.run {
                appState.signOutAndWipe()
            }
            await MainActor.run {
                dismiss()
            }
        } else {
            throw NSError(domain: "AccountDeletionError", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: "Server error: \(httpResponse.statusCode)"])
        }
    } catch {
        await MainActor.run {
            deleteAccountError = error
            isDeletingAccount = false
        }
    }
}
```

#### 3.2 ファイル修正: `AppState.swift`

**ファイルパス:** `aniccaios/aniccaios/AppState.swift`

**変更内容:**
- アカウント削除時の完全な状態リセットメソッドを追加

**追加メソッド:**
```swift
// Guideline 5.1.1(v)対応: アカウント削除時の完全な状態リセット
func signOutAndWipe() {
    authStatus = .signedOut
    userProfile = UserProfile()
    subscriptionInfo = .free
    habitSchedules = [:]
    customHabits = []
    customHabitSchedules = [:]
    pendingHabitTrigger = nil
    pendingHabitPrompt = nil
    cachedOffering = nil
    
    // UserDefaultsからすべてのユーザーデータを削除
    defaults.removeObject(forKey: userCredentialsKey)
    defaults.removeObject(forKey: userProfileKey)
    defaults.removeObject(forKey: subscriptionKey)
    defaults.removeObject(forKey: habitSchedulesKey)
    defaults.removeObject(forKey: customHabitsKey)
    defaults.removeObject(forKey: customHabitSchedulesKey)
    
    // 通知をすべてキャンセル
    Task {
        await scheduler.cancelAll()
    }
    
    // RevenueCatからログアウト
    Task {
        await SubscriptionManager.shared.handleLogout()
    }
}
```

#### 3.3 新規ファイル作成: `account.js`（バックエンドAPI）

**ファイルパス:** `apps/api/src/routes/mobile/account.js`

**実装内容:**
- アカウント削除エンドポイント（DELETE /api/mobile/account）
- RevenueCatのSubscriber削除
- データベースからのユーザーデータ完全削除

**主要コード:**
```javascript
import express from 'express';
import requireAuth from '../../middleware/requireAuth.js';
import { deleteSubscriber } from '../../services/revenuecat/api.js';
import { pool } from '../../lib/db.js';

const router = express.Router();

// Guideline 5.1.1(v)対応: アカウント削除
router.delete('/', async (req, res, next) => {
  try {
    const auth = await requireAuth(req, res);
    if (!auth) return;
    const userId = auth.sub;
    
    // RevenueCatのSubscriber削除（App User ID）
    try {
      await deleteSubscriber(userId);
    } catch (error) {
      // RevenueCat削除失敗はログに記録するが、処理は続行
      console.error(`[Account Deletion] Failed to delete RevenueCat subscriber for user ${userId}:`, error);
    }
    
    // アプリDBの削除（pg Poolでトランザクション）
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      // 関連データを削除（外部キー制約の順序に注意）
      await client.query('DELETE FROM usage_sessions WHERE user_id = $1', [userId]);
      await client.query('DELETE FROM profiles WHERE user_id = $1', [userId]);
      await client.query('DELETE FROM devices WHERE user_id = $1', [userId]);
      await client.query('DELETE FROM users WHERE id = $1', [userId]);
      await client.query('COMMIT');
    } catch (e) {
      await client.query('ROLLBACK');
      throw e;
    } finally {
      client.release();
    }
    
    return res.status(204).send();
  } catch (error) {
    console.error('[Account Deletion] Error:', error);
    next(error);
  }
});

export default router;
```

#### 3.4 ファイル修正: `mobile/index.js`（ルーター登録）

**ファイルパス:** `apps/api/src/routes/mobile/index.js`

**変更内容:**
- アカウント削除ルーターを追加

**変更箇所:**
```javascript
import express from 'express';
import realtimeRouter from './realtime.js';
import profileRouter from './profile.js';
import entitlementRouter from './entitlement.js';
import accountRouter from './account.js';  // 追加

const router = express.Router();

router.use('/realtime', realtimeRouter);
router.use('/profile', profileRouter);
router.use('/entitlement', entitlementRouter);
router.use('/account', accountRouter);  // 追加

export default router;
```

#### 3.5 ファイル修正: `revenuecat/api.js`（RevenueCat API）

**ファイルパス:** `apps/api/src/services/revenuecat/api.js`

**変更内容:**
- RevenueCatのSubscriber削除メソッドを追加

**追加メソッド:**
```javascript
// Guideline 5.1.1(v)対応: アカウント削除時にRevenueCatのSubscriberを削除
export async function deleteSubscriber(appUserId) {
  const key = BILLING_CONFIG.REVENUECAT_REST_API_KEY;
  const projectId = BILLING_CONFIG.REVENUECAT_PROJECT_ID;
  
  if (!key || !projectId) {
    logger.error('[RevenueCat] Missing API Key or Project ID for subscriber deletion', { 
      hasKey: !!key, 
      hasProjectId: !!projectId 
    });
    throw new Error('Missing RevenueCat configuration');
  }
  
  // DELETE /v2/projects/{project_id}/customers/{customer_id}
  const url = `${BASE_URL}/projects/${projectId}/customers/${encodeURIComponent(appUserId)}`;
  
  logger.info('[RevenueCat] Deleting subscriber', { appUserId, url });
  
  try {
    const resp = await fetch(url, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${key}`,
        Accept: 'application/json'
      }
    });
    
    if (!resp.ok) {
      const txt = await resp.text().catch(() => '');
      // 404は既に削除済みとして扱う（エラーをthrowしない）
      if (resp.status === 404) {
        logger.info('[RevenueCat] Subscriber already deleted', { appUserId });
        return;
      }
      logger.warn('[RevenueCat] Failed to delete subscriber', { 
        status: resp.status, 
        appUserId, 
        error: txt 
      });
      throw new Error(`RevenueCat API error: ${resp.status} ${txt}`);
    }
    
    logger.info('[RevenueCat] Subscriber deleted successfully', { appUserId });
  } catch (err) {
    logger.error('[RevenueCat] Error deleting subscriber', { 
      error: err.message, 
      appUserId 
    });
    throw err;
  }
}
```

---

### 4. Guideline 3.1.2（法的リンク不足）対応

#### 4.1 アプリ内リンク

**実装済み:**
- `LegalLinksView.swift` を作成し、Privacy PolicyとApple Standard EULAへのリンクを実装
- `PaywallContainerView.swift` と `ManageSubscriptionSheet.swift` に追加

（詳細は「1. Guideline 3.1.2（価格表記の強調順）対応」の1.2と1.4を参照）

#### 4.2 App Store Connectメタデータ設定（手動対応が必要）

**設定が必要な項目:**
1. **Privacy Policy URL:**
   - URL: `https://aniccaai.com/privacy`
   - App Store Connectの「App Privacy」セクションで設定

2. **Terms of Use (EULA):**
   - URL: `https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`
   - App Store Connectの「App Information」セクションの「EULA」フィールドで設定
   - または、App Descriptionの末尾にリンクを追記

**推奨されるApp Description追記:**
```
Privacy Policy: https://aniccaai.com/privacy
Terms of Use (EULA): https://www.apple.com/legal/internet-services/itunes/dev/stdeula/
```

---

## 実装ファイル一覧

### iOS（Swift）

1. **新規作成:**
   - `aniccaios/aniccaios/Views/PricingDisclosureBanner.swift`
   - `aniccaios/aniccaios/Views/LegalLinksView.swift`

2. **修正:**
   - `aniccaios/aniccaios/Components/PaywallContainerView.swift`
   - `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`
   - `aniccaios/aniccaios/VoiceSessionController.swift`
   - `aniccaios/aniccaios/SettingsView.swift`
   - `aniccaios/aniccaios/AppState.swift`

### バックエンド（Node.js/Express）

1. **新規作成:**
   - `apps/api/src/routes/mobile/account.js`

2. **修正:**
   - `apps/api/src/routes/mobile/index.js`
   - `apps/api/src/services/revenuecat/api.js`

---

## コミット履歴

- **コミット1:** `426957d` - Fix App Review issues: pricing disclosure, legal links, iPad bug, account deletion
- **コミット2:** `6f3aba5` - Fix account deletion API: use correct db import path and pg Pool transaction

---

## 審査通過のための最終チェックリスト

### iOS実装
- [x] Paywall上部に請求額を特大・太字で表示
- [x] 月額換算を副次的な表示に
- [x] Paywall下部にPrivacy PolicyとEULAリンクを常設
- [x] サブスクリプション管理画面にも法的リンクを追加
- [x] iPadでの音声セッション即終了バグを修正
- [x] アカウント削除機能を実装

### バックエンド実装
- [x] アカウント削除APIエンドポイントを実装
- [x] RevenueCatのSubscriber削除機能を実装
- [x] データベースからの完全削除を実装

### App Store Connect設定（提出前に必須）
- [ ] Privacy Policy URLを設定: `https://aniccaai.com/privacy`
- [ ] Terms of Use (EULA) URLを設定: `https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`
- [ ] App DescriptionにEULAリンクを追記（推奨）

---

## 重要な決定事項

1. **EULAの採用:**
   - Apple Standard EULAを採用（`https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`）
   - 自社の`/terms`ページではなく、Apple公式のStandard EULAへのリンクを使用
   - ランディングページへの追加は不要（アプリ内リンクとApp Store Connectメタデータで要件を満たす）

2. **Paywall実装方針:**
   - RevenueCatUIのPaywallViewはそのまま使用
   - 外側にラッパーを追加して、請求額の強調と法的リンクを実装
   - RCUI本体を変更しないことで、将来のRevenueCatアップデートへの対応を容易に

3. **アカウント削除の実装:**
   - アプリ内で完全に削除可能（外部サイトへの遷移不要）
   - RevenueCatのSubscriberも削除
   - データベースから完全に削除（トランザクションで整合性を保証）

---

## 参考リンク

- [Apple Standard EULA](https://www.apple.com/legal/internet-services/itunes/dev/stdeula/)
- [App Store Review Guidelines 3.1.2](https://developer.apple.com/app-store/review/guidelines/#subscriptions)
- [App Store Review Guidelines 5.1.1(v)](https://developer.apple.com/app-store/review/guidelines/#data-collection-and-storage)

---

**最終更新:** 2025-11-24
**対応者:** AI Assistant (Composer)
**レビュー対象:** 本ドキュメントは、実装内容のレビューと今後の参考資料として作成されました。











