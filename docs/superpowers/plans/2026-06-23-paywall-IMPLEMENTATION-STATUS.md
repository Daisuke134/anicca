# 実装ステータス — paywall 立て直し (2026-06-23, feature/paywall-notrial-jp3plan, PR #182)

★ 方針 (Dais 2026-06-23): no-human-in-loop。AI が pbxproj 編集・E2E・RevenueCat・TestFlight まで全部やって自分で検証。
★ 唯一の人間タスク = 新 App Store スクショ作成 + 1.9.4 へアップロード。その後 Anicca が asc で提出。

## ✅ DONE（コード・PR #182 / BUILD SUCCEEDED + adversary PASS 9/9）
- no-trial 全面化（hasTrialEligibility=false）
- 1.9.1 コピー復元 + 特典3（AI/feedback削除）— en/ja/de/es/fr/pt-BR
- 買い切り JP限定表示（Storefront==JPN gate）/ 並び 月→年→買い切り
- 無限スピナー詰まり修正（5s→再読込/復元）
- lifetime status=active / Anicca.storekit: trial削除+lifetime追加

## 🔄 残（全部 AUTONOMOUS、自分で E2E 緑まで iterate）
| # | タスク | 種別 |
|---|---|---|
| #7  | StoreKit/Maestro E2E harness（test target/test plan, pbxproj編集OK）。storefront=JPN で lifetime も検証 | autonomous |
| #12 | fastlane test_paywall 緑まで iterate（no-trial表記消滅 / 月→年→買い切り(JP) / 購入→解錠） | autonomous |
| #10 | RevenueCat: lifetime product + $rc_lifetime package + entitlement attach / ASC: trial削除・JP値下げ・lifetime IAP | autonomous |
| #13 | 1.9.4 ビルド→TestFlight アップロード（fastlane, asc API key）+ sandbox 最終確認 | autonomous |
| #17 | ★ 新スクショ作成 + 1.9.4 へアップロード ★ | HUMAN（唯一） |
| #18 | Dais『uploaded』後、asc で 1.9.4 を提出（ASC価格はこの提出と同期） | autonomous |

## シーケンス
E2E harness 構築(#7) → 緑まで iterate(#12) → RC/ASC 適用(#10) → 1.9.4 build+TestFlight(#13) → sandbox 自己検証 → [人間] スクショ upload(#17) → asc 提出(#18)。
> ASC のトライアル削除/価格変更は #13/#18（リリース）と同期。先に消すと旧1.9.3が誤表示するため。
