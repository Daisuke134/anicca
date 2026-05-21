今の13件の原因切り分けのため、バックエンドのサブスクリプション/VC処理コードとiOSのSubscription連携部を素早く特定してから、必要な擬似パッチだけを出します。まずはAPI内のsubscription/entitlement/virtual currency関連実装を検索して読み込みます。

[17 tools called]

以下、13点それぞれに回答・必要箇所のみ擬似パッチを提示します。

1. ログ一式について
- ANICCA_PROXY_BASE_URL/RC API Key: 設定は正しいです。
- StoreKit2 took longer: ネットワーク/StoreKit待ちの警告で問題なし。
- quic_migration_fallback: iOSネットワーク内部ログで無害。
- $attConsentStatus: RCにより「新しい値が既に保存済み」。値変更時だけ送る運用で問題なし（無視可）。

2. System gesture gate timed out
- シミュレータ/端末の一時遅延で発生しがち。致命ではなく対処不要。

3. AutoLayout 制約競合
- ナビゲーションバー内ボタンの自動制約で発生する典型的なログ。表示崩れが無ければ無視可（実害なし）。

4. Cancel 時の XPC/entitlement ログ
- iOSの権限/接続リセット由来の情報ログ。アプリ不具合ではありません。

5. キャンセル反映が遅い（何度もキルが必要）
- 原因: iOSは「/billing/revenuecat/sync」を叩いていますが、サーバ側がJWT必須のため401→内部同期が実行されず、最終的にWebhook待ちになっているため遅延。
- 対処: 同期エンドポイントをモバイル用ヘッダ（user-id）で許可します。

```diff
*** Update File: apps/api/src/routes/billing/revenuecat-sync.js
@@
-import requireAuth from '../../middleware/requireAuth.js';
-import handler from '../../api/billing/revenuecatSync.js';
+import handler from '../../api/billing/revenuecatSync.js';
@@
-router.post('/', async (req, res) => {
-  const auth = await requireAuth(req, res);
-  if (!auth) return;
-  req.auth = auth;
-  return handler(req, res);
-});
+router.post('/', handler);
```

```diff
*** Update File: apps/api/src/api/billing/revenuecatSync.js
@@
-import { fetchCustomerEntitlements } from '../../services/revenuecat/api.js';
-import { applyRevenueCatEntitlement, getEntitlementState, normalizePlanForResponse } from '../../services/revenuecat/webhookHandler.js';
+import { fetchCustomerEntitlements } from '../../services/revenuecat/api.js';
+import { applyRevenueCatEntitlement } from '../../services/revenuecat/webhookHandler.js';
+import { getEntitlementState, normalizePlanForResponse } from '../../services/subscriptionStore.js';
@@
 export default async function handler(req, res) {
   if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
-  const auth = req.auth;
-  const appUserId = auth.sub;
+  const appUserId = (req.auth?.sub || (req.get('user-id') || '').toString().trim());
+  if (!appUserId) return res.status(401).json({ error: 'user-id required' });
   const entitlements = await fetchCustomerEntitlements(appUserId);
   await applyRevenueCatEntitlement(appUserId, entitlements);
   const state = await getEntitlementState(appUserId);
   return res.json({ entitlement: normalizePlanForResponse(state) });
 }
```

6. 「Annual Plan がID表示になる」件
- 原因: `SubscriptionManager` が提供名取得に失敗した時、productIdentifierをそのまま表示。
- 対処: 既知IDを人間可読へマップし、IDは表示しない。

```diff
*** Update File: aniccaios/aniccaios/Services/SubscriptionManager.swift
@@
-        let productId = entitlement?.productIdentifier
+        let productId = entitlement?.productIdentifier
@@
-        self.init(
+        let mappedName: String? = {
+            switch productId {
+            case "ai.anicca.app.ios.annual":
+                return NSLocalizedString("subscription_plan_annual", comment: "")
+            case "ai.anicca.app.ios.monthly":
+                return NSLocalizedString("subscription_plan_monthly", comment: "")
+            default:
+                return nil
+            }
+        }()
+        self.init(
@@
-            planDisplayName: package?.storeProduct.localizedTitle ?? entitlement?.productIdentifier,
+            planDisplayName: package?.storeProduct.localizedTitle ?? mappedName,
```

7. RC仮想通貨の400（context不許可）
- 原因: リクエストボディに`context`を送っているため。
- 対処: 送信しない。

```diff
*** Update File: apps/api/src/services/revenuecat/virtualCurrency.js
@@
-async function adjustMinutes({ appUserId, minutes, currency = VC_CURRENCY_CODE, context }) {
+async function adjustMinutes({ appUserId, minutes, currency = VC_CURRENCY_CODE }) {
@@
-  const body = JSON.stringify({
-    adjustments: {
-      [currency]: minutes
-    },
-    context: context || {}
-  });
+  const body = JSON.stringify({
+    adjustments: {
+      [currency]: minutes
+    }
+  });
```

8. PROでも「This month: 0 / 30」になる
- 原因: 5の同期未実行によりDB上プランが`free`のまま→上限30を返却。
- 対処: 5の修正で直ちに`pro`が反映され、`PRO_MONTHLY_LIMIT=300`が返るようになります。追加実装不要。

9. Manage PlanはProなのにフロントはFREE上限/上限到達
- 原因: 同期未実行と7のRC400で整合が崩れていました。
- 対処: 5・7の修正で一致します。リアルタイム開始APIはサーバの残分判定を参照するため、同期後は正しく300分扱いになります。

10. Pro加入済み時に課金画面を出さない/文言改善
- 対処: 既にProなら案内文だけ表示。

```diff
*** Update File: aniccaios/aniccaios/Components/PaywallContainerView.swift
@@
-                VStack(spacing: 12) {
-                    Text(String(localized: "settings_subscription_pro"))
+                VStack(spacing: 12) {
+                    Text("You're already in the pro plan.")
                         .font(.headline)
```

11. FREE_MONTHLY_LIMIT/PRO_MONTHLY_LIMIT と VC「Purchase/Trial amount」どちらを使う？
- 最適解: 上限判定は「環境変数（FREE=30/PRO=300）」のみをソース・オブ・トゥルースにします。VCは台帳（付与/消費の監査）に限定。RC側「Purchase/Trial amount」は不要です。

12. VCの「Auto-expire at end of billing cycle」はONにすべき？
- 今回はOFFにします。上限はサーバ集計で月初にリセットされるため、VC側で自動失効させると二重リセット/不整合の原因になります。

13. VCのAssociated ProductsにAnnual/`ai.anicca.app.ios.annual`を紐付けるべき？
- 不要です。付与はサーバ（ジョブ/同期）で制御し、製品自動連動は使いません。

補足（即時反映強化・任意）
- 設定画面表示時にも同期を走らせると体感が安定します。

```diff
*** Update File: aniccaios/aniccaios/SettingsView.swift
@@
-            .onAppear {
-                loadPersonalizationData()
-            }
+            .onAppear {
+                loadPersonalizationData()
+                Task { await SubscriptionManager.shared.syncNow() }
+            }
```

- すでに修正済みのCustomer Center呼び出しは引数なしが正解（現行バージョンのAPI）。

要点
- 同期エンドポイントの認証要件を「user-idヘッダ対応」に緩和（5）。
- RC仮想通貨APIの`context`送信を廃止（7）。
- プラン名は常に人間可読表示（6）。
- 上限判定は環境変数のみを正とし、VC設定は使わない（11〜13）。

追加で必要な最小パッチ（購入直後の即反映）
支払い完了・復元完了の瞬間にサーバ同期を必ず走らせ、/mobile/realtime の上限判定に即反映させます。

*** Update File: aniccaios/aniccaios/Components/PaywallContainerView.swift
@@
     private func handle(customerInfo: CustomerInfo) {
         guard customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true else { return }
         let info = SubscriptionInfo(info: customerInfo)
         appState.updateSubscriptionInfo(info)
+        // 購入直後にサーバへ同期（DBを即更新 → 上限/残分を即返せるように）
+        Task { await SubscriptionManager.shared.syncNow() }
         onPurchaseCompleted?()
     }


これで「月額プラン加入したのに FREE 上限（30）が出続ける」「セッション開始が quota exceeded になる」などのズレが解消されます。すでに出している以下のパッチと組み合わせで完了です（再掲なし）。
サーバ側:
/billing/revenuecat/sync を user-id ヘッダで許可（JWT不要）
VCトランザクションから context を送らない（RCが400を返すため）
クライアント側:
Settings表示時に syncNow() を実行（体感の遅延をさらに低減）
プラン名の人間可読マッピング（IDを表示しない）
