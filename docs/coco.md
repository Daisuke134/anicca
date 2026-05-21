## Anicca iOS 実装ロードマップ

### 即時着手タスク（リアルタイム双方向対話）
1. `ios/Config/Environment.swift` を新規作成し、エフェメラルキー発行エンドポイント（POST `/realtime/session`）のベースURLやタイムアウト、アプリ識別子を定数として定義する。秘密情報は保持しない。
2. `ios/Services/RealtimeSessionService.swift` を実装し、`URLSession` で `/realtime/session` を呼び出して `client_secret.value` を取得する。401/500 などのエラーを明示的に返却し、呼び出し側が再試行できるようにする。
3. `ios/Services/RealtimeConversationManager.swift` を `@MainActor` `ObservableObject` として実装し、`import RealtimeAPI` の `Conversation` を内包する。`connect(ephemeralKey:)`、`disconnect()`、`toggleMute()`、`send(text:)` を公開し、`status`・`messages`・`isUserSpeaking`・`isModelSpeaking` を `@Published` で提供する。
4. `ios/ViewModels/VoiceSessionViewModel.swift` を作成し、上記サービスを注入する。`start()` でマイク権限確認→エフェメラルキー取得→`ConversationManager.connect()`、`stop()` で切断、`send(text:)` でテキスト送信を行い、UI 用の接続状態・エラー表示を管理する。
5. `ios/Views/VoiceSessionView.swift` を SwiftUI で構築する。接続ボタン、終了ボタン、ミュート切替、音声状態インジケータ、メッセージ一覧、テキスト送信欄を配置し、初回表示時にマイク権限を要求する。権限拒否時は設定アプリ誘導を表示する。
6. `ios/iosApp.swift` の `WindowGroup` を `VoiceSessionView()` に差し替え、起動直後にリアルタイム会話 UI が現れるようにする。必要に応じてアプリ起動時に `AVAudioSession` を `.playAndRecord` へ設定する。
7. 実機で `start()` を実行し、マイク入力→モデル音声出力が成立すること、ネットワーク不通時に UI が再接続を促すことを確認する。ログに session 状態遷移を記録する。

### 全体ロードマップ（Step 3–10）
3. `apps/api` にエフェメラルセッション発行エンドポイント（POST `/realtime/session`）を実装し、OpenAI API キーはサーバ側にのみ保持する。Railway staging にデプロイし、本文 JSON・レスポンス JSON をログ付きで検証する。
4. iOS の `RealtimeConversationService`（前項で構築）で、`Session` 初期値（`modalities`, `turn_detection`, `noise_reduction`, `maxResponseOutputTokens` など）を `docs/ios.md` の仕様に合わせて設定し、会話開始までの遅延を 500ms 以内に抑える。
5. オンボーディングフローを SwiftUI で実装し、権限取得→起床セット→ボイス選択→呼び出し導線→試走→トライアル開始までを段階化する。ボイス録音データは暗号化してサーバ送信後にローカル削除し、`voice_id` を安全に保存する。
6. 起床シーケンス用に Critical Alert 通知と前夜プリロード音源を組み合わせ、通知タップから 500ms 以内に会話が前面化する Foreground シーンを構築する。洗面→呼吸→瞑想→宣言のスクリプトに沿って会話を制御する。
7. 日中ナッジ向けに Screen Time API などのシグナル設計をまとめ、Time-Sensitive 通知→アプリ前面化→短時間介入（呼吸 3 回→視線移動→再開宣言）を実装する。介入結果は KPI 収集用に保存する。
8. データ保存レイヤーを App Group Keychain＋暗号化ファイルストレージで構築し、音声データは AES で暗号化、起床ログやナッジ履歴は Core Data/SQLite に格納して KPI 集計に利用する。
9. Passkey＋Sign in with Apple の認証と StoreKit 2 サブスクリプションを実装し、レシート検証は `apps/api` に集約する。iOS 側は Combine で購読状態を監視し、失効時は自動的に介入を停止する。
10. XCTest・UITest で起床シナリオ／日中ナッジ／課金導線／オフライン復帰を自動化し、TestFlight で実機検証→App Store 提出→バッテリー追加消費 3%/日以内を監視してリリースする。
