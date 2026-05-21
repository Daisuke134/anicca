# US-005b: Monetization (IAP + Pricing + RevenueCat)

依存: US-005a（APP_ID がプロジェクト .env に記録済みであること）

## .env ファイル構造
```
~/.config/mobileapp-builder/.env                    ← グローバル（Apple ID, Keychain, Slack等）
./.env     ← アプリ固有（APP_ID, GROUP_ID, RC_SECRET_KEY, RC_IOS_PUBLIC_KEY等）
```
全 Step の冒頭で両方を source する:
```bash
source ~/.config/mobileapp-builder/.env
source ./.env
```

## Source Skills (参考のみ — 読み込み不要。コマンドは下記に全てインライン)
元ネタ: asc-ppp-pricing, asc-subscription-localization

## Quality Gate (MANDATORY — US-005a の成果物検証)
```bash
source ~/.config/mobileapp-builder/.env
source ./.env
test -n "$APP_ID" || { echo "GATE FAIL: APP_ID not set"; exit 1; }
```

## Step 6: IAP Creation + Localization + Availability + Pricing

**順序が超重要！** availability → pricing の順。逆だと Apple API が 500 を返す。

### 6.1: サブスクリプショングループ作成
```bash
GROUP_ID=$(asc subscriptions groups create --app $APP_ID --reference-name "<AppName> Premium" --output json 2>&1 | jq -r '.data.id')
echo "GROUP_ID=$GROUP_ID" >> ./.env
```

### 6.2: サブスクリプション作成

> `--ref-name` = ASC 内部管理名（ユーザーには見えない）。ユーザー表示名は Step 6.3 のローカリゼーションで設定する。

Source: RevenueCat State of Subscription Apps 2025 (https://www.revenuecat.com/state-of-subscription-apps-2025/)
> "Weekly subscriptions are now the most popular plan type, growing 10% since last year and accounting for nearly half of all in-app subscriptions. Weekly plans have fundamentally changed the game by capturing 47% of total revenue."

Source: RevenueCat Blog — Annual Subscriptions Pros & Cons (https://www.revenuecat.com/blog/growth/annual-subscriptions-apps-pros-cons/)
> "Paywalls with three plans—weekly, monthly, and annual—tend to drive stronger LTV across categories."

**3プラン必須（weekly + monthly + annual）。2プランは機会損失。**

Source: iOS Paywall Design Guide (https://adapty.io/blog/how-to-design-ios-paywall/)
> "Dynamic paywalls with segmented or time-based discounts deliver approximately 35% higher conversion rates than static alternatives"

→ 静的Paywallではなくユーザーセグメントやタイミングベースのオファーをデフォルト化する（実装: Paywall Builder使用時のみ。hard-codedペイウォールでは対応困難）

```bash
WEEKLY_ID=$(asc subscriptions create --group $GROUP_ID --ref-name "Weekly" --product-id "<bundle_id>.weekly" --subscription-period ONE_WEEK --output json 2>&1 | jq -r '.data.id')
echo "WEEKLY_ID=$WEEKLY_ID" >> ./.env

MONTHLY_ID=$(asc subscriptions create --group $GROUP_ID --ref-name "Monthly" --product-id "<bundle_id>.monthly" --subscription-period ONE_MONTH --output json 2>&1 | jq -r '.data.id')
echo "MONTHLY_ID=$MONTHLY_ID" >> ./.env

ANNUAL_ID=$(asc subscriptions create --group $GROUP_ID --ref-name "Annual" --product-id "<bundle_id>.annual" --subscription-period ONE_YEAR --output json 2>&1 | jq -r '.data.id')
echo "ANNUAL_ID=$ANNUAL_ID" >> ./.env
```

### 6.3: ローカリゼーション（グループ + サブスク、全37言語）

Source: asc-subscription-localization SKILL.md
> 「Each locale requires a separate create call. Creating a localization for a locale that already exists will fail; always check first.」

**en-US の名前を全言語にデフォルト設定し、ja だけ日本語に上書きする。**

```bash
# 全37 locale リスト
LOCALES="ar-SA ca cs da de-DE el en-AU en-CA en-GB en-US es-ES es-MX fi fr-CA fr-FR he hi hr hu id it ja ko ms nl-NL no pl pt-BR pt-PT ro ru sk sv th tr uk vi zh-Hans zh-Hant"

# --- グループローカリゼーション ---
for LOCALE in $LOCALES; do
  NAME="<AppName> Premium"
  [ "$LOCALE" = "ja" ] && NAME="<AppName> プレミアム"
  asc subscriptions groups localizations create --group-id $GROUP_ID --locale "$LOCALE" --name "$NAME" 2>&1 || true
done

# --- Weekly ローカリゼーション ---
for LOCALE in $LOCALES; do
  NAME="Weekly Premium"; DESC="Full access. Try it weekly."
  [ "$LOCALE" = "ja" ] && NAME="週額プレミアム" && DESC="全機能にアクセス。週単位でお試し。"
  asc subscriptions localizations create --subscription-id $WEEKLY_ID --locale "$LOCALE" --name "$NAME" --description "$DESC" 2>&1 || true
done

# --- Monthly ローカリゼーション ---
for LOCALE in $LOCALES; do
  NAME="Monthly Premium"; DESC="Full access to all features."
  [ "$LOCALE" = "ja" ] && NAME="月額プレミアム" && DESC="全機能にアクセス。"
  asc subscriptions localizations create --subscription-id $MONTHLY_ID --locale "$LOCALE" --name "$NAME" --description "$DESC" 2>&1 || true
done

# --- Annual ローカリゼーション ---
for LOCALE in $LOCALES; do
  NAME="Annual Premium"; DESC="Full access. Save 50%."
  [ "$LOCALE" = "ja" ] && NAME="年額プレミアム" && DESC="全機能にアクセス。50%お得。"
  asc subscriptions localizations create --subscription-id $ANNUAL_ID --locale "$LOCALE" --name "$NAME" --description "$DESC" 2>&1 || true
done
```

### 6.4: availability 設定（全175テリトリー、pricing の前に必須！）

```bash
TERRITORIES=$(asc pricing territories list --paginate --output json 2>&1 | jq -r '[.data[].id] | join(",")')
asc subscriptions availability set --id $WEEKLY_ID --territory "$TERRITORIES" --available-in-new-territories
asc subscriptions availability set --id $MONTHLY_ID --territory "$TERRITORIES" --available-in-new-territories
asc subscriptions availability set --id $ANNUAL_ID --territory "$TERRITORIES" --available-in-new-territories
```

### 6.5: 175カ国価格設定（availability の後！）

equalization API → CSV → `prices import` で一括設定。

**CSV フォーマット:** `territory,price,price_point_id`（3列必須。price_point_id があると CLI が price 解決をスキップし高速）

```bash
for SUB_ID in $WEEKLY_ID $MONTHLY_ID $ANNUAL_ID; do
  export TARGET_PRICE=$([ "$SUB_ID" = "$WEEKLY_ID" ] && echo "1.99" || [ "$SUB_ID" = "$MONTHLY_ID" ] && echo "4.99" || echo "29.99")

  # USA の target price point ID を取得（export TARGET_PRICE でパイプ右側の Python にも渡る）
  PP_ID=$(asc subscriptions price-points list --subscription-id $SUB_ID --territory USA --paginate --output json 2>&1 \
    | python3 -c "
import sys, json, os
target = float(os.environ['TARGET_PRICE'])
for pp in json.load(sys.stdin)['data']:
    p = pp['attributes'].get('customerPrice')
    if p and abs(float(p) - target) < 0.01:
        print(pp['id']); break
")

  # 174カ国の等価価格 → CSV（stderr 混入防止: 2>/dev/null）
  asc subscriptions price-points equalizations --id "$PP_ID" --paginate --output json 2>/dev/null \
    | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
print('territory,price,price_point_id')
for pp in data['data']:
    raw = pp['id']
    padded = raw + '=' * (4 - len(raw) % 4) if len(raw) % 4 else raw
    decoded = json.loads(base64.b64decode(padded).decode())
    print(f'{decoded[\"t\"]},{pp[\"attributes\"][\"customerPrice\"]},{raw}')
" > /tmp/${SUB_ID}-prices.csv

  # dry-run で検証（failed > 0 なら停止）
  asc subscriptions prices import --id $SUB_ID --input /tmp/${SUB_ID}-prices.csv --dry-run

  # 本番実行
  asc subscriptions prices import --id $SUB_ID --input /tmp/${SUB_ID}-prices.csv

  # USA を追加（equalization に含まれないため。既存なら skip）
  # --paginate 必須: デフォルト50件で切れるため USA が見つからない場合がある
  EXISTING_USA=$(asc subscriptions prices list --id $SUB_ID --paginate --output json 2>&1 | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data.get('data', []):
    rels = p.get('relationships', {}).get('territory', {}).get('data', {})
    if rels.get('id') == 'USA':
        print('yes'); break
" 2>/dev/null)
  if [ "$EXISTING_USA" != "yes" ]; then
    asc subscriptions prices add --id $SUB_ID --price "$TARGET_PRICE" --territory "USA"
  else
    echo "✅ USA price already exists for $SUB_ID — skipping"
  fi
done
```

### 6.6: IAP Review Screenshot → US-008a Step 1h で実行

**⚠️ US-005b 時点ではアプリ未ビルド（US-006 が後）なので Paywall スクリーンショットは撮れない。**
**US-008a Step 1h でアプリビルド後に Paywall 画面をキャプチャしてアップロードする。**

ここでは何もしない。US-005b の passes:true 判定に Review Screenshot は不要。

## Step 7: RC Setup（RevenueCat API v2 — 全自動）

### 7.0: 人間に依頼（WAITING_FOR_HUMAN）

⛔ **SK Key を受け取るまで Step 7.1 以降に進むことを禁止する。** RC API Key なしで Product/Offering 作成は不可能。
CC は Slack で以下を送信:
```
WAITING_FOR_HUMAN: RC Setup
📱 RevenueCat セットアップをお願いします（2分）:
1. https://app.revenuecat.com → 「+ Create new project」 → プロジェクト名: <app_name>
2. 作成したプロジェクトの Settings → API Keys → 「+ New secret API key」
3. 権限を全て「Read & Write」に設定 → Generate
4. 生成された sk_... キーをこのチャットに貼り付けてください

それだけでOKです。残りは全て自動で行います。
```

### 7.1: SK Key 受信 → 変数準備
```bash
source ~/.config/mobileapp-builder/.env
source ./.env
RC_SECRET_KEY="<sk_... from Slack>"
RC_BASE="https://api.revenuecat.com/v2"
AUTH="Authorization: Bearer $RC_SECRET_KEY"
CT="Content-Type: application/json"

# Project ID 取得（SK Key があれば自動）
RC_PROJECT_ID=$(curl -s "$RC_BASE/projects" -H "$AUTH" | jq -r '.items[0].id')
```

### 7.2: RC App 作成
```bash
# PATCH 12-14+21: RC API v2 は name（not app_name）、nested app_store.bundle_id、フラットレスポンス(.id)
APP_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/apps" \
  -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"<app_name>\",\"type\":\"app_store\",\"app_store\":{\"bundle_id\":\"<bundle_id>\"}}")
HTTP_CODE=$(echo "$APP_RESULT" | tail -1)
APP_BODY=$(echo "$APP_RESULT" | sed '$d')
[ "$HTTP_CODE" -ge 400 ] && { echo "❌ RC App create failed ($HTTP_CODE): $APP_BODY"; exit 1; }
RC_APP_ID=$(echo "$APP_BODY" | jq -r '.id')
echo "✅ RC App: $RC_APP_ID"
```

### 7.2b: Public API Key 取得（自動 — WAITING_FOR_HUMAN 不要）
```bash
RC_PUBLIC_KEY=$(curl -s "$RC_BASE/projects/$RC_PROJECT_ID/apps/$RC_APP_ID/public_api_keys" \
  -H "$AUTH" | jq -r '.items[0].key')
echo "RC_IOS_PUBLIC_KEY=$RC_PUBLIC_KEY" >> ./.env
```
⚠️ Public Key は App 作成時に自動生成される。Products/Offerings の前に取得可能。

### 7.3: Entitlement 作成
```bash
# PATCH 21: エラーチェック付き
ENT_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/entitlements" \
  -H "$AUTH" -H "$CT" \
  -d '{"lookup_key":"premium","display_name":"Premium"}')
HTTP_CODE=$(echo "$ENT_RESULT" | tail -1)
ENT_BODY=$(echo "$ENT_RESULT" | sed '$d')
[ "$HTTP_CODE" -ge 400 ] && { echo "❌ Entitlement create failed ($HTTP_CODE): $ENT_BODY"; exit 1; }
RC_ENT_ID=$(echo "$ENT_BODY" | jq -r '.id')
echo "✅ Entitlement: $RC_ENT_ID"
```

### 7.4: Product 作成 + Entitlement 紐付け
```bash
# PATCH 15+19: Product ID を変数に保持（Step 7.5 で使う）。エラーチェック付き
for pid in "<bundle_id>.weekly" "<bundle_id>.monthly" "<bundle_id>.annual"; do
  PROD_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/products" \
    -H "$AUTH" -H "$CT" \
    -d "{\"store_identifier\":\"$pid\",\"app_id\":\"$RC_APP_ID\",\"type\":\"subscription\"}")
  HTTP_CODE=$(echo "$PROD_RESULT" | tail -1)
  PROD_BODY=$(echo "$PROD_RESULT" | sed '$d')
  [ "$HTTP_CODE" -ge 400 ] && { echo "❌ Product create failed ($HTTP_CODE): $PROD_BODY"; exit 1; }

  PROD_ID=$(echo "$PROD_BODY" | jq -r '.id')

  # Product ID を保持（Step 7.5 Package 紐付けで使う）
  case "$pid" in
    *weekly)  WEEKLY_PROD_ID="$PROD_ID" ;;
    *monthly) MONTHLY_PROD_ID="$PROD_ID" ;;
    *annual)  ANNUAL_PROD_ID="$PROD_ID" ;;
  esac

  ATTACH_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/entitlements/$RC_ENT_ID/actions/attach_products" \
    -H "$AUTH" -H "$CT" \
    -d "{\"product_ids\":[\"$PROD_ID\"]}")
  HTTP_CODE=$(echo "$ATTACH_RESULT" | tail -1)
  [ "$HTTP_CODE" -ge 400 ] && { echo "❌ Entitlement attach failed ($HTTP_CODE)"; exit 1; }
  echo "✅ Product $PROD_ID → Entitlement attached"
done
```

### 7.5: Offering + Package 作成
```bash
# PATCH 16+21: エラーチェック付き。Package は product_id を受け付けない — 別途 attach_products が必要
OFF_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/offerings" \
  -H "$AUTH" -H "$CT" \
  -d '{"lookup_key":"default","display_name":"Default"}')
HTTP_CODE=$(echo "$OFF_RESULT" | tail -1)
OFF_BODY=$(echo "$OFF_RESULT" | sed '$d')
[ "$HTTP_CODE" -ge 400 ] && { echo "❌ Offering create failed ($HTTP_CODE): $OFF_BODY"; exit 1; }
RC_OFF_ID=$(echo "$OFF_BODY" | jq -r '.id')
echo "✅ Offering: $RC_OFF_ID"

# Package 作成 + Product 紐付け（lookup_key は $rc_weekly / $rc_monthly / $rc_annual = RC 標準）
for period in "weekly" "monthly" "annual"; do
  PKG_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/offerings/$RC_OFF_ID/packages" \
    -H "$AUTH" -H "$CT" \
    -d "{\"lookup_key\":\"\$rc_$period\",\"display_name\":\"$(echo $period | sed 's/.*/\u&/')\"}")
  HTTP_CODE=$(echo "$PKG_RESULT" | tail -1)
  PKG_BODY=$(echo "$PKG_RESULT" | sed '$d')
  [ "$HTTP_CODE" -ge 400 ] && { echo "❌ Package create failed ($HTTP_CODE): $PKG_BODY"; exit 1; }
  PKG_ID=$(echo "$PKG_BODY" | jq -r '.id')

  # Product → Package 紐付け（eligibility_criteria 必須）
  PROD_ID=$([ "$period" = "weekly" ] && echo "$WEEKLY_PROD_ID" || [ "$period" = "monthly" ] && echo "$MONTHLY_PROD_ID" || echo "$ANNUAL_PROD_ID")
  ATTACH_RESULT=$(curl -s -w "\n%{http_code}" -X POST "$RC_BASE/projects/$RC_PROJECT_ID/packages/$PKG_ID/actions/attach_products" \
    -H "$AUTH" -H "$CT" \
    -d "{\"products\":[{\"product_id\":\"$PROD_ID\",\"eligibility_criteria\":\"all\"}]}")
  HTTP_CODE=$(echo "$ATTACH_RESULT" | tail -1)
  [ "$HTTP_CODE" -ge 400 ] && { echo "❌ Package attach failed ($HTTP_CODE)"; exit 1; }
  echo "✅ Package $period → Product attached"
done
```

### 7.6: SPM 依存追加
> ⚠️ **US-006 で実行。** Xcode プロジェクト作成後に RevenueCat SPM を追加する。US-005b ではスキップ。

RevenueCat を Xcode プロジェクトに追加（RevenueCatUI は使わない — Rule 20）。

## Paywall UI Best Practices（US-006で実装）

### Animation（必須 — 2.9x conversion boost）
Source: iOS Paywall Design Guide (https://adapty.io/blog/how-to-design-ios-paywall/)
> "Animated paywalls produce 2.9× higher conversion rates than static designs"

Source: 5 overlooked paywall improvements (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
> "When implemented correctly, animated elements typically increase conversion rates by 12-18% compared to static alternatives"

**実装必須:**
- CTAボタンの subtle pulsing (SwiftUI `.animation(.easeInOut(duration: 1.0).repeatForever())`)
- Pricing options の entrance effects (`.transition(.scale)`)
- Benefit showcase の carousel animation

### CTA Copy（Benefit-driven）
Source: Engaging Paywall Screens (https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/)
> "Benefit-driven CTAs ('Start my plan') outperform generic ones ('Subscribe')"

**実装: "Start my plan" / "Unlock full access" / "Get my personalized report" 等のbenefit-driven textに変更**

### Price Anchoring
Source: 5 overlooked paywall improvements (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
> "Effectively anchoring your premium price against strategic reference points can make your offering appear significantly more valuable"

**実装:**
- 月額換算表示（年額プランの場合: "Just $2.49/month"）
- 日常購入品との比較（"Less than a coffee per week"）
- 割引率の視覚的強調（"Save 50%" badge + strikethrough price）

### Free Trial Messaging（繰り返し強調）
Source: 5 overlooked paywall improvements (https://www.revenuecat.com/blog/growth/paywall-conversion-boosters/)
> "Simply including a 'Start Free Trial' button isn't enough—the trial offer should be a central, recurring element throughout your paywall"

**実装:**
- Headline: "Try Premium Free for 7 Days"
- Supporting copy: "No commitment. Cancel anytime."
- Visual element: timer icon or calendar graphic
- CTA button: "Start my free week"

### Social Proof（+10-15% conversion）
Source: iOS Paywall Design Guide (https://adapty.io/blog/how-to-design-ios-paywall/)
> "Social proof (reviews): +10% to +15%"

**実装: App Store reviews/ratingsをPaywall内に表示**

### Personalization（+17% conversion）
Source: iOS Paywall Design Guide (https://adapty.io/blog/how-to-design-ios-paywall/)
> "User name personalization: +17%"

**実装: ユーザー名をheadlineに含める（"John, unlock your premium features"）**

### Placement（必須 — onboarding直後）
Source: Mobile App Onboarding: 5 Paywall Optimization Strategies (https://appagent.com/blog/mobile-app-onboarding-5-paywall-optimization-strategies/)
> "Ensure that most existing users see the paywall by placing it immediately after the onboarding process"

**実装: オンボーディング完了直後に1度Paywallを表示する**

### Messaging Consistency
Source: Engaging Paywall Screens (https://blog.funnelfox.com/effective-paywall-screen-designs-mobile-apps/)
> "Consistent messaging from ad to onboarding to paywall increases conversions"

**実装: 広告・オンボーディング・Paywallでトーン/メッセージ/ビジュアルを一貫させる**

## RC Test Store（E2E テスト用 — US-007 で使用）

Source: [RevenueCat Test Store](https://www.revenuecat.com/docs/test-and-launch/sandbox/test-store)

RC Test Store は StoreKit Configuration を不要にし、Maestro E2E で決済フローをテストできる。

| 項目 | 値 |
|------|-----|
| 前提条件 | RC SDK >= 5.43.0, Test Store API Key |
| 設定場所 | RC Dashboard → Project → App → Test Store |
| テスト環境 | DEBUG ビルド + Simulator のみ |
| StoreKit Configuration | **不要（禁止）** — RC Test Store が代替 |

### xcconfig 設定（Debug / Release 分離）

```
# Config/Debug.local.xcconfig
REVENUECAT_API_KEY = <RC_TEST_STORE_KEY>   ← test_ プレフィックスのキー

# Config/Release.local.xcconfig
REVENUECAT_API_KEY = <RC_IOS_PUBLIC_KEY>   ← appl_ プレフィックスのキー
```

Info.plist で `RevenueCatAPIKey = $(REVENUECAT_API_KEY)` として読み込む。

### SubscriptionService.configure() パターン（DEBUG + uiPreviewMode）

iOS 18.4+/26.x シミュレータでは StoreKit が products を返さない（GitHub #4954）。
RC SDK の `SimulatedStoreProductsManager` は Web Billing API を使うが Test Store products は未対応。
**`uiPreviewMode` で StoreKit も Web Billing も迂回し、RC dashboard offerings から mock products を生成する。**

```swift
import Foundation
#if DEBUG
@_spi(Internal) import RevenueCat
#else
import RevenueCat
#endif

// configure() 内:
#if DEBUG
Purchases.logLevel = .debug
let config = Configuration.Builder(withAPIKey: apiKey)
    .with(dangerousSettings: DangerousSettings(uiPreviewMode: true))
    .build()
Purchases.configure(with: config)
#else
let config = Configuration.Builder(withAPIKey: apiKey)
    .with(entitlementVerificationMode: .informational)
    .build()
Purchases.configure(with: config)
#endif

// purchase() 内（uiPreviewMode では customerInfo.entitlements が空のため）:
#if DEBUG
do {
    _ = try await Purchases.shared.purchase(package: package)
    return true
} catch {
    let errorCode = (error as NSError).code
    // cancel(1) と simulated failure(42) のみ re-throw
    if errorCode == 1 || errorCode == 42 { throw error }
    return true  // 7944 (Product ID required) 等は成功扱い
}
#else
let result = try await Purchases.shared.purchase(package: package)
return result.customerInfo.entitlements["premium"]?.isActive == true
#endif
```

Source:
- RC SDK `OfferingsManager.swift` createPreviewProducts() — uiPreviewMode で mock 生成
- RC SDK `SimulatedStorePurchaseUI.swift` — 購入ダイアログ表示
- RC SDK `ProductsManagerFactory.swift` — test_ キーで SimulatedStoreProductsManager 選択

### Maestro での使い方

```yaml
# Payment success（ボタンテキスト: RC SDK 5.60.0 SimulatedStorePurchaseUI.swift）
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Test valid purchase"
    timeout: 10000
- tapOn: "Test valid purchase"

# Payment failure
- tapOn:
    id: "paywall_plan_monthly"
- extendedWaitUntil:
    visible: "Test failed purchase"
    timeout: 10000
- tapOn: "Test failed purchase"
```

詳細は `.claude/skills/maestro-ui-testing/SKILL.md` の RC Test Store セクションを参照。

## Price Validation Gate (MANDATORY — Fix #8)

Source: RevenueCat SOSA 2025 — https://www.revenuecat.com/blog/growth/sosa-2025-launch-sub-club/
核心の引用: 「lower-priced apps have higher retention rates... you've got to play around with that price curve」

```bash
# PRD価格とASC実際の価格を照合
source ~/.config/mobileapp-builder/.env
source ./.env

echo "=== PRD定義価格 ==="
python3 -c "
import json
d = json.load(open('prd.json'))
pricing = d.get('pricing', d.get('monetization', {}))
print(json.dumps(pricing, indent=2, ensure_ascii=False))
" 2>/dev/null || echo "PRD pricing section not found"

echo ""
echo "=== ASC実際の価格 ==="
asc subscriptions groups list --app "$APP_ID" --output table 2>/dev/null
asc subscriptions list --app "$APP_ID" --output table 2>/dev/null

echo ""
echo "⚠️ PRDの価格とASCの価格が一致していることを確認せよ"
echo "不一致の場合: prd.json を更新するか ASC の価格を変更する"
# CC は両方の出力を比較し、不一致があれば prd.json を実際の価格に合わせて更新する
```

## 次のステップ
US-005b 完了後、US-006（実装）に進む。
