1. 改訂後のオンボーディング体験（例）
端末言語が日本語のユーザー “Akira” のケース:
Welcome
「Aniccaが毎日の習慣を声で支えます。」
CTA: “Get Started”。
Mic Permission → Notification Permission
目的説明つきで許可をリクエスト。許可後0.5秒で自動遷移。
Sign in with Apple
純正黒ボタン。Face ID 認証 → /auth/apple に送信 → 成功で AppState.authStatus = .signedIn(userId…)。
氏名とメールが一度だけ返るので UserProfile.displayName に即保存。
Habit Selection (Wake / Training / Bedtime)
Wake を有効化 → 時間選択 (06:00)。
Training を有効化 → 時間選択 (19:00)。
Bedtime は今回スキップ。
Habit Follow-up (選択済みハビットだけが即座に表示)
Wake: カード直下にテキストフィールド “Where do you usually wake up?”（プレースホルダー “Third-floor bedroom”）。
入力すると UserProfile.sleepLocation = "Third-floor bedroom in Tokyo apartment"。
Training: “Which training do you want to focus on every day?”（タイル選択: Push-up / Core / Cardio / Stretch）。
複数選択可、選ばなければ空のまま。
Bedtimeは未選択なので質問は出ない。
Sleep location は Wake/B edtime 共通でここ一度だけ聞く。
Completion Card
現在20:10の場合 → 「You’re all set! Next up: tonight at 19:00 I’ll nudge you for Training.」
ロジック: 現在時刻から最も近いハビット (19:00 Training) を計算。
“Continue” でメイン画面へ。
メイン画面 (SessionView)
青い “Talk to Anicca” ボタン。
右上ギアは常時表示：
Habitの時間変更
Follow-up回答(睡眠場所, Trainingフォーカス)の再編集
言語Picker (自動設定済み, いつでも変更可)
Sign Out ボタン（AppStateリセット）
Wake習慣の声かけ例 (翌朝6:00):
> 「おはよう、Akiraさん。三階のベッドルームから起きる頃だね。身体を優しく起こして、1日のスタートを整えよう。」
Training習慣の声かけ例 (日19:00):
> 「Akiraさん、Push-upメニューの時間だよ。準備ができたら10回1セットから始めようか。」


iOSログイン＋パーソナライズ統合計画
<タスク分析>

主要タスク: Sign in with Apple をオンボーディング中盤に挿入し、選択した習慣に応じたフォローアップ質問を同画面で行い、取得データをプロンプトへ反映させる。
技術スタック: iOS (SwiftUI・Combine・AuthenticationServices・WebRTC)、Node.js/Express、PostgreSQL。既存バージョンは据え置き。
重要要件: UIテキストは英語、プロンプトは日本語。言語は端末ロケールで自動設定し、設定画面でのみ変更可能。Wake/Bedtime で共通の寝場所、Training は毎日のフォーカスを入力させる。Sign in with Apple は純正ボタン・優先配置。
潜在課題: Apple IDの氏名は初回のみ→即保存必須、匿名状態でのデータ保存防止、同期失敗時のリトライ、Completionカードの近日スケジュール算出。
実装順序: 認証基盤 → ルーティング＆ガード → UserProfile/同期 → ハビット選択＋フォローアップUI → 設定画面拡張 → プロンプトテンプレート更新 → API/DB → Completionロジック → ドキュメント。
重複実装防止: AppState と HabitPromptBuilder を拡張し、質問はハビットカード内で完結。新API は /auth/apple と /mobile/profile のみ追加。
</タスク分析>
実装ステップ
AppState 認証対応  
AppState.swift に AuthStatus と UserCredentials を追加し、authStatus を導入。init で保存済みクレデンシャルを復元し、updateHabit 系は .signedIn のみ許可。userProfile を sleepLocation / trainingFocus など新フィールド付きで保持。
ContentView ルーティング更新  
ContentView.swift を authStatus ベースで分岐。AuthenticationProcessingView を追加し、サインイン処理中の待機UIを提供。
Auth調停レイヤー  
Authentication/AuthCoordinator.swift と AuthPresentationDelegate.swift を新設し、startSignIn() → /auth/apple 連携 → AppState 更新 → エラー時リセット。signOut() は AppState.resetState() を呼ぶ。
オンボーディング拡張  
OnboardingStep を welcome → microphone → notifications → account → habits の順に整理し、ハビットカード内でフォローアップを表示する。Wake選択時にテキストフィールド “Where do you usually wake up?” を一度だけ表示（プレースホルダー “Third-floor bedroom”）。Trainingでは “Which training do you want to focus on every day?” のタイル選択。Bedtime固有質問は省略し、寝場所は Wake で収集した値を再利用。保存時に AppState.updateUserProfile を呼び、sleepLocation/trainingFocus を更新。
Completion画面追加  
新規 Onboarding/CompletionStepView.swift を作成し、You’re all set! Next up: {closestHabit} 形式で近日予定を表示。最短スケジュールを計算するヘルパを AppState か HabitScheduleFormatter として実装。
設定画面拡張  
SettingsView.swift に常設のギアメニューとして、Habit時間編集＋Follow-up回答編集（Sleep location, Training focus）＋ Language Picker ＋ Sign Out ボタンを提供。フォローアップ編集は新規 Settings/PersonalizationFormView.swift をシートで表示し、共通フォームを再利用。
Profile同期サービス  
Services/ProfileSyncService.swift を actor として実装し、enqueue(profile:) → /mobile/profile PUT を行う。Wake/Trainingのフォローアップ保存時に呼び出し、失敗時は再試行キューに残す。
プロンプトテンプレート更新  
Resources/Prompts/common.txt を日本語で再構成し、${LANGUAGE_LINE}, ${USER_NAME}, ${TASK_TIME}, ${TASK_DESCRIPTION} のみ保持。wake_up.txt と bedtime.txt に ${SLEEP_LOCATION} を埋め込む文を用意し、training.txt には ${TRAINING_FOCUS_LIST} を差し込む文を用意。HabitPromptBuilder にレンダリングヘルパを追加し、空値は行ごと除去。
バックエンド拡張  
apps/api/docs/migrations/003_create_mobile_profiles.sql を追加し、mobile_profiles テーブルを作成 (device_id PK, user_id, profile jsonb, language)。
apps/api/src/routes/auth/apple.js ＋ services/auth/appleService.js を追加し、Identity Token検証とユーザーupsertを実装。
apps/api/src/routes/mobile/profile.js ＋ services/mobile/profileService.js を新設し、GET/PUT /mobile/profile を提供。
apps/api/src/routes/mobile/realtime.js を修正し、user-id ヘッダー必須＋issueRealtimeClientSecret({ deviceId, userId }) を呼ぶ。
Completion計算ロジックとテスト  
AppState か専用ヘルパに「次に到来するハビット」を返す関数を追加し、Completion画面と検証用ログで使用。シミュレータ検証で Wake/Training 両方が正しく案内されることを確認。
ドキュメント整備  
docs/Login.md を更新し、ログイン→フォローアップ→Completion の流れを追記。docs/ios-personalization.md を作成して体験ストーリーとプロンプト仕様、Completionメッセージのロジックを記載。
実装TODO
auth-routing: AppState/AuthCoordinator/ContentView を整備しサインイン状態を制御
habit-followups: ハビットカード内で寝場所・Trainingフォーカスを取得し保存
profile-sync: UserProfile 永続化と /mobile/profile 同期を実装
prompt-render: プロンプトとビルダーを寝場所/フォーカス挿入に対応
backend-auth: Apple認証APIと mobile_profiles テーブルを追加
backend-profile: /mobile/profile エンドポイントとRealtime userId必須化を実装
docs-ux: Completionカード含むUXフローと検証手順をドキュメント化