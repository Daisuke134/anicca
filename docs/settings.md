# RevenueCat & Railway 設定情報

このドキュメントには、RevenueCatとRailwayの設定情報を記録しています。今後の開発で参照するためのベース情報です。

## Railway環境変数

### Production環境

```
REVENUECAT_CUSTOMER_CENTER_ID=default
REVENUECAT_ENTITLEMENT_ID=entlb820c43ab7
REVENUECAT_PAYWALL_ID=anicca
REVENUECAT_PROJECT_ID=projbb7b9d1b
REVENUECAT_REST_API_KEY=sk_MbPWvasajZsBPaYhxnLUufGtUxjxn
REVENUECAT_VC_CODE=anicca
REVENUECAT_WEBHOOK_SECRET=<REDACTED_ROTATED_2026-05-21>
```

### Staging環境

```
REVENUECAT_CUSTOMER_CENTER_ID=default
REVENUECAT_ENTITLEMENT_ID=entlb820c43ab7
REVENUECAT_PAYWALL_ID=anicca
REVENUECAT_PROJECT_ID=projbb7b9d1b
REVENUECAT_REST_API_KEY=sk_MbPWvasajZsBPaYhxnLUufGtUxjxn
REVENUECAT_VC_CODE=anicca
REVENUECAT_WEBHOOK_SECRET=<REDACTED_ROTATED_2026-05-21>
```

## RevenueCat APIキー設定

### Secret API Keys

- **ラベル名**: `anicca2`
- **キー値**: `sk_MbPWvasajZsBPaYhxnLUufGtUxjxn`
- **用途**: REST API v2用

### SDK API Keys

- **Test Store**: `test_InOtDYNvBLQqzbPoTMCOOBeXdJi`
- **Production (anicca)**: `appl_AyTtJmtNsepVIgvJovlHkYdGfqF`

## RevenueCat APIキー権限設定

### Customers Configuration Permissions

- **Permission Type**: Custom
- **Customers Configuration**: Read & write
- **Subscriptions Configuration**: Read only
- **Purchases Configuration**: Read only
- **Invoices Configuration**: Read only

### Project Configuration Permissions

- **Permission Type**: Read only
- **Projects Configuration**: Read only
- **Apps Configuration**: Read only
- **Entitlements Configuration**: Read only
- **Offerings Configuration**: Read only
- **Packages Configuration**: Read only
- **Products Configuration**: Read only

## RevenueCat Webhook設定

### Production Webhook

- **URL**: `https://anicca-proxy-production.up.railway.app/api/billing/webhook/revenuecat`
- **Environment**: Only for Production
- **Webhook Secret**: `<REDACTED_ROTATED_2026-05-21>`

### Staging Webhook

- **URL**: `https://anicca-proxy-staging.up.railway.app/api/billing/webhook/revenuecat`
- **Environment**: Only for Sandbox
- **Webhook Secret**: `<REDACTED_ROTATED_2026-05-21>`

## RevenueCat設定値

- **Entitlement ID**: `entlb820c43ab7`
- **Paywall ID**: `anicca`
- **Project ID**: `projbb7b9d1b`
- **Customer Center ID**: `default`
- **Virtual Currency Code**: `anicca`

## iOS App設定

### Production環境 (Production.xcconfig)

```
ANICCA_PROXY_BASE_URL = https://anicca-proxy-production.up.railway.app/api
REVENUECAT_API_KEY = appl_AyTtJmtNsepVIgvJovlHkYdGfqF
REVENUECAT_ENTITLEMENT_ID = entlb820c43ab7
REVENUECAT_PAYWALL_ID = anicca
REVENUECAT_CUSTOMER_CENTER_ID = default
```

### Staging環境 (Staging.xcconfig)

```
ANICCA_PROXY_BASE_URL = https://anicca-proxy-staging.up.railway.app/api
REVENUECAT_API_KEY = test_InOtDYNvBLQqzbPoTMCOOBeXdJi
REVENUECAT_ENTITLEMENT_ID = entlb820c43ab7
REVENUECAT_PAYWALL_ID = anicca
REVENUECAT_CUSTOMER_CENTER_ID = default
```

## Product ID

### 本番環境

- **月額**: `ai.anicca.app.ios.monthly`
- **年額**: `ai.anicca.app.ios.annual`

### テスト環境

- **月額**: `monthly`
- **年額**: `yearly`

---

## 重要な情報（技術的な注意点）

### APIキーの形式について

- REST API v2では`Authorization: Bearer ${API_KEY}`形式を使用
- 環境変数には`Bearer`を含めない（コード側で付与）
- Webhook Secretは`Bearer`不要（別の認証方式）

### WebhookのAPIバージョンについて

- Webhookの`api_version: "1.0"`は正常（REST API v2とは独立）
- Webhookフォーマットは現在`1.0`が標準
- REST API v2への移行とは別の仕組み

### Railway側の設定について

- WebhookエンドポイントはRailway側で追加設定不要
- RevenueCatからRailwayのエンドポイントにPOSTが送られる
- 通常のHTTPエンドポイントとして動作

### Environment設定の意味

- **Only for Production**: App Store/Google Playの本番環境のイベントのみ
- **Only for Sandbox**: TestFlight/内部テスト/サンドボックス環境のイベントのみ
- **All**: 両方の環境のイベント

### APIキー権限について

- 現在の`Read only`設定で問題なし（エンタイトルメント取得のみ）
- Write権限は通常不要（サブスクリプションはApp Store/Google Play経由で管理）
- テスト目的でWrite権限が必要な場合は、テスト用APIキーを別途作成

### 修正パッチの適用範囲

- **PaywallContainerView.swift**: `.onRestoreCompleted`処理追加、エラーハンドリング強化
- **SubscriptionManager.swift**: サーバー同期後のCustomerInfo再取得
- **apps/api/src/services/revenuecat/api.js**: エラーハンドリングとログ出力の強化

---

## 更新履歴

- 2025-11-22: 初版作成（RevenueCat課金機能リリース準備時）











