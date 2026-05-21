# RevenueCat課金機能をメインブランチにマージ

## 目的

現在のワークツリー（`2025-11-10-oqf6-I8dlb`）にあるRevenueCat課金機能を、メインブランチにマージします。メインブランチは最新でApp Store申請済みのため、課金機能に関連するファイルのみを追加・更新します。

## マージ対象ファイル

### iOSアプリ側（aniccaios/）

**新規ファイル（追加）：**

- `aniccaios/aniccaios/Services/SubscriptionManager.swift` - RevenueCat初期化・管理
- `aniccaios/aniccaios/Components/PaywallContainerView.swift` - ペイウォールUI
- `aniccaios/aniccaios/Views/SubscriptionRequiredView.swift` - サブスクリプション必須ビュー
- `aniccaios/aniccaios/Models/SubscriptionInfo.swift` - サブスクリプション情報モデル

**既存ファイル（更新）：**

- `aniccaios/aniccaios/Config.swift` - RevenueCat設定値追加
- `aniccaios/aniccaios/AppDelegate.swift` - SubscriptionManager初期化追加
- `aniccaios/aniccaios/AppState.swift` - subscriptionInfoプロパティ追加
- `aniccaios/aniccaios/SettingsView.swift` - 課金UI追加
- `aniccaios/aniccaios/Info.plist` - RevenueCatキー追加
- `aniccaios/Configs/Production.xcconfig` - RevenueCat設定追加
- `aniccaios/Configs/Staging.xcconfig` - RevenueCat設定追加

### API側（apps/api/）

**新規ファイル（追加）：**

- `apps/api/src/services/revenuecat/api.js` - RevenueCat APIクライアント
- `apps/api/src/services/revenuecat/webhookHandler.js` - Webhook処理
- `apps/api/src/api/billing/revenuecatSync.js` - サブスクリプション同期エンドポイント
- `apps/api/src/api/billing/webhookRevenueCat.js` - Webhookエンドポイント
- `apps/api/src/routes/billing/revenuecat-sync.js` - ルート定義
- `apps/api/src/routes/billing/webhook/revenuecat.js` - ルート定義
- `apps/api/supabase/migrations/20251110_add_revenuecat_columns.sql` - DBマイグレーション

**既存ファイル（更新）：**

- `apps/api/src/config/environment.js` - RevenueCat設定追加
- `apps/api/src/server.js` - RevenueCat webhookルート追加
- `apps/api/src/services/subscriptionStore.js` - RevenueCat対応追加
- `apps/api/src/routes/billing/index.js` - RevenueCatルート追加

## 実行手順

1. **メインブランチの最新化確認**

- メインブランチが最新であることを確認
- 現在のワークツリーとの差分を最終確認

2. **メインブランチに切り替え**

- メインディレクトリで`main`ブランチにチェックアウト

3. **課金機能ファイルのマージ**

- 新規ファイルをコピー
- 既存ファイルの差分を確認し、課金機能関連の変更のみを適用

4. **Xcodeプロジェクトファイルの更新**

- `project.pbxproj`にRevenueCatパッケージ依存関係が追加されているか確認
- 新規ファイルがプロジェクトに追加されているか確認

5. **動作確認**

- ビルドエラーがないか確認
- マージ後の差分を確認

6. **コミット・プッシュ**

- 変更をコミット
- メインブランチにプッシュ

## 注意事項

- メインブランチの既存機能を壊さないよう注意
- 課金機能以外の変更は含めない
- Xcodeプロジェクトファイルのマージは慎重に行う
- ビルド成果物（build/、xcarchive/）は含めない