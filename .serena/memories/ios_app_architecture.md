# iOS App Architecture (v1.6.2)

## エントリーポイント
- `aniccaiosApp.swift` → `ContentRouterView` → (Onboarding | Auth | MainTabView)
- `MainTabView` — メインタブ + NudgeCard overlay + Paywall fullscreen cover

## 画面構成
| 画面 | View | 役割 |
|------|------|------|
| MyPath | MyPathTabView | 問題一覧、Tell Anicca、DeepDive |
| NudgeCard | NudgeCardView | 通知タップ → フルスクリーン表示 |
| Profile | ProfileView系 | アカウント・課金管理 |

## オンボーディング (4ステップ)
| Step | View | 内容 |
|------|------|------|
| welcome | WelcomeStepView | 紹介 + Sign in with Apple |
| struggles | StrugglesStepView | 13問題選択 |
| liveDemo | DemoNudgeStepView | 例Nudge体験 |
| notifications | NotificationPermissionStepView | 通知許可 |
※ liveDemo後にSoft Paywall表示（RevenueCat PaywallView）

## 13 ProblemTypes
staying_up_late, cant_wake_up, self_loathing, rumination, procrastination, anxiety, lying, bad_mouthing, porn_addiction, alcohol_dependency, anger, obsessive, loneliness

## 通知スケジュール
- staying_up_late: 5回/日 (20:00-1:00)
- その他: 3回/日 (時間帯は問題ごとに最適化)
- iOS 64通知制限: 最大32スロット × 2日間

## Nudgeバリアント
- ルールベース: 問題ごとに14-21バリアント（6言語ローカライズ済み）
- LLM生成: `/mobile/nudge/today` から日次取得、LLMNudgeCacheでキャッシュ
- 選択ロジック: Day1=決定論的 / Day2+=LLM優先→Day-Cyclingフォールバック

## サブスクリプション
- $9.99/月、1週間無料トライアル
- RevenueCat + RevenueCatUI (PaywallView)
- Free/Grace/Pro の3状態
- Freeユーザー: LLM Nudgeスキップ、月間Nudge数制限

## API連携 (Config.swift)
- /auth/apple — Apple認証
- /mobile/profile — プロフィール同期
- /mobile/entitlement — サブスク状態
- /mobile/nudge/today — LLM Nudge取得
- /mobile/nudge/feedback — フィードバック送信
- /mobile/nudge/trigger — Nudgeトリガー記録

## 認証
- Sign in with Apple (オプション)
- Device ID fallback (Keychain保存)
- Headers: device-id, user-id, X-App-Version

## 状態管理
- AppState (@MainActor singleton) + Combine
- UserDefaults: オンボーディング状態、通知設定
- Keychain: Device ID、認証情報

## テスト
- Unit/Integration: 17ファイル (Swift Testing + XCTest)
- E2E: 8 Maestroフロー (onboarding, nudge, paywall)
- 実行: `cd aniccaios && fastlane test`

## ローカライズ
6言語: ja, en, de, es, fr, pt-BR（各言語378 Nudgeキー）