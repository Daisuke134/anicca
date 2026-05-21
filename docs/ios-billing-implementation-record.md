# iOS課金機能実装記録

## 概要
iOSアプリ（aniccaios）の課金機能実装に関する設定・実装内容の記録。

## RevenueCat設定

### API Keys
- **Production SDK API Key**: `appl_AyTtJmtNsepVIgvJovlHkYdGfqF`
  - RevenueCat ID: `app511ef26659`
  - 用途: 本番環境（App Store提出用）
- **Test Store SDK API Key**: `test_InOtDYNvBLQqzbPoTMCOOBeXdJi`
  - RevenueCat ID: `appa9055e3436`
  - 用途: ステージング環境（サンドボックステスト用）
- **Secret API Key (V2)**: `sk_MbPWvasajZsBPaYhxnLUufGtUxjxn`
  - 用途: バックエンド（Railway）でのREST API呼び出し用

### Project ID
- `projbb7b9d1b`

### Entitlement ID
- `entlb820c43ab7`

### Paywall ID
- `anicca`

**注意**: RevenueCatダッシュボードには2種類のIDが表示されます
- **Offering Identifier**: `anicca`（SDKで使用、`REVENUECAT_PAYWALL_ID`に設定）
- **RevenueCat ID**: `ofrng78a01eb506`（REST API用の内部ID、SDKでは使用しない）

### Customer Center ID
- `default`

### Virtual Currency
- **Currency Code**: `CREDIT`（環境変数`REVENUECAT_VC_CODE`で設定、デフォルトは`CREDIT`）
- **Associated Products**:
  - `ai.anicca.app.ios.monthly`（月額プラン）
    - Purchase amount: 300分
    - Trial amount: 300分
    - Expiration: At the end of the billing cycle
  - `ai.anicca.app.ios.annual`（年額プラン）- **推奨: 追加設定**
    - Purchase amount: 3600分（年額、月次300分×12ヶ月相当）
    - Trial amount: 3600分
    - Expiration: At the end of the billing cycle

## App Store Connect設定

### サブスクリプショングループ
- **グループ名**: （設定済み）
- **サブスクリプション**:
  - `ai.anicca.app.ios.monthly`（月額プラン）- 審査待ち
  - `ai.anicca.app.ios.annual`（年額プラン）- 審査待ち

### 注意事項
- **アプリ内課金**項目は空で問題ありません（サブスクリプショングループがあれば不要）
- サブスクリプションは「審査待ち」状態でApp Store提出可能
- 審査通過後、本番の決済が可能になります

## スキーム設定

### ステージングスキーム（aniccaios-staging）
- **Proxy URL**: `https://anicca-proxy-staging.up.railway.app/api`
- **RevenueCat API Key**: `test_InOtDYNvBLQqzbPoTMCOOBeXdJi`（Test Store）
- **用途**: サンドボックス環境でのテスト用

### メインスキーム（aniccaios）
- **Proxy URL**: `https://anicca-proxy-production.up.railway.app/api`
- **RevenueCat API Key**: `appl_AyTtJmtNsepVIgvJovlHkYdGfqF`（Production）
- **用途**: 本番環境（App Store提出用）

## Railway環境変数設定

### ステージング環境
- `REVENUECAT_PROJECT_ID`: `projbb7b9d1b`
- `REVENUECAT_REST_API_KEY`: `sk_MbPWvasajZsBPaYhxnLUufGtUxjxn`
- `REVENUECAT_ENTITLEMENT_ID`: `entlb820c43ab7`
- `REVENUECAT_PAYWALL_ID`: `anicca`
- `REVENUECAT_CUSTOMER_CENTER_ID`: `default`
- `REVENUECAT_VC_CODE`: `anicca`
- `REVENUECAT_WEBHOOK_SECRET`: `<REDACTED_ROTATED_2026-05-21>`

### 環境変数（利用制限）
- `FREE_MONTHLY_LIMIT`: `30`（無料プランの月次利用制限、分単位）
- `PRO_MONTHLY_LIMIT`: `300`（有料プランの月次利用制限、分単位）

### 本番環境
- `REVENUECAT_PROJECT_ID`: `projbb7b9d1b`
- `REVENUECAT_REST_API_KEY`: `sk_MbPWvasajZsBPaYhxnLUufGtUxjxn`
- `REVENUECAT_ENTITLEMENT_ID`: `entlb820c43ab7`
- `REVENUECAT_PAYWALL_ID`: `anicca`
- `REVENUECAT_CUSTOMER_CENTER_ID`: `default`
- `REVENUECAT_VC_CODE`: `anicca`
- `REVENUECAT_WEBHOOK_SECRET`: `<REDACTED_ROTATED_2026-05-21>`

### 環境変数（利用制限）
- `FREE_MONTHLY_LIMIT`: `30`（無料プランの月次利用制限、分単位）
- `PRO_MONTHLY_LIMIT`: `300`（有料プランの月次利用制限、分単位）

## 実装ファイル

### iOSアプリ側
- `aniccaios/Configs/Staging.xcconfig`: ステージング環境の設定
- `aniccaios/Configs/Production.xcconfig`: 本番環境の設定
- `aniccaios/aniccaios/Components/PaywallContainerView.swift`: Paywall表示コンポーネント
- `aniccaios/aniccaios/Services/SubscriptionManager.swift`: RevenueCat SDKの初期化・管理
- `aniccaios/aniccaios/Extensions/Offering+SafeAccess.swift`: Offering拡張（0除算エラー回避）

### バックエンド側
- `apps/api/src/services/revenuecat/virtualCurrency.js`: Virtual currencyの付与・消費処理
- `apps/api/src/services/revenuecat/webhookHandler.js`: RevenueCat Webhookハンドラー
- `apps/api/src/services/revenuecat/api.js`: RevenueCat REST API呼び出し
- `apps/api/src/jobs/monthlyCredits.js`: 月次Virtual currency付与ジョブ

## 環境変数の設定場所

### Railway環境変数
- `FREE_MONTHLY_LIMIT`: 無料プランの月次利用制限（分単位、デフォルト: 30）
- `PRO_MONTHLY_LIMIT`: 有料プランの月次利用制限（分単位、デフォルト: 300）

## 既知の問題と対処法

### Division by zeroエラー
- **原因**: RevenueCatUIの`CarouselComponentView`で、Paywallに商品が正しく設定されていない場合に発生
- **対処法**: `Offering+SafeAccess.swift`で`containsEmptyCarousel`を実装し、商品が空の場合はPaywallViewを表示しない

### Paywall IDの混同
- **原因**: RevenueCatダッシュボードに2種類のIDが表示されるため混同しやすい
- **対処法**: SDKではOffering Identifier（`anicca`）を使用し、RevenueCat ID（`ofrng78a01eb506`）はREST API専用

### Test Store環境でのエラー
- **"The receipt is not valid"**: Test Store環境では正常な動作（無視してOK）
- **RevenueCat.BackendError error 0**: Test Store環境では正常な動作（無視してOK）
- **quic_migration_fallback**: ネットワーク関連の警告（無視してOK）

## App Store提出時の注意事項

### 署名設定
- **開発中**: Apple Development証明書で問題ありません
- **App Store提出時**: Archive作成時に自動でDistribution証明書に切り替わります（手動変更不要）

### 審査要件
1. Paywall画面が表示される
2. サブスクリプション購入フローが動作する（実際の決済は発生しない）
3. キャンセル機能が動作する
4. アップグレード/ダウングレードが動作する
5. 無料プランの上限到達時の処理が動作する
6. 有料プランの上限到達時の処理が動作する

### 提出方法
- **メインスキーム（Production）でビルドして提出**
- ステージングスキームのエラーは無視して問題ありません（Test Store環境の設定問題の可能性が高い）

## RevenueCatダッシュボードでの設定確認事項

### Offering設定
1. Offering Identifierが`anicca`であることを確認
2. OfferingにPackagesが正しく設定されていることを確認
3. 各PackageにProductが紐づいていることを確認

### Virtual Currency設定
1. 月額プラン（`ai.anicca.app.ios.monthly`）にVirtual Currencyが設定されていることを確認
2. 年額プラン（`ai.anicca.app.ios.annual`）にもVirtual Currencyを設定（推奨）

## Virtual Currency実装

### 現在の設定
- 月額プラン（`ai.anicca.app.ios.monthly`）のみ設定済み
  - Purchase amount: 300分
  - Trial amount: 300分
- 年額プラン（`ai.anicca.app.ios.annual`）は未設定（推奨: 追加設定）

### 推奨事項
- **年額プラン（`ai.anicca.app.ios.annual`）も追加することを推奨**
  - ユーザーに選択肢を提供できる
  - 年額の方が単価が安い場合、ユーザーにとってメリットがある
  - RevenueCatのドキュメントでも推奨されている

### 実装方法
1. RevenueCatダッシュボードで、`ai.anicca.app.ios.annual`にもVirtual currencyを設定（例: 3600分/年）
2. Webhookハンドラーでプランタイプを判定し、適切に付与

## 参考リンク
- [RevenueCat Virtual Currencies Documentation](https://www.revenuecat.com/blog/engineering/how-to-monetize-your-ai-app-with-virtual-currencies/)
- [RevenueCat iOS SDK Documentation](https://docs.revenuecat.com/docs/ios)

