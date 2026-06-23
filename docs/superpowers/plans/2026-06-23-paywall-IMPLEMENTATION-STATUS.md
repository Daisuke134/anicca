# 実装ステータス — paywall 立て直し (2026-06-23, feature/paywall-notrial-jp3plan, PR #182)

## DONE（コード・このPRに含む / BUILD SUCCEEDED + adversary PASS）
- no-trial 全面化（hasTrialEligibility=false） — PaywallVariantBView.swift
- 1.9.1 コピー復元 + 特典3（AI/feedback削除） — en/ja/de/es/fr/pt-BR strings
- 買い切り JP限定表示（Storefront.current==JPN gate） — PaywallVariantBView.swift
- プラン並び 月→年→買い切り
- 無限スピナー詰まり修正（5s timeout→再読込/復元）
- lifetime status=active — SubscriptionManager.swift
- Anicca.storekit: trial削除 + lifetime非消費型追加

## 検証
- ✅ xcodebuild build = BUILD SUCCEEDED
- ✅ fresh-context adversary（vcsdd）= PASS（全9次元, file:line evidence）
- ⏳ StoreKit local 購入E2E: test plan + SKTestSession を別途。JP lifetime を見るには test 側で storefront=JPN（Anicca.storekit の _storefront は USA のまま）
- 本番性: TestFlight+sandbox（Dais実機, 1回）+ 既存本番売上 $47/28d が「本番購入は通る」を証明

## RELEASE-GATED（1.9.4 提出と同時, Dais "submit" で実行 / このPRに含めない）
- ASC: 3商品の introductory FREE_TRIAL 削除 / JP 月¥500・年¥2,000 / lifetime IAP ¥5,000(US$99.99)
- RevenueCat: lifetime product + $rc_lifetime package + entitlement entlb820c43ab7 attach
- App Store: 新 scroll UI + 新 paywall スクショ(EN/JA) + 1.9.4 提出
- ★ ASC のトライアル削除は 1.9.4 と同時にする事（先に消すと旧1.9.3が誤表示） ★

## 残（タスク #7/#12/#10/#13）= 上記 release-gated + StoreKit harness 配線
