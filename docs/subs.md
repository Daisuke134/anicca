今から原因箇所を広く洗い出します。まず API 側の課金/制限関連の設定と RevenueCat Webhook を確認し、iOS 側の表示文言/ボタン制約の実装も同時に探します。

[23 tools called]

いまリポジトリ（API と iOS）を広く確認しました。原因箇所を特定できたので、直すための擬似パッチをこのチャットにまとめます。[[memory:11283936]]

### 1) API: ESM SyntaxError（重複関数）修正
```diff
--- a/apps/api/src/services/subscriptionStore.js
+++ b/apps/api/src/services/subscriptionStore.js
@@
-export async function getMonthlyUsage(userId) {
-  const client = requireSupabase();
-  const now = new Date();
-  const firstDay = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
-  const firstDayIso = firstDay.toISOString().slice(0, 10);
-  const { data, error } = await client
-    .from('realtime_usage_daily')
-    .select('usage_date,count')
-    .eq('user_id', userId)
-    .gte('usage_date', firstDayIso);
-  if (error) throw error;
-  return (data || []).reduce((sum, row) => sum + (row.count || 0), 0);
-}
```
- 理由: 同一モジュール内で `export async function getMonthlyUsage` が2回宣言されており、ESM が「すでに宣言済み」として落ちていました。後者の重複を削除するだけで解消します（実装内容は同一）。

### 2) API: 外部キーエラー 23503（`realtime_usage_daily`）の抑止
```diff
--- a/apps/api/src/services/subscriptionStore.js
+++ b/apps/api/src/services/subscriptionStore.js
@@
 export async function incrementTodayUsage(userId) {
   const client = requireSupabase();
   const todayIso = new Date().toISOString().slice(0, 10);
+  // auth.users（または users）に存在しない user_id だと FK で落ちるため回避
+  const exists = await supabaseUserExists(userId);
+  if (!exists) {
+    const today = await getTodayUsage(userId);
+    return today?.count || 0;
+  }
   const existing = await getTodayUsage(userId);
   const nextCount = (existing?.count || 0) + 1;
   const { error } = await client
     .from('realtime_usage_daily')
     .upsert({
       user_id: userId,
       usage_date: todayIso,
       count: nextCount,
       updated_at: new Date().toISOString()
     }, { onConflict: 'user_id,usage_date' });
   if (error) throw error;
   return nextCount;
 }
@@
 export async function getEntitlementState(userId) {
   const [subscription, monthlyUsage] = await Promise.all([
     fetchSubscriptionRow(userId),
     getMonthlyUsage(userId)
   ]);
-  const statusInfo = normalizeStatus(subscription?.entitlement_source || ENTITLEMENT_SOURCE.STRIPE, subscription?.status);
+  let statusInfo = normalizeStatus(
+    subscription?.entitlement_source || ENTITLEMENT_SOURCE.STRIPE,
+    subscription?.status
+  );
+  // RevenueCat: キャンセル済でも有効期限内は is_active で PRO 扱いに補正
+  if (
+    subscription?.entitlement_source === 'revenuecat' &&
+    subscription?.current_period_end &&
+    new Date(subscription.current_period_end) > new Date() &&
+    statusInfo.plan === 'free'
+  ) {
+    statusInfo = { ...statusInfo, plan: 'pro' };
+  }
   const limit = resolveMonthlyLimit(statusInfo.plan);
   const count = monthlyUsage || 0;
   const remaining = Math.max(limit - count, 0);
```
- 理由: Supabase 側に存在しない `user_id` で upsert すると FK 違反になるため、存在確認して未作成ならカウントだけ返して挿入をスキップします。また RevenueCat の「解約予約（willRenew=false）」を即 Free 扱いにしてしまう問題を補正し、期限内は PRO 上限（例: 300）を適用します。

### 3) API: RevenueCat Webhook の plan/status 正規化
```diff
--- a/apps/api/src/services/revenuecat/webhookHandler.js
+++ b/apps/api/src/services/revenuecat/webhookHandler.js
@@
 export async function applyRevenueCatEntitlement(userId, entitlements) {
   const entitlement = entitlements[BILLING_CONFIG.REVENUECAT_ENTITLEMENT_ID];
   const supabase = requireSupabase();
-  const status = entitlement?.period_type === 'trial' ? 'trialing' : (entitlement?.unsubscribe_detected_at ? 'canceled' : 'active');
+  const isActive = entitlement?.is_active === true;
+  const isTrial = entitlement?.period_type === 'trial';
+  // 解約予約でも有効期限までは active として扱う（上限は PRO）
+  const status = isActive ? (isTrial ? 'trialing' : 'active') : 'expired';
   const payload = {
     user_id: userId,
-    plan: entitlement?.is_active ? 'pro' : 'free',
+    plan: isActive ? 'pro' : 'free',
     status,
     current_period_end: entitlement?.expires_date || null,
     entitlement_source: 'revenuecat',
     revenuecat_entitlement_id: BILLING_CONFIG.REVENUECAT_ENTITLEMENT_ID,
     revenuecat_original_transaction_id: entitlement?.original_transaction_id || null,
     entitlement_payload: entitlement || null,
     updated_at: new Date().toISOString()
   };
   await supabase.from('user_subscriptions').upsert(payload, { onConflict: 'user_id' });
 }
```
- 理由: これまでは `unsubscribe_detected_at` を見て即 `status='canceled'` にしていたため、`normalizeStatus` が Free に落とし込み、上限が 30 になっていました。解約予約は「有効期限までは active」として扱い、上限 300 を維持します。

### 4) iOS: 英語表示＆文言ローカライズ（「こんげつ」直し）
```diff
--- a/aniccaios/aniccaios/SettingsView.swift
+++ b/aniccaios/aniccaios/SettingsView.swift
@@
-                        if let limit = appState.subscriptionInfo.monthlyUsageLimit,
-                           let remaining = appState.subscriptionInfo.monthlyUsageRemaining,
-                           let count = appState.subscriptionInfo.monthlyUsageCount {
-                            Text("こんげつ: \(count) / \(limit) 回")
+                        if let limit = appState.subscriptionInfo.monthlyUsageLimit,
+                           let remaining = appState.subscriptionInfo.monthlyUsageRemaining,
+                           let count = appState.subscriptionInfo.monthlyUsageCount {
+                            Text(String(format: NSLocalizedString("settings_usage_this_month_format", comment: ""), count, limit))
                                 .font(.subheadline)
                                 .foregroundStyle(.secondary)
                             ProgressView(value: Double(count), total: Double(limit))
                                 .progressViewStyle(.linear)
                         }
```

新規追加（ローカライズ定義）:
```diff
+++ b/aniccaios/aniccaios/en.lproj/Localizable.strings
+"settings_usage_this_month_format" = "This month: %d / %d";
+"settings_subscription_canceled_until" = "Canceled — ends on %@";

+++ b/aniccaios/aniccaios/ja.lproj/Localizable.strings
+"settings_usage_this_month_format" = "今月: %d / %d 回";
+"settings_subscription_canceled_until" = "キャンセル済 — %@で終了";
```
- 理由: 固定日本語を排し、システム言語に追従。英語環境で「This month」に、 日本語は「今月」に統一されます。

### 5) iOS: キャンセル状態の即時表示（「終了日まで有効」）
```diff
--- a/aniccaios/aniccaios/Models/SubscriptionInfo.swift
+++ b/aniccaios/aniccaios/Models/SubscriptionInfo.swift
@@
 struct SubscriptionInfo: Codable, Equatable {
   enum Plan: String, Codable { case free, grace, pro }
   var plan: Plan
   var status: String
   var currentPeriodEnd: Date?
   var managementURL: URL?
   var lastSyncedAt: Date
   var productIdentifier: String?
   var planDisplayName: String?
   var priceDescription: String?
   var monthlyUsageLimit: Int?
   var monthlyUsageRemaining: Int?
   var monthlyUsageCount: Int?
+  // 解約予約（willRenew=false）かどうか
+  var willRenew: Bool?
@@
   var isEntitled: Bool { plan == .pro && status != "expired" }
```

```diff
--- a/aniccaios/aniccaios/Services/SubscriptionManager.swift
+++ b/aniccaios/aniccaios/Services/SubscriptionManager.swift
@@
 extension SubscriptionInfo {
     init(info: CustomerInfo) {
         let configuredId = AppConfig.revenueCatEntitlementId
         let primaryEntitlement = info.entitlements[configuredId]
         let fallbackEntitlement = info.entitlements.active.values.first
         let entitlement = primaryEntitlement ?? fallbackEntitlement
@@
-        self.init(
+        let willRenew = entitlement?.willRenew ?? false
+        let isTrial = entitlement?.periodType == .trial
+        let statusString: String
+        if entitlement?.isActive == true {
+            statusString = isTrial ? "trialing" : (willRenew ? "active" : "canceled")
+        } else {
+            statusString = "expired"
+        }
+        self.init(
             plan: plan,
-            status: entitlement.map { String(describing: $0.verification) } ?? "unknown",
+            status: statusString,
             currentPeriodEnd: entitlement?.expirationDate,
             managementURL: info.managementURL,
             lastSyncedAt: .now,
             productIdentifier: productId,
             planDisplayName: package?.storeProduct.localizedTitle ?? entitlement?.productIdentifier,
             priceDescription: package?.localizedPriceString,
             monthlyUsageLimit: nil,
             monthlyUsageRemaining: nil,
-            monthlyUsageCount: nil
+            monthlyUsageCount: nil,
+            willRenew: willRenew
         )
     }
 }
```

```diff
--- a/aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift
+++ b/aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift
@@
-            .toolbar {
-                ToolbarItem(placement: .navigationBarTrailing) {
-                    Button {
-                        dismiss()
-                    } label: {
-                        Image(systemName: "xmark.circle.fill")
-                            .foregroundStyle(.secondary)
-                    }
-                }
-            }
+            .toolbar {
+                ToolbarItem(placement: .navigationBarTrailing) {
+                    Button {
+                        dismiss()
+                    } label: {
+                        Image(systemName: "xmark.circle.fill")
+                            .foregroundStyle(.secondary)
+                            .frame(width: 24, height: 24) // AutoLayout 警告を抑止
+                    }
+                }
+            }
@@
-                if let date = appState.subscriptionInfo.currentPeriodEnd {
-                    Text(String(format: NSLocalizedString("settings_subscription_until", comment: ""), dateFormatter.string(from: date)))
+                if let date = appState.subscriptionInfo.currentPeriodEnd {
+                    if appState.subscriptionInfo.willRenew == false {
+                        Text(String(format: NSLocalizedString("settings_subscription_canceled_until", comment: ""), dateFormatter.string(from: date)))
+                            .font(.caption)
+                            .foregroundStyle(.secondary)
+                    } else {
+                        Text(String(format: NSLocalizedString("settings_subscription_until", comment: ""), dateFormatter.string(from: date)))
+                            .font(.caption)
+                            .foregroundStyle(.secondary)
+                    }
-                        .font(.caption)
-                        .foregroundStyle(.secondary)
                 }
```
- 理由: RevenueCat の `willRenew=false` を UI に反映し、「キャンセル済—終了日」を即時表示。ツールバーのボタンに固定サイズを与えて、表示直後の AutoLayout 警告（幅=0 由来）を抑止します。

---

### 6) 事象ごとの説明（要点）
- 「Active のまま 0/30 回になる」: RevenueCat の解約予約を `canceled` として Free 扱いにしていたため。上記 API パッチで「期限内は PRO（300）を適用」します。
- 「Cancel したのに Active と出る」: Apple の購読管理 UI は「期限到来まで Active 表示」が仕様。アプリ内では上記 iOS パッチで「キャンセル済—終了日」を明示します。
- 「Annual と Monthly が同時に出る」: App Store Connect で同一サブスクリプショングループに設定されていない可能性が高いです。Annual/Monthly を同一グループに統合し、RevenueCat の Entitlement で両 Product をひとつの Entitlement に割当ててください（そうすれば同時保持はできません）。
- 「Request a refund が接続できない」: サンドボックスでは Apple 側の `reportaproblem.apple.com` が常時対応していないことがあり、表示不可になることがあります（本番では解消されます）。RevenueCat の Customer Center からの返金導線も Apple 側可用性に依存します。
- コンソールの XPC/RunningBoard ログ: iOS 17/18 でよく出る OS ログで、機能上の問題ではありません（無害）。

---

### 実施順序（最短）
1) API を上記 1〜3 のとおり修正して再デプロイ（Railway 環境変数は PRO=300, FREE=30 のまま）。  
2) iOS を 4〜5 のとおり修正してビルドし、英語環境で「This month: 0 / 300」など正しく表示されることを確認。  
3) App Store Connect のサブスク構成（グループ）を確認・統一。  

必要なら、このまま実編集とデプロイまで進めます。

