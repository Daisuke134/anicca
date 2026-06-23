# 実装ステータス — paywall 立て直し (2026-06-23, feature/paywall-notrial-jp3plan, PR #182)

★ 方針 (Dais 2026-06-23): NO HUMAN IN LOOP（Dais も tap しない）。AI が pbxproj 編集・XCUITest・StoreKit config・E2E・RevenueCat・TestFlight まで全部やって自分で検証。Dais は提出前に「見るだけ」。
★ 唯一の人間関与 = ① 提出前にスクショ/動作を「見る」② 新 App Store スクショを作成し 1.9.4 にアップロード（提出物として）。tap も検証も AI。

## simulator で paywall を越える方法（Apple公式で確定）
- simulator は実Apple ID/sandbox 購入 **不可**。**StoreKit Configuration File（.storekit）= ログイン不要・無料で購入完了・Simulator対応** が唯一解。
- `Anicca.storekit`（lifetime追加・trial削除済）を **scheme/test plan で有効化** → サインインダイアログ消滅・ハードペイウォール突破。
- 出典: developer.apple.com/documentation/storekit/testing-at-all-stages-of-development-with-xcode-and-the-sandbox

## ✅ DONE（コード・PR #182 / BUILD SUCCEEDED + adversary PASS 9/9）
- no-trial 全面化 / 1.9.1 コピー復元+特典3 / 買い切りJP限定 / 月→年→買い切り / 詰まり修正 / lifetime status / storekit

## 🔄 残（全部 AUTONOMOUS）
| # | タスク | 種別 |
|---|---|---|
| #7  | scheme に Anicca.storekit 設定 + XCUITest harness（onboレ→paywall→購入→解錠, ログイン不要）| 🤖 |
| #12 | fastlane/xcodebuild test を緑まで iterate + EN/JA(JP storefront ¥+買い切り) スクショ自動取得 | 🤖 |
| #10 | RevenueCat: lifetime product+package+entitlement / ASC: trial削除・JP値下げ・lifetime IAP | 🤖 |
| #13 | 1.9.4 build → TestFlight アップロード + sandbox 自己検証 | 🤖 |
| #17 | 新 App Store スクショ作成 + 1.9.4 へアップロード（提出物）| 🙋 Dais（見る/上げるのみ）|
| #18 | Dais『uploaded』後 asc で 1.9.4 提出 | 🤖 |

## シーケンス
scheme config + XCUITest(#7) → 緑+スクショ(#12) → RC/ASC(#10) → build+TestFlight(#13) → [Dais 見る+スクショupload(#17)] → asc 提出(#18)

## ✅ App Store スクショ（2026-06-23 Dais 承認済）
- EN/JA 各4枚、GOAT 完全コピー + 新scroll UI + 3枚目「Choose From 8 Themes / 8種以上の豊富なテーマ」
- 日本語=Hiragino W6 太字、phone を GOAT 同等に下げ余白拡大、SF Pro Rounded Bold(EN)
- 保存: `aniccaios/fastlane/screenshots/{en-US,ja}/` + `~/anicca-project-store-assets/1.9.4/`
- これが 1.9.4 にアップロードする確定版（es/de/fr は EN 画像流用）

## 次: JP storefront 実画面（¥500/¥2,000/¥5,000 + 買い切り）を StoreKit config(storefront=JPN) で確認

## JP価格設定 進捗（2026-06-23, Dais go 受領・1つずつ実行）
- ✅ JP-1 monthly.b JP ¥500 価格変更 作成（発効 2026-06-24, preserve既存購読者, US base $9.99 不変）pricePoint=¥500
- ✅ JP-2 yearly.b JP ¥2,000 価格変更 作成（発効 2026-06-24, US base $39.99 不変）pricePoint=¥2000
- ⏳ JP-3 トライアル削除 yearly.b/weekly.b（P3D intro）
- ⏳ JP-4 lifetime IAP 新規 ai.anicca.app.ios.lifetime + JP ¥5,000
- ⏳ JP-5 RC offering anicca_variant_b に lifetime package 追加
- ASC ids: monthly.b=6769264298 / yearly.b=6762049696 / weekly.b=6762049888 / group(B)=22027036
