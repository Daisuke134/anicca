# モバイルアプリ課金機能のSupabase撤去 → Railway Postgres一本化実装記録

## 概要

2025年11月に実施した、iOSアプリの課金・使用量管理機能の大規模リファクタリング。Supabase依存を完全撤去し、Railway Postgresに一本化した。これにより、外部キー制約エラー（23503）の根本原因を解消し、データストアの整合性を確保した。

---

## 背景と問題

### 発生していた問題

1. **外部キー制約エラー（23503）**
   ```
   Key (user_id)=(a3b3a6c9-3d62-4692-b25d-1c116364b858) is not present in table "users".
   insert or update on table "realtime_usage_daily" violates foreign key constraint
   ```
   - `realtime_usage_daily` テーブルが Supabase の `auth.users` を参照していた
   - モバイルアプリは独自JWT認証を使用しており、Supabase Auth のユーザーIDとは別体系
   - 結果として、存在しない `user_id` で upsert しようとしてエラーが発生

2. **二重データストア管理の複雑化**
   - 認証: 独自JWT（Railway API）
   - プロフィール: Railway Postgres (`mobile_profiles`)
   - 課金/使用量: Supabase (`user_subscriptions`, `realtime_usage_daily`)
   - この分離により、ID不整合と同期漏れが発生しやすかった

3. **ESM SyntaxError（重複関数定義）**
   - `subscriptionStore.js` で `getMonthlyUsage` が2回定義されていた
   - Railway デプロイ時に起動失敗

4. **iOS表示の問題**
   - 英語環境で「こんげつ 0/30 回」と日本語が表示される
   - キャンセル後も「Active」と表示され、終了日が不明確
   - AutoLayout 制約警告が頻発

---

## 解決方針：Railway Postgres一本化

### なぜSupabaseを撤去したか

1. **認証体系の不一致**
   - モバイルアプリは独自JWT認証を使用（`apps/api/src/middleware/requireAuth.js`）
   - Supabase Auth は使用していない
   - したがって、Supabase の `auth.users` テーブルにユーザーが存在しない

2. **データストアの統一**
   - プロフィールデータは既に Railway Postgres で管理（`mobile_profiles`）
   - 課金/使用量データも同じDBで管理することで、整合性を保てる
   - 外部キー制約を設けず、アプリケーション層で整合性を保証する設計に変更

3. **運用の簡素化**
   - Supabase サービスキーの管理が不要になる
   - データベース接続先が1つに統一される
   - マイグレーション管理が単純化される

### 設計原則

- **ユーザーIDの統一**: iOS の `credentials.userId` を唯一の正として、RevenueCat `appUserId` = APIヘッダ `user-id` = DB主キーとして統一
- **外部キー制約なし**: `user_subscriptions` と `realtime_usage_daily` は独立したテーブルとして運用（アプリケーション層で整合性を保証）
- **環境変数による設定**: ハードコードを一切せず、Railway環境変数から読み込む

---

## 実装内容

### 1. データベーススキーマ（Railway Postgres）

#### マイグレーションファイル
**ファイル**: `apps/api/docs/migrations/006_init_billing_tables_on_railway.sql`

```sql
-- Create core billing tables on Railway Postgres
create table if not exists public.user_subscriptions (
  user_id text primary key,
  plan text not null default 'free',
  status text not null default 'free',
  stripe_customer_id text,
  stripe_subscription_id text,
  entitlement_source text not null default 'revenuecat',
  revenuecat_entitlement_id text,
  revenuecat_original_transaction_id text,
  entitlement_payload jsonb,
  current_period_end timestamptz,
  trial_end timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.realtime_usage_daily (
  user_id text not null,
  usage_date date not null,
  count integer not null default 0,
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (user_id, usage_date)
);

create table if not exists public.subscription_events (
  event_id text primary key,
  user_id text,
  type text not null,
  provider text not null default 'revenuecat',
  payload jsonb,
  created_at timestamptz not null default timezone('utc', now())
);
```

**重要な設計判断**:
- `user_id` は `text` 型で、外部キー制約を設けない
- `realtime_usage_daily` の `user_id` も `text` で、`user_subscriptions` への参照を持たない
- アプリケーション層（`subscriptionStore.js`）で整合性を保証

#### マイグレーション自動実行機能

**ファイル**: `apps/api/src/lib/migrate.js`（新規作成）

```javascript
import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { query } from './db.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const MIGRATIONS_DIR = path.resolve(__dirname, '../../docs/migrations');

export async function runMigrationsOnce() {
  // 進捗管理テーブル
  await query(`create table if not exists schema_migrations(
    id text primary key,
    applied_at timestamptz not null default timezone('utc', now())
  )`);

  // 006(今回のRailway用DDL) のみ適用。既存の他SQLは対象外。
  const files = (await fs.readdir(MIGRATIONS_DIR))
    .filter(f => /^006_.*\.sql$/.test(f))
    .sort();

  for (const f of files) {
    const id = f;
    const done = await query('select 1 from schema_migrations where id=$1', [id]);
    if (done.rowCount) continue;
    const sql = await fs.readFile(path.join(MIGRATIONS_DIR, f), 'utf8');
    // 単純セミコロン分割で逐次実行（関数等は含まれない前提）
    const statements = sql
      .split(/;\s*\n/gm)
      .map(s => s.trim())
      .filter(Boolean);
    for (const stmt of statements) {
      await query(stmt);
    }
    await query('insert into schema_migrations(id) values($1)', [id]);
  }
}
```

**サーバ起動時に実行**:
**ファイル**: `apps/api/src/server.js`

```javascript
import { runMigrationsOnce } from './lib/migrate.js';

// マイグレーション（初回のみ実行）
await runMigrationsOnce();
```

---

### 2. API側の変更

#### subscriptionStore.js の全面書き換え

**ファイル**: `apps/api/src/services/subscriptionStore.js`

**変更内容**:
- Supabase クライアントのインポートと初期化を削除
- すべての関数を Railway Postgres の `query()` 関数に置き換え
- `supabaseUserExists()` 関数を削除（不要になった）

**主な変更点**:

1. **fetchSubscriptionRow()**
   ```javascript
   // 変更前: Supabase client
   const { data, error } = await client.from('user_subscriptions')...
   
   // 変更後: Railway Postgres
   const r = await query('select * from user_subscriptions where user_id = $1 limit 1', [userId]);
   return r.rows[0] || null;
   ```

2. **incrementTodayUsage()**
   ```javascript
   // 変更前: Supabase upsert（FK制約エラーの原因）
   await client.from('realtime_usage_daily').upsert(...)
   
   // 変更後: Railway Postgres（FK制約なし）
   await ensureSubscriptionRow(userId); // 事前にレコードを保証
   const r = await query(
     `insert into realtime_usage_daily (user_id, usage_date, count, updated_at)
      values ($1, current_date, 1, timezone('utc', now()))
      on conflict (user_id, usage_date)
      do update set count = realtime_usage_daily.count + 1,
                    updated_at = timezone('utc', now())
      returning count`,
     [userId]
   );
   ```

3. **getMonthlyUsage()**
   ```javascript
   // 変更前: Supabase client
   const { data, error } = await client.from('realtime_usage_daily')...
   
   // 変更後: Railway Postgres
   const r = await query(
     `select coalesce(sum(count),0) as total
      from realtime_usage_daily
      where user_id=$1
        and usage_date >= date_trunc('month', (now() at time zone 'utc'))::date`,
     [userId]
   );
   return Number(r.rows[0]?.total || 0);
   ```

4. **getEntitlementState() の解約予約対応**
   ```javascript
   // RevenueCat: 解約予約でも有効期限までは PRO として扱う
   if (
     subscription?.entitlement_source === 'revenuecat' &&
     subscription?.current_period_end &&
     new Date(subscription.current_period_end) > new Date() &&
     statusInfo.plan === 'free'
   ) {
     statusInfo = { ...statusInfo, plan: 'pro' };
   }
   ```
   - これにより、解約予約後も有効期限までは PRO 上限（300回）が適用される

5. **重複関数定義の削除**
   - `getMonthlyUsage()` が2回定義されていた問題を修正（239行目の重複を削除）

#### RevenueCat Webhook Handler の変更

**ファイル**: `apps/api/src/services/revenuecat/webhookHandler.js`

**変更内容**:
- Supabase クライアントを削除し、Railway Postgres の `query()` に置き換え
- 解約予約（`willRenew=false`）の扱いを修正

**主な変更点**:

```javascript
// 変更前: Supabase
const status = entitlement?.period_type === 'trial' ? 'trialing' : (entitlement?.unsubscribe_detected_at ? 'canceled' : 'active');

// 変更後: Railway + 解約予約の正規化
const isActive = entitlement?.is_active === true;
const isTrial = entitlement?.period_type === 'trial';
const status = isActive ? (isTrial ? 'trialing' : 'active') : 'expired';
```

**理由**: `unsubscribe_detected_at` があると即座に `canceled` にしてしまい、`normalizeStatus()` が `free` に変換してしまう。解約予約でも有効期限までは `active` として扱い、PRO上限を維持する。

#### Stripe Webhook Handler の変更

**ファイル**: `apps/api/src/services/stripe/webhookHandler.js`

**変更内容**:
- `supabaseUserExists` のインポートと使用箇所をすべて削除

```javascript
// 変更前
import { supabaseUserExists } from '../subscriptionStore.js';
if (!(await supabaseUserExists(userId))) return;

// 変更後
// インポート削除、ガード削除（Railway Postgres は FK制約がないため不要）
```

#### 環境変数設定の変更

**ファイル**: `apps/api/src/config/environment.js`

**変更内容**:
- Supabase 関連の警告チェックを無効化

```javascript
// 変更前
if (!API_KEYS.SUPABASE_URL || !API_KEYS.SUPABASE_SERVICE_ROLE_KEY) {
  warnings.push('Supabase credentials are not set');
}

// 変更後
// Supabase は撤去方針（コメントアウトまたは削除）
```

---

### 3. iOS側の変更

#### ローカライズキーの追加

**ファイル**: `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`
```strings
"settings_usage_this_month_format" = "This month: %d / %d";
"settings_subscription_canceled_until" = "Canceled — ends on %@";
```

**ファイル**: `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`
```strings
"settings_usage_this_month_format" = "今月: %d / %d 回";
"settings_subscription_canceled_until" = "キャンセル済 — %@で終了";
```

**注意**: Root配下の `en.lproj/` と `ja.lproj/` は削除済み（重複ビルドエラーを回避）

#### SettingsView の使用量表示修正

**ファイル**: `aniccaios/aniccaios/SettingsView.swift`

**変更内容**:
- ハードコードされた日本語「こんげつ」をローカライズキーに置き換え

```swift
// 変更前
Text("こんげつ: \(count) / \(limit) 回")

// 変更後
Text(String(format: NSLocalizedString("settings_usage_this_month_format", comment: ""), count, limit))
```

#### SubscriptionInfo モデルの拡張

**ファイル**: `aniccaios/aniccaios/Models/SubscriptionInfo.swift`

**変更内容**:
- `willRenew` プロパティを追加（解約予約状態を保持）

```swift
struct SubscriptionInfo: Codable, Equatable {
    // ... 既存プロパティ ...
    var willRenew: Bool?  // 追加
}
```

#### SubscriptionManager の変更

**ファイル**: `aniccaios/aniccaios/Services/SubscriptionManager.swift`

**変更内容**:
- RevenueCat の `willRenew` を読み取り、`SubscriptionInfo` に設定

```swift
extension SubscriptionInfo {
    init(info: CustomerInfo) {
        // ... 既存コード ...
        let willRenew = entitlement?.willRenew ?? false
        let isTrial = entitlement?.periodType == .trial
        let statusString: String
        if entitlement?.isActive == true {
            statusString = isTrial ? "trialing" : (willRenew ? "active" : "canceled")
        } else {
            statusString = "expired"
        }
        self.init(
            // ... 既存パラメータ ...
            willRenew: willRenew  // 追加
        )
    }
}
```

#### ManageSubscriptionSheet の変更

**ファイル**: `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`

**変更内容**:
1. **解約予約の終了日表示**
   ```swift
   if let date = appState.subscriptionInfo.currentPeriodEnd {
       if appState.subscriptionInfo.willRenew == false {
           Text(String(format: NSLocalizedString("settings_subscription_canceled_until", comment: ""), dateFormatter.string(from: date)))
               .font(.caption)
               .foregroundStyle(.secondary)
       } else {
           Text(String(format: NSLocalizedString("settings_subscription_until", comment: ""), dateFormatter.string(from: date)))
               .font(.caption)
               .foregroundStyle(.secondary)
       }
   }
   ```

2. **AutoLayout 警告の修正（×ボタン）**
   ```swift
   ToolbarItem(placement: .navigationBarTrailing) {
       Button {
           dismiss()
       } label: {
           Image(systemName: "xmark.circle.fill")
               .foregroundStyle(.secondary)
               .frame(width: 24, height: 24)  // 追加：固定サイズで制約警告を抑止
       }
   }
   ```

---

## Railway環境変数設定

### 必須環境変数

以下の環境変数を Railway のプロジェクト設定で設定する必要がある：

#### 課金制限設定
- `PRO_MONTHLY_LIMIT`: PROプランの月次利用上限（例: `300`）
- `FREE_MONTHLY_LIMIT`: 無料プランの月次利用上限（例: `30`）

#### RevenueCat設定
- `REVENUECAT_PROJECT_ID`: RevenueCat プロジェクトID
- `REVENUECAT_REST_API_KEY`: RevenueCat REST API キー
- `REVENUECAT_WEBHOOK_SECRET`: RevenueCat Webhook 署名検証用シークレット
- `REVENUECAT_ENTITLEMENT_ID`: Entitlement ID（デフォルト: `pro`）
- `REVENUECAT_PAYWALL_ID`: Paywall ID（例: `ofrng78a01eb506`）
- `REVENUECAT_CUSTOMER_CENTER_ID`: Customer Center ID

#### データベース接続
- `DATABASE_URL`: Railway Postgres の接続文字列（Railway が自動設定）

### 設定方法

1. Railway ダッシュボード → プロジェクト → Variables タブ
2. 上記の環境変数を追加
3. デプロイ後に反映される

### 確認方法

サーバ起動時のログで確認：
```
- Free monthly limit: 30
- Pro monthly limit: 300
```

---

## データフロー

### 購読状態の同期フロー

1. **RevenueCat Webhook 受信** (`apps/api/src/api/billing/webhookRevenueCat.js`)
   - RevenueCat から購読状態変更イベントを受信
   - `processRevenueCatEvent()` を呼び出し

2. **購読状態の更新** (`apps/api/src/services/revenuecat/webhookHandler.js`)
   - RevenueCat API から最新の Entitlement を取得
   - `applyRevenueCatEntitlement()` で Railway Postgres の `user_subscriptions` を更新
   - 解約予約でも有効期限までは `plan=pro`, `status=active` として保存

3. **iOS アプリの同期** (`aniccaios/aniccaios/Services/SubscriptionManager.swift`)
   - `syncUsageInfo()` で `/mobile/entitlement` エンドポイントから最新状態を取得
   - `SubscriptionInfo` を更新し、UIに反映

### 使用量カウントのフロー

1. **Realtime セッション発行時** (`apps/api/src/routes/mobile/realtime.js`)
   - `getEntitlementState()` で現在の購読状態と使用量を取得
   - `canUseRealtime()` で残枠をチェック
   - 残枠があれば `incrementTodayUsage()` でカウントを増やし、セッションを発行

2. **月次集計** (`apps/api/src/services/subscriptionStore.js`)
   - `getMonthlyUsage()` で当月の使用量を集計
   - UTC基準で月初（`date_trunc('month', now() at time zone 'utc')`）から集計

---

## 解決した問題

### 1. 外部キー制約エラー（23503）
- **原因**: Supabase の `auth.users` を参照していたが、モバイルアプリは独自JWT認証を使用
- **解決**: Railway Postgres に移行し、外部キー制約を設けない設計に変更

### 2. ESM SyntaxError（重複関数定義）
- **原因**: `getMonthlyUsage()` が2回定義されていた
- **解決**: 重複定義を削除

### 3. iOS表示の問題
- **英語環境で日本語表示**: ローカライズキーを追加して解決
- **キャンセル後の表示**: `willRenew=false` を検知して「Canceled — ends on <日付>」を表示
- **AutoLayout警告**: ×ボタンに固定サイズを設定して解決

### 4. 解約予約後の上限問題
- **原因**: 解約予約を即座に `free` 扱いにしてしまい、上限が30回になっていた
- **解決**: 有効期限までは `pro` として扱い、上限300回を維持

---

## 残課題と今後の対応

### 1. iOS: 既に購読済みユーザーへのPaywall表示
- **現状**: 購読済みでもPaywallが表示され、「Already subscribed」警告が出る
- **対応**: `PaywallContainerView` で `appState.subscriptionInfo.isEntitled` をチェックし、購読済みならPaywallを表示しない

### 2. iOS: Customer Center の識別子指定
- **現状**: `RevenueCatUI.CustomerCenterView()` に識別子を指定していない
- **対応**: `customerCenterIdentifier: AppConfig.revenueCatCustomerCenterId` を指定

### 3. RevenueCat Paywall のローカライズ
- **現状**: RevenueCat ダッシュボード側のPaywall文言が未設定で、ローカライズエラーが出る
- **対応**: RevenueCat ダッシュボード → Paywall（Identifier: `ofrng78a01eb506`）→ Localization で `en` と `ja` のテキストを設定

### 4. シミュレータ/他端末でPaywallが表示されない
- **原因候補**:
  - Offering ID が別プロジェクト/環境に紐付いている
  - 端末の `AppUserID` が別のRCプロジェクトにログインしている
- **確認方法**: iOS ログで `Using API Key:` と `AppConfig.revenueCatPaywallId` を確認

---

## ファイル変更一覧

### API側
- `apps/api/docs/migrations/006_init_billing_tables_on_railway.sql`（新規）
- `apps/api/src/lib/migrate.js`（新規）
- `apps/api/src/server.js`（マイグレーション実行を追加）
- `apps/api/src/services/subscriptionStore.js`（全面書き換え）
- `apps/api/src/services/revenuecat/webhookHandler.js`（Railway Postgres化）
- `apps/api/src/services/stripe/webhookHandler.js`（`supabaseUserExists`削除）
- `apps/api/src/config/environment.js`（Supabase警告を無効化）

### iOS側
- `aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`（キー追加）
- `aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`（キー追加）
- `aniccaios/aniccaios/en.lproj/Localizable.strings`（削除：重複回避）
- `aniccaios/aniccaios/ja.lproj/Localizable.strings`（削除：重複回避）
- `aniccaios/aniccaios/SettingsView.swift`（ローカライズ化）
- `aniccaios/aniccaios/Models/SubscriptionInfo.swift`（`willRenew`追加）
- `aniccaios/aniccaios/Services/SubscriptionManager.swift`（`willRenew`読み取り）
- `aniccaios/aniccaios/Views/ManageSubscriptionSheet.swift`（解約表示＋AutoLayout修正）

---

## 運用上の注意点

### マイグレーション
- サーバ起動時に自動実行される（`runMigrationsOnce()`）
- `schema_migrations` テーブルで進捗を管理し、同じマイグレーションは2回実行されない
- 新しいマイグレーションは `apps/api/docs/migrations/` に `007_*.sql` 形式で追加

### データ移行
- Supabase から Railway Postgres へのデータ移行は実施していない（新規ユーザーから適用）
- 既存の Supabase データが必要な場合は、手動で移行スクリプトを作成する必要がある

### デプロイ順序
1. Railway 環境変数を設定
2. コードをデプロイ（マイグレーションが自動実行される）
3. iOS アプリをビルド・配布

---

## 参考資料

- Stripe Subscription Use Cases: `examples/stripe-subscription-use-cases/`
- RevenueCat iOS SDK: `examples/purchases-ios/`
- Railway Postgres 接続: `apps/api/src/lib/db.js`

---

## 更新履歴

- 2025-11-20: 初版作成（Supabase撤去 → Railway Postgres一本化）

