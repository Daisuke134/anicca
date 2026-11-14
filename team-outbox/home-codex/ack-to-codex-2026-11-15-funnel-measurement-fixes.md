# funnel measurement fixes 受領・返信

受領しました。この checkout には委任ファイル `team-outbox/muse/to-codex-2026-11-15-funnel-measurement-fixes.md` が存在しなかったため、依頼本文に記載された要点を正本として作業しました。

## 現状・成果

- **Anicca:** [`AppDelegate.swift`](../../apps/mobile/anicca-ios/aniccaios/AppDelegate.swift) で初回起動を永続判定し、`app_opened` に boolean の `first_launch` を追加しました。
- **Anicca purchase:** [`AnalyticsManager.swift`](../../apps/mobile/anicca-ios/aniccaios/Services/AnalyticsManager.swift) で RevenueCat の成功 callback だけが `purchase_completed` を送り、cancel callback は既存の `purchase_result(result=cancelled)` のままにしました。完了イベントには共通 context により `app_id` / `app_environment` が必ず付きます。これは引き続き client observation であり、決済正本は RevenueCat / Apple です。
- **`rating_prompt_shown` 0件:** [`OnboardingStep.swift`](../../apps/mobile/anicca-ios/aniccaios/Onboarding/OnboardingStep.swift) で旧 rating prompt が onboarding から削除されています。現在の post-value 経路は [`ReviewPromptCoordinator.swift`](../../apps/mobile/anicca-ios/aniccaios/Services/ReviewPromptCoordinator.swift) から `rating_store_review_requested` を送る設計で、`rating_prompt_shown` の送信 call site はありません。したがって0件は配送障害ではなく、廃止済みイベント名を集計していたことが理由です。
- **Dhamma Quotes:** このリポジトリにアプリ実装コードはありません（仕様は外部 `anicca-products` の publisher 実装を指しています）。そのため `onboarding_started` 配線欠落の原因特定・修理、および出荷ビルドへの包含はこのリポでは**判定不能（現状は未計測扱い）**です。
- **Honne:** [`AnalyticsManager.swift`](../../apps/mobile/honne-ai/BenYinFanYiAI/Services/AnalyticsManager.swift)、[`OnboardingView.swift`](../../apps/mobile/honne-ai/BenYinFanYiAI/Views/OnboardingView.swift)、[`SubscriptionService.swift`](../../apps/mobile/honne-ai/BenYinFanYiAI/Services/SubscriptionService.swift) が app target 配下にあり、app open / onboarding / purchase の計装 call site を確認しました。このリポのソース上は**計装あり**です（実際の production readback は別途必要）。
- **Sleep Reset / STUDIO CHERIE:** 両アプリの実装コードがこのリポにないため、出荷ビルドの計装有無は**判定不能（現状は未計測扱い）**です。
- チーム記録: [`docs/team/BOARD.md`](../../docs/team/BOARD.md) に監査結果を追記しました。

## 制約

根拠として指定された `anicca-ops/files/full-funnel-six-apps-2026-11-15.md` §3・§4 はこの checkout から直接参照できませんでした。上記のコード根拠と、依頼本文に転記された委任要点に基づく結果です。
