# Spec: ソフトペイウォール化 + 日本語話者への Lifetime 表示

- 日付: 2026-07-03
- ブランチ: `claude/aicca-ios-pricing-paywall-nzkmax`
- 対象: iOS アプリ `aniccaios` (Anicca / ai.anicca.app.ios), MARKETING_VERSION 1.9.0
- 依頼者: Dais

## 1. Goal (Dais verbatim の要約)

本番アプリのオンボーディング末尾のペイウォールに対し、次の2点を修正する。

| # | 現状 (バグ) | あるべき姿 (contract) |
|---|---|---|
| G1 | Lifetime(買い切り・一生)プランが日本語ユーザーに表示されない | 日本語話者には 月額 → 年額 → 買い切り の3プランを表示。英語(非日本語)には 月額 + 年額 のみ表示(買い切り非表示) |
| G2 | ハードペイウォール(閉じるボタンなし・課金しないとメイン画面に進めない) | ソフトペイウォール。画面右上に平均サイズのバツ(×)ボタン。タップで**課金せず**メイン画面(FeedRootView)へ遷移 |

Dais verbatim: 「ライフタイムのプランが日本語で出ればいい。日本語の話者に対して出ればいい」「右上にバツボタンが大きすぎず小さすぎず平均サイズ…タップしたらそのPウォールから次の画面にいける」

## 2. 現状分析 (as-is, file:line 根拠)

| 事実 | 根拠 |
|---|---|
| 本番ペイウォールは `PaywallVariantBView`。primer → planSelection の2段 | `Onboarding/OnboardingBibleViews.swift:707` `PaywallFlowContainer` |
| Lifetime は **ストアフロント国 == "JPN"** でゲート(言語ではない) | `Onboarding/PaywallVariantBView.swift:27-30` |
| `storefrontCountry` は `.task` 内で async 取得、初期値 `""` | `PaywallVariantBView.swift:20, 96-98` |
| 閉じるボタンが**存在しない**。`onDismiss` は no-op | `OnboardingBibleViews.swift:722` `onDismiss: { /* hard paywall: no-op */ }` |
| 提示は `.fullScreenCover` + `.interactiveDismissDisabled(true)` | `Onboarding/OnboardingFlowView.swift:46-53` |
| 日本語判定の既存パターン = `Locale.preferredLanguages.first` の `hasPrefix("ja")` | `Models/UserProfile.swift:48-49`, `Services/QuoteProvider.swift:770-771` |
| Lifetime のローカライズ文字列は全6言語に存在 | `paywall_b_plan_lifetime` / `paywall_b_per_lifetime` / `paywall_b_lifetime_badge` |
| Lifetime 商品は storekit / RC に定義済 | `Anicca.storekit` `ai.anicca.app.ios.lifetime` NonConsumable |
| 無課金 dismiss 用の分析イベントが既に定義済 | `AnalyticsManager` `onboardingPaywallDismissedFree` |
| 無課金 dismiss 用ハンドラ名が既にコメントに参照済 | `AppState.swift:171` `handlePaywallDismissedAsFree` |
| ソフトペイウォール用 Maestro テストが既存(実装が追いついていない) | `maestro/onboarding/03-soft-paywall.yaml` が `paywall-close-button` を期待 |

→ ソフトペイウォール設計は元々存在したが、あるコミットでハード化され、閉じるボタンとdismiss配線が失われた。本 spec でそれを復元 + lifetime を言語判定へ変更する。

## 3. Contract

### 3.1 Lifetime 表示 (G1)

```
入力: 端末の優先言語 (Locale.preferredLanguages.first), RevenueCat current offering の availablePackages
出力: lifetimePackage: Package?
規則:
  - isJapanese == true  かつ offering に .lifetime あり → その Package を返す
  - それ以外 → nil (表示しない)
  - isJapanese := (Locale.preferredLanguages.first ?? "en").lowercased().hasPrefix("ja")
不変条件:
  - 月額(.monthly)・年額(.annual)は言語に依らず常に表示 (従来通り)
  - 並び順は 月 → 年 → 買い切り (従来通り, PaywallVariantBView.swift:138)
  - storefront(国)への依存を撤廃 (async レース起因の非表示を根絶)
```

### 3.2 ソフトペイウォール (G2)

```
入力: ユーザーが右上 × をタップ
出力: ペイウォールを閉じ、FeedRootView(メイン)へ遷移。課金は発生しない
規則:
  - × ボタン: 右上 (topTrailing)、SF Symbol "xmark"、平均サイズ (アイコン ~17pt / タップ領域 ~44pt)
  - accessibilityIdentifier = "paywall-close-button"
  - primer/planSelection どちらの段でも常に表示 (PaywallFlowContainer レベルの overlay)
  - タップ時: onboardingPaywallDismissedFree を track → appState.markOnboardingComplete() → showPaywall = false
不変条件:
  - 購入成功パス(handlePaywallSuccess)は不変
  - .interactiveDismissDisabled(true) は維持 (スワイプ誤操作での離脱は防ぐ。離脱は明示的な × のみ)
  - 課金しない dismiss でも isOnboardingComplete=true (以降ペイウォールを再表示しない)
```

## 4. 触るファイル (境界)

| ファイル | 変更 |
|---|---|
| `aniccaios/aniccaios/Onboarding/PaywallVariantBView.swift` | lifetime ゲートを言語判定へ。未使用の storefront コードを削除 |
| `aniccaios/aniccaios/Onboarding/OnboardingBibleViews.swift` | `PaywallFlowContainer` に `onDismiss` param + 右上 × overlay |
| `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift` | `onDismiss` を `handlePaywallDismissedAsFree` に配線 |
| `aniccaios/maestro/onboarding/03-soft-paywall.yaml` | 現行フロー/`feed-scroll` に整合、lifetime(ja)検証追加 |
| `aniccaios/maestro/v1.8.0/05-paywall_variant_b_ja.yaml` | stale な dismiss id / 文言を現行に整合 |

## 5. E2E 判定 (GATE 3)

| 項目 | 判定 |
|---|---|
| E2E 必要か | **必要**。ペイウォールは課金導線 = user-facing の中核 |
| テスト | `maestro/onboarding/03-soft-paywall.yaml` (× → feed-scroll 到達, 無課金) + ja 起動で lifetime "買い切り" 可視を assert |
| 実機確認 | Dais が simulator/実機で ① ja: 月/年/買い切り3枚 ② en: 月/年2枚 ③ × で無課金メイン到達 を目視 |

## 6. 実行環境の制約 (honesty)

本セッションは Linux リモートコンテナで実行されており、iOS toolchain(xcodebuild / swift / maestro / asc)は**存在しない**(`uname` = Linux, `which` 全て not found)。
従ってビルド・Maestro 実走・App Store Connect 提出は**このセッションでは物理的に実行不可**。

- 本セッションの成果物 = コード変更 + Maestro yaml + 本 spec を push + draft PR。
- ビルド/E2E/提出は Mac 上で以下を実行 (§7)。

## 7. Mac 側リリース手順 (Dais が実行)

```bash
cd aniccaios
# 1. バージョン bump (App Store は同一ビルド番号を再提出不可)
fastlane set_version version:1.9.1   # or 適宜
# 2. Maestro E2E (simulator)
maestro test maestro/onboarding/03-soft-paywall.yaml
# 3. 完全自動リリース (build → upload → wait → submit for review)
fastlane full_release
```

`fastlane full_release` = build+upload+wait_for_processing+submit_review。完了で「審査待ち(Waiting for Review)」状態になる。
