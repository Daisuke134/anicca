# task-001: ペイウォールCVR改善（0% → 10%目標）

## Source
- メトリクス: ペイウォール表示55人→トライアル0人（7日間、CVR 0.0%）
- RevenueCat blog: "5 overlooked paywall improvements" (Dec 2025)
- RevenueCat blog: "How four paywall redesigns boosted conversions" (Nov 2025)

## Problem
オンボーディング完了後にRevenueCat PaywallViewを表示しているが、
55人がペイウォールを見て誰もトライアルを開始していない。
根本原因の仮説:
1. ペイウォール表示前に十分な価値体験がない
2. CTA文言が魅力的でない（RevenueCatデフォルト）
3. ペイウォール dismiss 後の再表示戦略がない
4. 年額プランの割引率が見えにくい

## Spec

### 1. DemoNudgeStepView の改善（価値体験の強化）
現在のオンボーディングフロー:
welcome → struggles → liveDemo → notifications → paywall

liveDemo（DemoNudgeStepView）でユーザーに実際のNudgeを体験させているが、
この体験をもっとインパクトのあるものにする:
- 「あなたの選んだ問題タイプに基づいて、こんなNudgeが届きます」のプレビュー表示
- ユーザーの struggles 選択に基づいてパーソナライズされたデモ
- 「実際に使ってみた人の声」（ソーシャルプルーフ）を1-2件表示

### 2. ペイウォール直前のバリュープロップ画面追加
notifications ステップ完了後、ペイウォール表示前に:
- 「あなた専用のプランが準備できました」的な画面を挟む
- 選んだ struggles に基づく「こんな改善が期待できます」リスト
- 「7日間無料・いつでもキャンセル」を大きく表示
- 実装: 新しい OnboardingStep case `.valueRecap` を追加

### 3. ペイウォール dismiss 後の再表示戦略
現在: dismiss → handlePaywallDismissedAsFree() → そのまま無料で使用開始
改善: 
- 無料プラン開始後、アプリ内で価値を感じたタイミング（3日後、7日後）で再表示
- NudgeCardView で👍タップ時に「Proならもっと多くのNudgeが届きます」バナー
- Settings から手動でペイウォール再表示可能にする（既にあるか確認）

### 4. RevenueCat ダッシュボードでの調整（手動・後で）
- CTA文言の日本語最適化
- 年額プランの「Save XX%」を目立たせる
- アニメーション付きCTAボタン（RC Paywalls v2で対応可能か調査）

## Files
- aniccaios/Onboarding/OnboardingFlowView.swift
- aniccaios/Onboarding/OnboardingStep.swift
- aniccaios/Onboarding/DemoNudgeStepView.swift
- aniccaios/Onboarding/ValueRecapStepView.swift（新規）
- aniccaios/Views/NudgeCardView.swift（Pro誘導バナー）
- aniccaios/Services/PaywallRetriggerService.swift（新規）

## Tests
- ユニットテスト: OnboardingStep の新しい case が正しく遷移する
- ユニットテスト: PaywallRetriggerService のタイミングロジック
- Maestro E2E: オンボ完了→バリューリキャップ→ペイウォール表示の流れ

## Priority: 1（最重要 — MRR直結）
