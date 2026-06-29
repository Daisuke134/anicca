# PATCH — paywall 立て直し（no-trial 全同期 + 1.9.1コピー復元 + JP限定3プラン/値下げ/買い切り）

最新版 = **release/1.9.3**（main も同値）。本 patch は worktree で実装し、`dev`→`main`→`release/1.9.4` で出す。

## 確定した決定（Dais, 2026-06-23）
1. **無料トライアルを全廃**（ASC↔RC↔iOS を 100% no-trial に同期）。CTA=「Start Your Journey Now / 今すぐ旅を始める」。
2. **paywall コピーを 1.9.1 の自然な文言へ復元**。ただし2特典は**削除**（「AI生成…/AI-generated…」と「フィードバックから学習…/Learns from your feedback」）→ 特典は3つ。
3. **日本(JPストア)限定の実験**: 月¥1,500→**¥500** / 年¥6,000→**¥2,000** + **買い切り ¥5,000 を追加**。
4. **英語(US等)**: 月$9.99 / 年$39.99 据置、**買い切りは出さない**、トライアル無し。
5. ハード paywall の**無限スピナー詰まりを修正**（購入不能トラウマの一因）。

## SSOT 事実（実測: asc 2.0.0 / RevenueCat API / 1.9.3 コード）
| 項目 | 値 |
|---|---|
| App id | `6755129214`（`ai.anicca.app.ios`） |
| ライブ paywall View | `aniccaios/aniccaios/Onboarding/PaywallVariantBView.swift`（`OnboardingBibleViews.swift:719`） |
| ライブ offering | `ofrngb357e8cdb3`（`anicca_variant_b`, is_current） |
| entitlement | `entlb820c43ab7`（Prod/Staging, `Configs/Production.xcconfig:4`） |
| RC app_id(Apple) | `app511ef26659` |
| sub: monthly.b | id `6769264298` / `ai.anicca.app.ios.monthly.b` / prod `prodd6e68bd651` |
| sub: yearly.b | id `6762049696` / `ai.anicca.app.ios.yearly.b` / prod `prodecbf22e88d` |
| sub: weekly.b | id `6762049888`（非表示） |
| 新 lifetime | `ai.anicca.app.ios.lifetime`（NON_CONSUMABLE, 新規） |
| 現状トライアル | yearly.b/monthly.b/weekly.b すべて FREE_TRIAL/THREE_DAYS（全テリトリ）= **要削除** |
| 本番購入は機能中の証拠 | RevenueCat 直近28日 売上$47 / 有料6 / 新規129（=本番課金は通っている） |

---

## PHASE 0 — worktree（products は worktree 必須）
```bash
cd /Users/anicca/anicca-project && git fetch origin && git checkout dev && git pull
git worktree add ../anicca-paywall -b feature/paywall-notrial-jp3plan
cd ../anicca-paywall/aniccaios && xcodebuild -scheme aniccaios -destination "generic/platform=iOS Simulator" -quiet build CODE_SIGNING_ALLOWED=NO ; cd ..
```

## PHASE 1 — App Store Connect（asc 2.0.0）

### 1-1. 無料トライアル全削除（3商品 × 全テリトリ）
```bash
for SUB in 6762049696 6769264298 6762049888; do
  asc subscriptions offers introductory list --subscription-id $SUB --output json \
   | python3 -c "import json,sys;[print(o['id']) for o in json.load(sys.stdin).get('data',[])]" \
   | while read OID; do asc subscriptions offers introductory delete --id "$OID" --confirm; done
done
# 検証: 各 SUB で introductory list が空
```

### 1-2. JP 価格（日本のみ。US据置）
```bash
asc subscriptions pricing prices set --subscription-id 6769264298 --price "500"  --territory JP --preserved   # 月¥500
asc subscriptions pricing prices set --subscription-id 6762049696 --price "2000" --territory JP --preserved   # 年¥2,000
asc subscriptions pricing summary --app 6755129214 --territory JP   # 検証
```

### 1-3. 買い切り IAP（NON_CONSUMABLE, base=JP¥5,000）
```bash
asc iap setup --app 6755129214 --type NON_CONSUMABLE \
  --reference-name "Anicca Lifetime" --product-id "ai.anicca.app.ios.lifetime" \
  --locale "ja-JP" --display-name "買い切り" --description "アニッチャ プレミアムを永久に。" \
  --price "5000" --base-territory "Japan"           # → $IAP_ID を控える
asc iap localizations create --iap-id "$IAP_ID" --locale "en-US" --display-name "Lifetime" --description "Anicca Premium, forever."
# US 表示はするが英語paywallでは出さない(下記 PHASE3 で JPストアのみ表示)。US価格は自動均等化のまま or 任意で$99.99に:
#   asc iap pricing price-points list --iap-id "$IAP_ID" --territory USA → $99.99 の id を取得し schedules create
```

## PHASE 2 — RevenueCat（MCP, project `projbb7b9d1b`）
```
1) create-product: app_id=app511ef26659, type=non_consumable,
   store_identifier="ai.anicca.app.ios.lifetime", display_name="Anicca Lifetime" → $RC_LIFETIME_PROD
2) create-packages: offering_id=ofrngb357e8cdb3, lookup_key="$rc_lifetime",
   display_name="Lifetime", position=3 → $RC_LIFETIME_PKG
3) attach-products-to-package: package_id=$RC_LIFETIME_PKG,
   products=[{product_id:$RC_LIFETIME_PROD, eligibility_criteria:"all"}]
4) attach-products-to-entitlement: entitlement_id=entlb820c43ab7, product_ids=[$RC_LIFETIME_PROD]
```
> lifetime は global offering に入るが、**表示は iOS 側で JPストア限定にゲートする**（PHASE 3-3）。価格(¥500/¥2,000)は ASC の JPテリトリ価格で自動ローカライズ＝US は $9.99/$39.99 のまま。

## PHASE 3 — iOS コード（`aniccaios/aniccaios/`）

### 3-1. トライアル全廃（`Onboarding/PaywallVariantBView.swift`）
43–51行 `hasTrialEligibility` を常に false:
```diff
-    private var hasTrialEligibility: Bool {
-        // 2026-05-22 Dais directive: free trial back ON …(略)
-        guard let pkg = selectedPackage else { return true }
-        return pkg.packageType == .annual || pkg.packageType == .monthly
-    }
+    // 2026-06-23 Dais: 無料トライアル全廃。ASC からも intro offer を削除済。
+    private var hasTrialEligibility: Bool { false }
```
→ バッジ「3 DAYS FREE」消滅 / CTA=`paywall_b_cta_no_trial` / trust=`paywall_b_trust_no_trial`（コード分岐は既存のまま自動でno-trial側へ）。

### 3-2. 特典を5→3に（同ファイル `featureList`, 105–114行）
```diff
     private var featureList: some View {
         VStack(alignment: .leading, spacing: 8) {
             featureRow(String(localized: "paywall_b_feature_nudges"))
-            featureRow(String(localized: "paywall_b_feature_ai"))
             featureRow(String(localized: "paywall_b_feature_personalized"))
-            featureRow(String(localized: "paywall_b_feature_feedback"))
             featureRow(String(localized: "paywall_b_feature_cancel"))
         }
```

### 3-3. 買い切りカード（JPストア限定表示）
import 追加 + storefront state（StoreKit2, iOS15+）:
```diff
 import SwiftUI
 import RevenueCat
+import StoreKit
```
22行 `monthlyPackage` の直後:
```diff
     private var monthlyPackage: Package? { packages.first { $0.packageType == .monthly } }
+    @State private var storefrontCountry: String = ""
+    // 買い切りは日本(JPストア)のみ表示する実験（US等では nil）
+    private var lifetimePackage: Package? {
+        guard storefrontCountry == "JPN" else { return nil }
+        return packages.first { $0.packageType == .lifetime }
+    }
```
`body` の `.onAppear{…}` に隣接して storefront をロード（68行付近に追記）:
```diff
         .onAppear { … }
+        .task { storefrontCountry = await Storefront.current?.countryCode ?? "" }
```
`planCards` 内の ScrollView VStack を **monthly → annual → lifetime の順**に並べ替え（現状は annual→monthly）。VStack の中身を丸ごと以下に置換:
```swift
VStack(spacing: 12) {
    // 1) Monthly（最上段）
    if let monthly = monthlyPackage {
        planCard(
            package: monthly,
            priceLabel: monthly.localizedPriceString + String(localized: "paywall_b_per_month"),
            badge: trialBadge(for: monthly),          // no-trial化で nil
            dailyPriceLabel: nil
        )
    }
    // 2) Annual（既定選択・[おすすめ]/[BEST VALUE] + 日割り）
    if let yearly = yearlyPackage {
        planCard(
            package: yearly,
            priceLabel: yearly.localizedPriceString + String(localized: "paywall_b_per_year"),
            badge: trialBadge(for: yearly) ?? String(localized: "paywall_plan_yearly_badge"),
            dailyPriceLabel: dailyPrice.map {
                String(format: NSLocalizedString("paywall_b_daily_price", comment: ""), $0)
            }
        )
    }
    // 3) Lifetime（JPストアのみ。lifetimePackage が JP以外で nil）
    if let lifetime = lifetimePackage {
        planCard(
            package: lifetime,
            priceLabel: lifetime.localizedPriceString + String(localized: "paywall_b_per_lifetime"),
            badge: String(localized: "paywall_b_lifetime_badge"),
            dailyPriceLabel: nil
        )
    }
}
.padding(.horizontal, 24).padding(.top, 8)
```
> 既定選択は **annual のまま**（`onAppear` の `selectedPackage = yearlyPackage ?? monthlyPackage` 据置）＝最上段が monthly でもハイライトは annual。月を既定にしたい場合は `monthlyPackage ?? yearlyPackage` に変更（要指示）。
`localizedPlanTitle`（291行 `.weekly` の後）:
```diff
         case .weekly: return String(localized: "paywall_b_plan_weekly")
+        case .lifetime: return String(localized: "paywall_b_plan_lifetime")
         default: return package.storeProduct.localizedTitle
```

### 3-4. 詰まり修正（無限スピナー → 再読込/復元）
`packages.isEmpty` ブロック（58–61行）を置換 + state/関数追加:
```diff
-            if packages.isEmpty {
-                ProgressView().padding(.top, 40)
-                Spacer()
-            } else {
+            if packages.isEmpty {
+                VStack(spacing: 16) {
+                    ProgressView()
+                    if showReloadAfterTimeout {
+                        Text(String(localized: "paywall_b_load_failed"))
+                            .font(.system(size: 14)).foregroundStyle(.secondary)
+                            .multilineTextAlignment(.center).padding(.horizontal, 24)
+                        Button(String(localized: "paywall_b_retry")) {
+                            Task { await SubscriptionManager.shared.refreshOfferings() }
+                        }.font(.system(size: 16, weight: .semibold))
+                        Button(String(localized: "paywall_plan_restore")) { restorePurchases() }
+                            .font(.system(size: 14)).foregroundStyle(.secondary)
+                    }
+                }.padding(.top, 40).onAppear { scheduleReloadTimeout() }
+                Spacer()
+            } else {
```
View 内に追加:
```swift
@State private var showReloadAfterTimeout = false
private func scheduleReloadTimeout() {
    DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
        if packages.isEmpty { showReloadAfterTimeout = true }
        Task { await SubscriptionManager.shared.refreshOfferings() }
    }
}
```

### 3-5. lifetime の entitlement status（`Services/SubscriptionManager.swift` 289–296行）
```diff
         let willRenew = entitlement?.willRenew ?? false
+        let isLifetime = productId == "ai.anicca.app.ios.lifetime"
         let isTrial = entitlement?.periodType == .trial
         let statusString: String
         if entitlement?.isActive == true {
-            statusString = isTrial ? "trialing" : (willRenew ? "active" : "canceled")
+            statusString = isTrial ? "trialing" : (willRenew || isLifetime ? "active" : "canceled")
```

### 3-6. Localizable.strings — 1.9.1 コピーへ復元 + 新キー
**`en.lproj`**（既存値を 1.9.1 値へ置換、+ lifetime 3キー）:
```
"paywall_b_title"            = "Gentle words when you need them most";
"paywall_b_subtitle"         = "Daily cards to help you through your struggles";
"paywall_b_feature_nudges"   = "Reminders at the right moment";
"paywall_b_feature_personalized" = "Adapts to your unique struggles";
"paywall_b_feature_cancel"   = "Cancel anytime, no questions asked";
"paywall_b_cta_no_trial"     = "Start Your Journey Now";
"paywall_b_trust_no_trial"   = "Cancel anytime · Satisfaction guaranteed";
"paywall_b_review"           = "\"Anicca helped me be kinder to myself.\"";
"paywall_b_plan_lifetime"    = "Lifetime";
"paywall_b_per_lifetime"     = " · pay once";
"paywall_b_lifetime_badge"   = "ONE-TIME";
"paywall_b_load_failed"      = "Couldn't load plans. Check your connection and try again.";
"paywall_b_retry"            = "Reload plans";
```
**`ja.lproj`**:
```
"paywall_b_title"            = "あなたが一番つらいとき、\nそっと届く言葉";
"paywall_b_subtitle"         = "あなたの悩みに寄り添うカードを毎日受け取ろう";
"paywall_b_feature_nudges"   = "最適なタイミングのリマインダー";
"paywall_b_feature_personalized" = "あなたの悩みに合わせて適応";
"paywall_b_feature_cancel"   = "いつでもキャンセル可能";
"paywall_b_cta_no_trial"     = "今すぐ旅を始める";
"paywall_b_trust_no_trial"   = "いつでもキャンセル · 満足保証";
"paywall_b_review"           = "「アニッチャのおかげで自分に優しくなれました」";
"paywall_b_plan_lifetime"    = "買い切り";
"paywall_b_per_lifetime"     = " · 一度きり、ずっとあなたのもの";
"paywall_b_lifetime_badge"   = "一回のみ";
"paywall_b_load_failed"      = "プランを読み込めませんでした。通信環境をご確認の上、再試行してください。";
"paywall_b_retry"            = "プランを再読み込み";
```
**de/es/fr/pt-BR**: 同様に title/subtitle/feature×3/cta_no_trial/trust_no_trial を 1.9.1 相当へ + lifetime/retry キー（暫定 EN 可）。
> `paywall_b_feature_ai` / `paywall_b_feature_feedback` は描画から外す（strings は残置で無害）。

### 3-7. `Anicca.storekit`
`ai.anicca.app.ios.lifetime`(nonConsumable, ¥5,000/$99.99) を追加。**全 .b 商品の introductoryOffer を削除**（no-trial をシミュレータでも一致）。

## PHASE 4 — TOBE UI（実描画）

### 🇺🇸 EN（買い切り無し・2プラン・no-trial）
```
   Gentle words when you need them most

   Daily cards to help you through
   your struggles

   ✓  Reminders at the right moment
   ✓  Adapts to your unique struggles
   ✓  Cancel anytime, no questions asked

   ○  Monthly Plan
      $9.99/mo
   ◉  Annual Plan           [BEST VALUE]
      $39.99/yr  ·  Just $0.11/day

   [       Start Your Journey Now       ]
   "Anicca helped me be kinder to myself."
   Cancel anytime · Satisfaction guaranteed
   Restore Purchases · Terms · Privacy
```

### 🇯🇵 JA（買い切り有り・3プラン・JP価格・no-trial）
```
   あなたが一番つらいとき、
   そっと届く言葉

   あなたの悩みに寄り添うカードを
   毎日受け取ろう

   ✓  最適なタイミングのリマインダー
   ✓  あなたの悩みに合わせて適応
   ✓  いつでもキャンセル可能

   ○  月額プラン
      ¥500/月
   ◉  年額プラン            [おすすめ]
      ¥2,000/年  ·  1日あたりたった¥5
   ○  買い切り              [一回のみ]
      ¥5,000 · 一度きり、ずっとあなたのもの

   [        今すぐ旅を始める        ]
   「アニッチャのおかげで自分に優しくなれました」
   いつでもキャンセル · 満足保証
   購入を復元 · 利用規約 · プライバシー
```

## PHASE 5 — Maestro E2E（NO-MOCK）
`aniccaios/maestro/paywall_jp3plan.yaml`:
```yaml
appId: ai.anicca.app.ios
---
- launchApp: { clearState: true }
- runFlow: flows/onboarding_to_paywall.yaml
- assertNotVisible: "3 DAYS FREE"      # トライアル表記が消えた事
- assertNotVisible: "3日間無料"
- assertVisible: "今すぐ旅を始める"     # no-trial CTA(JP)
# JPストア時のみ:
- assertVisible: "買い切り"
- tapOn: "買い切り"
- tapOn: { id: "paywall-plan-cta" }
- assertVisible: "Sign In"             # sandbox 購入シート
```
RED→GREEN（コード前は `assertNotVisible 3日間無料` で失敗）。実 sandbox 購入の最終確認は実機（fastlane不可）。

## PHASE 6 — 「買えない」検証（実購入なしで限界まで）
| # | 検証 | 手段 |
|---|---|---|
| 1 | 本番課金が通っている | ✅ RevenueCat 売上$47/28d（=Agreement Active の論理的証拠） |
| 2 | 商品 state=APPROVED | ✅ asc 確認済 |
| 3 | Paid Apps Agreement=Active | ★ cloakbrowser→Dais実ブラウザ で ASC 目視（CLAUDE.md準拠） |
| 4 | コード/解錠にバグ無し | ★ cloakbrowser で sandbox テスター作成（asc不可）→ TestFlight で Dais が新規購入1回 |
> sandbox = コード/フローの正しさを証明（≠本番のAgreement）。本番購入そのものは実購入のみ。両者の合わせ技で実質確定。
> ✅ Paid Apps Agreement = Active（Dais 確認済 2026-06-23）。

### 6-bis. ★ Xcode手動なし・Appleサインイン不要の自動購入E2E（StoreKit Config）★
**問題**: simulator で Apple サインイン不可 → 旧来は cua-driver で Xcode を開き Run 手動。**不要にする。**
**仕組み**: `aniccaios/Anicca.storekit`（既存・PHASE 3-7 で lifetime追加/trial削除済）を **test plan 経由で有効化**すると、simulator はローカル購入環境（サインイン不要）になる。
1. `aniccaios/aniccaios.xcodeproj` に test plan `PaywallStoreKit.xctestplan` を作成し、`defaultOptions.storeKitConfigurationFileReference` = `Anicca.storekit` を設定（共有スキームにも Run>Options>StoreKit Configuration を設定しコミット）。
2. テスト2種:
   - **A: XCUITest** `PaywallUITests.swift` — onboarding→paywall→各プラン tap→**ローカル購入シート Confirm**→`entitlements.active` に `anicca` が入る事を assert（サインインダイアログは出ない）。
   - **B: SKTestSession**（`import StoreKitTest`）— `let s = try SKTestSession(configurationFileNamed:"Anicca")` → `try await s.buyProduct(productIdentifier:"ai.anicca.app.ios.lifetime")` → RevenueCat entitlement 解錠を assert。UI無し・決定論。
3. fastlane lane（`aniccaios/fastlane/Fastfile`）:
```ruby
lane :test_paywall do
  run_tests(scheme: "aniccaios", devices: ["iPhone 16"], testplan: "PaywallStoreKit")
end
```
   実行 `cd aniccaios && fastlane test_paywall` → Xcode GUI無し・Appleサインイン無しで paywall→購入→解錠を緑/赤判定。
> 注意: StoreKit ローカルは `.storekit` のローカル価格（ASC実価格ではない）。フロー/解錠/コードの検証用。ASC実価格は `asc summary`、本番性は TestFlight+sandbox で別途。
> Maestro 単体（外部起動）は StoreKit Config を注入できない為、**購入テストは XCUITest/SKTestSession（test plan）で行う**。Maestro は購入以外のUIフローに使用。

## PHASE 7 — App Store スクショ + finish
- 新 scroll UI + 新 paywall(EN 2プラン / JP 3プラン) のスクショ EN/JA を version 提出と同梱。
- finish: commit→`gh pr create --base dev`→vcsdd adversary+Maestro緑+Dais実機 sandbox OK→dev→main→release/1.9.4。
```bash
git worktree remove ../anicca-paywall   # 完了後
```

## 検証チェックリスト（DONE=4D収束）
- [ ] asc: 3商品の introductory offer 空（no-trial）
- [ ] asc: JP monthly=¥500 / yearly=¥2,000、US 据置
- [ ] asc: lifetime IAP JP¥5,000（US価格は表示しないが設定）
- [ ] RC: `$rc_lifetime` package + entitlement attach
- [ ] code: hasTrialEligibility=false / 特典3 / 買い切りカード=JPのみ / 詰まり修正 / status
- [ ] strings: EN・JA が 1.9.1 コピー + 新キー
- [ ] Maestro: トライアル表記消滅 + JP買い切りカード緑
- [ ] Paid Apps Agreement=Active（cloakbrowser/Dais）
- [ ] TestFlight sandbox で Dais が新規購入→解錠 確認
- [ ] App Store: 新スクショ + 1.9.4 提出
</content>
