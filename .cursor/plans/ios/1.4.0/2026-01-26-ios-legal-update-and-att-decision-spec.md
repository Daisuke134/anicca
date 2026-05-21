## 概要

目的は2つ：

1. iOSアプリ内フッター（`LegalLinksView`）から開く **Privacy Policy / Terms** を、現在のiOSアプリ実装と一致する内容に更新する（英語/日本語）。
2. オンボーディング内の **ATT許可ステップ** を「残す/移動/削除」のどれにするかを、計測可能な形で意思決定し、必要な計測イベントも定義する。

重要：現状コードには **HealthKit/Motion/センサー同期/日次メトリクス送信** が残っており、「HealthKitはもう使っていない」前提と矛盾している可能性がある。法務文面は **コード上の実態をソース・オブ・トゥルース** とし、必要なら機能側の削除/無効化もこのSpecでスコープに含める。

### レビューの入口（重要）

他エージェントが `dev` ブランチ作業中でもレビューできるように、**Worktree** と **ブランチ** を明記する。

| 項目 | 値 |
|---|---|
| Worktree（ローカル） | `/workspace/worktrees/anicca-proactive-legal` |
| ブランチ | `cursor/anicca-ios-legal-update-e2d1` |
| Spec | `.cursor/plans/proactive/2026-01-26-ios-legal-update-and-att-decision-spec.md` |

レビュー方法（ローカル例）：

| # | 手順 |
|---|---|
| 1 | `cd /workspace/worktrees/anicca-proactive-legal` |
| 2 | `git log --oneline --decorate -n 20` |
| 3 | `git diff origin/dev..HEAD` |

---

## As-Is（現状）

### Legalリンク（iOS）

- `MyPathTabView` フッターに `LegalLinksView` が表示される。
- `LegalLinksView` の遷移先
  - Privacy: `https://aniccaai.com/privacy/<lang>`（`lang` は `AppState.shared.userProfile.preferredLanguage.rawValue`）
  - Terms: Apple Standard EULA 直リンク（`https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`）

### Privacy / Terms（Web）

- `apps/landing/app/privacy/en|ja/page.tsx` に現行文面あり
  - デスクトップ/Stripe/Supabase/Slack/Google連携/音声などの記述が含まれている
- `apps/landing/app/terms/page.tsx` は日本語の利用規約（デスクトップ/Stripe前提の記述を含む）
- 英語の `/terms/en` が存在しない（または未整備）

### オンボーディング（iOS）

`OnboardingFlowView` は以下の5ステップ：

`welcome → value → struggles → notifications → att`

ATT ステップ（`ATTPermissionStepView`）は「Continue」を押すと `ATTrackingManager.requestTrackingAuthorization` を呼ぶ。

> Note: このAs-Isは「変更前の状態」を表す。PR実装ではATTをオンボーディングから外している（後述）。

### “HealthKitはもう使っていない”前提とのギャップ

UI（SwiftUI Views / Settings）上はセンサーのトグルや許可導線が見当たらず、「ユーザーが触るフロント導線としては使っていない」ように見える。

しかしコード上は以下が残存しており、「サーバー側がONにしたらバックグラウンドで動き得る」状態になっている：

- `AppDelegate`（オンボーディング完了済み時）で `HealthKitManager.shared.configureOnLaunchIfEnabled()` を呼ぶ
- `MetricsUploader` が `HealthKitManager` / `MotionManager` を参照し、`/mobile/daily_metrics` に送信するパスがある
- `InfoPlist.strings` に `NSHealth*` / `NSMotionUsageDescription` が存在
- `SensorAccessState` / `SensorAccessSyncService` などセンサー連携の状態管理が存在
  - `SensorAccessSyncService.fetchLatest()` がサーバーから `sleepEnabled/stepsEnabled/motionEnabled/screenTimeEnabled` を pull し、`AppState` にマージできる構造がある（UIが無くてもサーバー起点で有効化され得る）

上記が「実運用では使っていない（常にOFF）」の可能性もあるため、実装前に「完全削除 or 完全無効化」を決め、文面とコードを一致させる必要がある。

---

## To-Be（変更後）

### 1) 法務ページの方針（単一の決定）

**決定**：iOSアプリ内のTermsリンクを「Apple EULA直リンク」ではなく、`aniccaai.com/terms/<lang>` に統一する。  
理由：アプリ実態（課金/計測/通知/データ取り扱い）をApple EULAだけではカバーできないため。Apple EULAは Termsページ内で参照リンクとして明示する。

### 2) Privacy Policy（EN/JA）

**決定**：Privacy Policy から「デスクトップ/Stripe/Supabase/Slack/Google連携」等の記述を削除し、iOSアプリで実際に扱う項目に限定して再記述する。

最低限含める事実（iOS実装からの確定事項）：

- **識別子**：device-id（`identifierForVendor` 相当のIDFV）を使用（サーバー送信あり）
- **認証**：Sign in with Apple（Apple user id、メールは提供された場合のみ等）
- **計測SDK**：Mixpanel / Singular / Superwall / RevenueCat（各SDKが収集する範囲の説明を「利用目的」とセットで記述）
- **ATT**：許可の有無でIDFAが利用可能になること、許可しなくてもアプリ機能は使えること
- **通知**：通知権限、通知タップ時の挙動（NudgeCard表示）
- **サーバー**：`ANICCA_PROXY_BASE_URL` のAPIへ必要データを送信する（user-id/device-idヘッダ、プロファイル同期、nudge取得など）
- **保存**：端末内（UserDefaults/Keychain）とサーバー側（PostgreSQL等）の役割分担

「HealthKit/Motion/ScreenTime」については、次のどちらかに統一する：

- **A. 完全削除**：コード/権限文言/ポリシーからも削除（推奨：今回のユーザー要望に一致）
- **B. 機能は残すがデフォルトOFF**：その場合は Privacy Policy に「ユーザーが明示的に有効化した場合のみ取得」を明記し、オンボーディングでは要求しないことを明示

このSpecでは **A（完全削除）** を基本方針として進める（ユーザー要望「HealthKit不要」に強く整合）。

完全削除の理由（明確化）：

- Privacy Policyに「HealthKit等は取得しない」と書き切るには、UIに無いだけでは不十分で、内部的にも取得・送信し得る余地をゼロにする必要がある
- プロジェクトルール「未使用コードは容赦なく削除する」に一致する
- Apple審査・プライバシー表示（用途説明文）においても、不要な権限文言を残さない方が安全

### 3) Terms（EN/JA）

**決定**：`/terms/en` と `/terms/ja` を用意し、`/terms` はブラウザ言語でリダイレクトする。

Terms に含める要点：

- 対象は iOS アプリ（Anicca）であること
- 課金：iOSの自動更新サブスクはApple経由、解約/返金はApple規約に従う（Apple Standard EULA/Appleの返金ポリシー参照）
- 免責：健康/医療/法的助言ではない、行動変容の補助である
- 禁止事項/知財/規約変更/準拠法

### 4) iOSアプリ側リンク

- `LegalLinksView` の Terms リンクを `https://aniccaai.com/terms/<lang>` に変更
- 表示ラベルは現状の `legal_privacy_policy` / `legal_terms_of_use` を維持（UI/UX変更禁止のため）

### 5) ATT（App Tracking Transparency）の扱い

**決定**：本アプリでは **ATTの許可リクエストを表示しない**（オンボーディング中も、オンボーディング後も出さない）。

理由：

- 体験上の離脱要因になりやすい
- 計測は **SKAdNetwork（SKAN）を主軸**にする（ユーザー許可不要）
- 「プライバシーを大事にする」メッセージとの整合性を優先する

### 6) Mixpanelでの離脱検知（計測設計）

現状イベントは「完了」しか取れていない：

- `onboarding_notifications_completed`
- `onboarding_att_completed`

ATT自体を出さない方針のため、ATT画面起因の離脱ファネルは不要。
オンボーディング完了ファネルは以下を基本とする：

- `onboarding_notifications_completed` → `onboarding_completed`

---

## 実装結果（このSpecのTo-Beが最終的にどう実装されたか）

### iOS: ATTは「出さない」（仕様変更・次の修正タスク）

現状PR実装は「オンボーディング後（初回NudgeCard後）に1回だけ提示」だが、方針を **完全撤去**に変更する。

| 項目 | 仕様 |
|---|---|
| 方針 | **ATT許可リクエストは表示しない**（onboarding中もonboarding後も） |
| iOS実装 | ATT提示導線・永続化キー・ATTイベントを削除する |

削除対象（予定）：

| 種別 | 対象 |
|---|---|
| iOS UI/導線 | `ATTPermissionStepView` の提示導線（`MainTabView` / `AppState`） |
| 永続化キー | `com.anicca.attPromptPresented` |
| Info.plist | `NSUserTrackingUsageDescription`（ATTを出さないなら削除） |
| Analytics | `onboarding_att_viewed` / `onboarding_att_prompt_shown` / `onboarding_att_status`（不要なら削除） |

### iOS: センサー系（HealthKit/Motion/ScreenTime/日次メトリクス）を完全削除（実装済み）

**削除した理由**：UIに出ていなくても、内部的に取得/送信し得る余地があるとPrivacyに「取得しない」と書き切れないため。実装と法務文面を一致させる。

| 項目 | 対応 |
|---|---|
| センサー機能実装 | `HealthKitManager` / `MotionManager` / `ScreenTimeManager` / `SensorAccessSyncService` / `MetricsUploader` / `SensorAccessState` を削除 |
| 実行経路 | `AppDelegate` と `AppState` から関連呼び出しを削除 |
| Info.plist | `NSHealth*` / `NSMotionUsageDescription` / `NSAlarmKitUsageDescription` / `BGTaskSchedulerPermittedIdentifiers(com.anicca.metrics.daily)` を削除 |
| InfoPlist.strings | `NSHealth*` / `NSMotion*` / `NSAlarmKit*` 文言を削除 |

**レビュー指摘の反映予定（未実装・次の修正タスク）**

| 指摘 | 現状 | 修正方針 |
|---|---|---|
| `mobile/daily_metrics` の残骸 | `Config.swift` にURL定義が残っている可能性がある | 未使用なら削除し、「完全削除」をより強く担保する |

### iOS: Legalリンク（Terms）を自社ページへ統一（実装済み）

| 項目 | 対応 |
|---|---|
| Termsリンク | `https://aniccaai.com/terms/<lang>` に変更（Apple EULAはWeb Terms内で参照） |
| ファイル | `aniccaios/aniccaios/Views/LegalLinksView.swift` |

### Web: Privacy / Terms をiOS前提に更新（実装済み）

| 項目 | 対応 |
|---|---|
| Privacy EN/JA | desktop/Stripe/Supabase/Slack/Google/音声などの記述を撤去し、iOS実態（通知/ATT/RevenueCat/Superwall/Mixpanel/Singular等）へ更新 |
| Terms | `/terms` を言語リダイレクトに変更し、`/terms/en` と `/terms/ja` を新設（Apple課金/Apple EULA参照を明記） |

**レビュー指摘の反映予定（未実装・次の修正タスク）**

| 指摘 | 現状 | 修正方針 |
|---|---|---|
| Privacy本文と「マイク/カメラ権限宣言」のズレ | Privacy本文にマイク/カメラの扱いを明記していない | 実装で「実際に使わない」なら Info.plist から権限宣言・許可導線を削除する（使うならPrivacy本文に目的を追記） |

---

## Netlify（プレビュー確認）運用

| 目的 | 推奨手段 | 理由 |
|---|---|---|
| PRの見た目確認 | GitHub連携 Deploy Preview | トークン不要、PRごとにURLが出る |
| ローカル/Cloud Agentから手動デプロイ | Netlify CLI + `NETLIFY_AUTH_TOKEN` | Cloud環境ではブラウザログインができないためトークンが必要 |

トークンの設定先（例）：

| # | どこに設定 | 何を設定 |
|---|---|---|
| 1 | CI / 実行環境の環境変数 | `NETLIFY_AUTH_TOKEN`（Personal Access Token） |


---

## 実装方針（ファイル別・何をどう変えるか）

※ このセクションは「チャットで合意した内容」を実装に落とすためのチェックリスト。UIデザイン変更は行わず、リンク先/文面/不要コード削除に限定する。

| 変更カテゴリ | ファイル | 変更内容 |
|---|---|---|
| iOS: Termsリンク | `aniccaios/aniccaios/Views/LegalLinksView.swift` | Termsリンクを Apple直リンク → `https://aniccaai.com/terms/<lang>` に変更（Privacyは現状維持） |
| Web: Privacy EN/JA | `apps/landing/app/privacy/en/page.tsx` / `apps/landing/app/privacy/ja/page.tsx` | desktop/Stripe/Supabase/Slack/Google連携等の記述を削除し、iOS実態（RevenueCat/Superwall/Mixpanel/Singular/ATT/通知/サーバ送信）へ更新 |
| Web: Terms EN/JA | `apps/landing/app/terms/en/page.tsx`（新規） / `apps/landing/app/terms/ja/page.tsx`（新規or移設） | iOS前提のTermsを整備。Apple課金・解約・返金の扱い、免責等を明記し、Apple Standard EULAへの参照を含める |
| Web: /terms ルーティング | `apps/landing/app/terms/page.tsx` | `/terms` をブラウザ言語で `/terms/en` or `/terms/ja` にリダイレクトへ変更（privacyと同パターン） |
| iOS: センサー完全削除 | `aniccaios/aniccaios/Services/HealthKitManager.swift` ほか | HealthKit/Motion/ScreenTime/センサー同期/日次メトリクス送信の仕組みを完全削除（またはビルド・実行経路から完全に切断） |
| iOS: AppDelegate掃除 | `aniccaios/aniccaios/AppDelegate.swift` | `HealthKitManager.configureOnLaunchIfEnabled()`、`MetricsUploader`登録/スケジュール、`SensorAccessSyncService.fetchLatest()` 等の呼び出しを削除 |
| iOS: InfoPlist文言 | `aniccaios/aniccaios/Resources/*/InfoPlist.strings` | `NSHealth*` / `NSMotionUsageDescription` / 不要な説明文言を削除（通知/ATT/マイク等、必要なものだけ残す） |

---

## 受け入れ条件

| # | 条件 | 判定方法 |
|---|---|---|
| 1 | iOSフッターのPrivacyリンクが `https://aniccaai.com/privacy/<lang>` のままで、内容がiOS実態に一致している | ブラウザで確認（EN/JA） |
| 2 | iOSフッターのTermsリンクが `https://aniccaai.com/terms/<lang>` を開く | 実機/シミュレータでタップ確認 |
| 3 | Privacy/Termsからデスクトップ/Stripe/Supabase/Slack/Google連携等の記述が消えている | ページ内容確認 |
| 4 | 「HealthKit等は使っていない」前提に合わせ、コード/権限文言/ポリシーの整合が取れている | コード検索 + ページ内容確認 |
| 5 | ATTの扱い（オンボーディング内/外）がSpec通りに確定し、必要イベントが定義されている | Specレビューで確定（実装は別PRでも可） |

---

## To-Be チェックリスト

| # | To-Be | 状態 |
|---|---|---|
| 1 | `apps/landing` の Privacy EN/JA を iOS 実態に合わせて更新 | ☐ |
| 2 | `apps/landing` の Terms を `/terms/en` `/terms/ja` に分離し、`/terms` はリダイレクト | ☐ |
| 3 | iOS `LegalLinksView` の Terms 遷移先を `aniccaai.com/terms/<lang>` に変更 | ☐ |
| 4 | HealthKit/Motion/センサー系を「完全削除」方針で整理（コード/権限/文面） | ☐ |
| 5 | ATTをオンボーディングから外す方針を適用し、後段提示の仕様を定義 | ☐ |
| 6 | ATT離脱検知のMixpanelイベント（viewed/prompt/status）を定義 | ☐ |

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|---|---|---|
| 1 | 3 | `LegalLinksView` が想定URLを開く | ☐（手動） |
| 2 | 1,2 | Privacy/Terms ページがEN/JAで表示できる | ☐（手動） |
| 3 | 4 | HealthKit/Motion関連が削除されてもビルドが通る | ☐（実装後に限定テスト） |
| 4 | 5,6 | ATTイベントがファネル構築に必要十分 | ☐（Mixpanel設定確認） |

---

## E2E シナリオ（Maestro）

※ UI変更が入る場合のみ作成（今回のSpec段階では実装しない）

| # | フロー | 目的 |
|---|---|---|
| 1 | `mypath-footer-legal-links` | フッターの Privacy/Terms 表示とタップ導線確認 |

---

## Skills / Sub-agents

| ステージ | 使用するもの | 用途 |
|---|---|---|
| Spec作成 | `/plan` | 仕様の整理 |
| 実装後レビュー | `/codex-review` | Review Gate |
| 実装前の広範囲探索 | Subagent: Explore | センサー/計測/法務リンク影響範囲の探索 |

---

## 境界（Boundaries）

### 触るファイル（予定）

- `aniccaios/aniccaios/Views/LegalLinksView.swift`
- `apps/landing/app/privacy/**`
- `apps/landing/app/terms/**`
- （HealthKit完全削除する場合）`aniccaios/aniccaios/Services/HealthKitManager.swift` 等の関連一式
- （ATT移動する場合）`aniccaios/aniccaios/Onboarding/*` と関連イベント

### 触らない（または要承認）

- レイアウト/色/フォント/余白などUIデザイン変更（禁止）
- 既存のユーザー体験を大きく変える追加機能（このSpecの範囲外）

---

## ローカライズ

| key | EN | JA |
|---|---|---|
| `legal_privacy_policy` | Privacy Policy | プライバシーポリシー |
| `legal_terms_of_use` | Terms of Use (EULA) | 利用規約 (EULA) |

※ 表示文言は原則維持（UI変更禁止）。必要なら後続で文言変更の承認を取る。

---

## ユーザー作業（実装前）

| # | タスク | 手順 | 取得するもの |
|---|---|---|---|
| 1 | MixpanelでATT離脱を確認 | Funnelを `onboarding_notifications_completed → onboarding_att_completed` で作成し、過去1〜3週間のCVRを見る | 離脱率の数字（スクショ/メモ） |

※ エージェント環境からMixpanelワークスペースへAPIアクセスする手段が無い場合、ここはユーザー側で実施（数字を共有）→最終決定に反映。

---

## 実行手順（実装フェーズ用：今回は未実行）

| # | 手順 | コマンド |
|---|---|---|
| 1 | 変更ファイルのlint（Web側のみ） | `cd apps/landing && npm test`（または既存のlintコマンド） |
| 2 | iOSビルド確認（変更範囲のみ） | `cd aniccaios && fastlane build_for_simulator` |

---

## レビューチェックリスト

| # | 観点 | チェック |
|---|---|---|
| 1 | 事実整合 | 「実装に無いもの（desktop/Stripe/HealthKit等）」が文面に残っていないか |
| 2 | 過不足 | iOSで実際に使うSDK/送信先が漏れていないか |
| 3 | UI禁止遵守 | レイアウト変更なし（リンク先/文面のみ） |
| 4 | 後方互換 | 古いリンク/ページが404にならない導線（リダイレクト含む） |
| 5 | 計測設計 | ATT移動の効果が測れるイベント設計になっているか |

