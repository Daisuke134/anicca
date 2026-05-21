# Anicca iOS 実装TODO v1.0（Codex向け・音声ファースト）

最終更新日: 2025-10-31（Asia/Tokyo）
対象読者: 実装担当（Codex/エンジニアリング）、QA、デザイン、運用
前提文書: 「Anicca iOS 実装仕様 v1.0（Codex向け・完全版）」

---

## 0. 目的

音声だけで迷わず実装・起動・検証まで到達できるよう、実作業の順序と受け入れ基準を明文化する。UIは必要最小限（認証・権限・支払い・トラブル復旧のみ）。

---

## 1. クリティカルパス（時系列）

1. [x] リポジトリ初期化と依存導入
2. [x] オーディオ基盤（AVAudioSession + AVAudioEngine）
3. [ ] LiveKit接続と再接続制御
4. 通知基盤（Time‑Sensitive、後でCritical Alert）
5. BGTaskによる前夜プリロード
6. オンボーディング（UI入力＋音声ガイド）
7. 音声パイプライン拡張（Realtime/Deepgram/ElevenLabs）
8. データ保存（Core Data + CloudKit）
9. 決済導入（RevenueCat + StoreKit2）
10. 観測性とイベント計測
11. E2E自動テストと手動QA
12. TestFlight 提出と審査ドキュメント整備

---

## 2. 音声ファースト方針とUI最小化

2.1 音声で完結すべき操作

1. 起床、ナッジ、瞑想誘導、日次内省の開始と完了報告
2. ボイス切替、音量と話速、介入強度の変更
3. 失敗時の再試行指示（例: 「もう一度やり直して」）

2.2 画面が必要な最小領域

1. 初回認証（Passkey + Sign in with Apple）
2. 権限リクエストと結果表示（マイク、通知、背景オーディオ）
3. 決済ペイウォール（RevenueCat）
4. トラブル復旧画面（接続不可、権限未許可、課金切れ）

2.3 音声コマンド設計（例）

1. モード変更: 「アニッチャ、標準ボイス」「アニッチャ、クローンに切り替え」
2. 介入制御: 「もう少し静かに」「話速を少し上げて」「今日は短めで」
3. エラー回復: 「接続をやり直して」「オフラインで続けて」

---

## 3. 実装TODO（順番と受け入れ基準付き）

### 3.1 リポジトリ初期化（IOS‑001）

目標: `aniccaios/` に既存Xcodeプロジェクトを配置し、SPM依存を固定タグで導入する。
手順:

1. `aniccaios/aniccaios/aniccaios.xcodeproj` をベースに構成
2. Package Dependencies: RevenueCat（必要に応じて追加）
3. ターゲット設定: iOS 17最小、Signingは開発チームを設定
4. Info.plist 自動生成とバンドルID `com.anicca.ios`
   受け入れ基準:
5. クリーンビルド成功
6. 依存の解決とアーカイブ可能

### 3.2 オーディオ基盤（IOS‑002）

目標: 低遅延でAEC/NS/AGCが有効な入力を確立。
手順:

1. `AudioSessionConfigurator.swift` を作り category=playAndRecord, mode=voiceChat を設定
2. AVAudioEngineで入力ノードのVoiceProcessingを有効化
3. マイク権限取得ダイアログの音声ガイド
   受け入れ基準:
4. 16k/48kサンプルでの安定収音
5. 音声のラウンドトリップ遅延ログ出力

### 3.3 LiveKit接続（IOS‑003）

目標: エフェメラルトークンでRoomに接続、音声Publish/Subscribeし、切断時は自動再接続。
手順:

1. `Features/Voice/RealtimeSession.swift` 実装
2. `Services/API/MobileAPIClient.swift` に `/rtc/ephemeral-token` 呼び出し
3. 回線断検知→指数的バックオフで再接続
   受け入れ基準:
4. 接続から3秒以内に下り音声を再生
5. 切断後30秒以内に自動復帰

### 3.4 通知基盤（IOS‑004）

目標: Time‑Sensitive通知で前面化し、タップで即時LiveKit接続。
手順:

1. `Services/Notifications/NotificationCenter.swift` 実装
2. 起床用音源 `wake.caf` をバンドル
3. 通知タップでアプリがForegroundになり `RealtimeSession.join()` を即実行
   受け入れ基準:
4. 通知→3秒以内に会話開始
5. サイレント中でもTime‑Sensitiveが表示

### 3.5 BGTask前夜プリロード（IOS‑005）

目標: 就寝前に起床音源と初期プロンプトをプリロード。
手順:

1. タスクID `com.anicca.preload` 登録
2. サーバから台本受領→音源生成→`SoundAssets` に保存
   受け入れ基準:
3. スケジュール時刻の±1分で確実に通知発火
4. 失敗時にリトライし、ログに残す

### 3.6 オンボーディング（IOS‑007）

目標: フォーム入力と音声ガイドを組み合わせ、ユーザーが数分で起床設定まで完了できる導線を提供する。
手順:

1. `Features/Onboarding/OnboardingFlow.swift` を新設し、SwiftUI でステップ型フォームを構築（名前、起床時刻、休日設定、優先習慣、連絡先など）。
2. 権限取得（マイク / 通知 / 背景オーディオ）をフォーム途中で案内し、許可状態は音声でフィードバック。拒否時は UI で再設定導線を表示。
3. 入力確定後、`CoreData`（または暫定のローカルモデル）に保存し、`RealtimeSession` へ引き渡す初期コンテキストを生成。
4. 起床テストモードを用意し、ユーザーが「起床シミュレーションを再生」ボタンから事前確認できるようにする（ローカル音声の再生のみ）。
5. フォーム完了時に「日中の呼び出し」「オンデマンド呼び出し」のためのショートカット（Siri / Widget）案内を表示。
   受け入れ基準:
6. 入力必須項目が全て揃った状態で保存され、アプリ再起動後も参照できる。
7. 権限が拒否された場合でもユーザーに再設定手順を即提示し、フォーム離脱ゼロを目指す。

### 3.7 音声パイプライン拡張（IOS‑006）

目標: Phase 1 では OpenAI Realtime 音声を直結し、Phase 2 で Deepgram STT／ElevenLabs TTS に切り替え可能なプラガブル構成を整える。
手順:

1. `VoicePipeline` プロトコルを定義（`start`, `stop`, `switchTTS`, `switchSTT`）。
2. Phase 1：`RealtimeVoicePipeline`（Realtime API のストリーミングを使用）を実装し、`RealtimeSession` と `VoiceEngine` の間に挿入。レスポンス開始が2秒以内であることを保証。
3. Phase 2：`DeepgramElevenLabsPipeline` を実装し、STT/TTS を差し替え可能にする。切り替えは `VoiceMode` スイッチだけで即時反映。
4. オフライン時は `AVSpeechSynthesizer` によるフォールバック処理を組み込み、ネットワーク断でも指示が継続するようにする。
   受け入れ基準:
5. どのパイプラインでも対話開始から最初のレスポンスまで 2 秒以内。
6. パイプライン切替後もセッションを維持し、ユーザーへの音声が途切れない。

### 3.8 データ保存（IOS‑008）

目標: Core Data + CloudKit で UserProfile, Routine, Reflection, VoiceProfile, Interaction を保存。
手順:

1. `Services/Storage/CoreDataStack.swift` とモデル定義
2. CRUDユースケースと自動マイグレーション
   受け入れ基準:
3. iCloud有効時に2台で同期
4. PIIを含む音声実体は暗号化済みで保存

### 3.9 決済（IOS‑009）

目標: 無料期間から自動更新に移行、失敗時のリトライ。
手順:

1. RevenueCat導入、OfferingとEntitlementを作成
2. ペイウォール表示と復元動線
   受け入れ基準:
3. 無料→有料の自動切替
4. 解約時の機能制限が即時反映

### 3.10 観測性（IOS‑010）

目標: OSLogとイベント計測の埋め込み。
手順:

1. `Logger.swift` でカテゴリ（Audio, RTC, Notify, Pipeline, Billing）
2. `Analytics.swift` でイベント `wake_triggered`, `wake_joined`, `nudge_done` など
   受け入れ基準:
3. 主要フローにイベントが発火
4. PIIを含まないこと

### 3.11 E2E/QA（IOS‑011）

目標: 起床→会話→瞑想→終了、通知拒否、回線断復帰の自動化。
手順:

1. XCUITestでモック通知→接続→台本完走
2. ネットワークリンクコンディショナで遅延・損失
   受け入れ基準:
3. 80%以上の成功率
4. 致命的クラッシュゼロ

### 3.12 提出準備（IOS‑012）

目標: TestFlightビルドと審査資料。
手順:

1. プライバシーマニフェスト、権限文言
2. Critical Alert申請文書（用途、影響、代替策）
   受け入れ基準:
3. TestFlight配布開始
4. 審査提出に必要なメタ情報が揃う

---

## 4. 音声のみ運用での仕様変更点

1. 常時のタブやボタンを廃止し、全操作は「呼びかけ→返答」で進行
2. 画面は状態表示と復旧のためだけに存在（例: 接続不可、権限未許可、支払いエラー）
3. 長押しやスワイプに依存しない。視覚的インジケータは音声で説明
4. 設定値の変更も音声で受け付け、後から確認の読み上げを行う

---

## 5. チケット化バックログ（割当用）

IOS‑001 リポジトリ初期化とSPM依存
IOS‑002 AudioSessionとAVAudioEngine構成
IOS‑003 LiveKit接続と自動再接続
IOS‑004 通知基盤(Time‑Sensitive)と前面化ハンドオフ
IOS‑005 BGTask前夜プリロード
IOS‑006 音声パイプライン(Realtime/Deepgram/ElevenLabs)
IOS‑007 オンボーディング音声誘導
IOS‑008 Core Data + CloudKit モデル
IOS‑009 RevenueCat課金
IOS‑010 観測性とイベント
IOS‑011 E2E自動テスト
IOS‑012 TestFlight提出と審査資料

---

## 6. インターフェースひな形

6.1 VoicePipeline

```swift
protocol VoicePipeline {
    func start(context: VoiceContext) async throws
    func stop() async
    func switchTTS(_ mode: TTSMode) async
    func switchSTT(_ mode: STTMode) async
}
```

6.2 RealtimeSession

```swift
protocol RealtimeSession {
    func join(token: String, url: String) async throws
    func leave() async
    var onDownlinkAudio: ((AudioFrame) -> Void)? { get set }
    var onStateChanged: ((ConnectionState) -> Void)? { get set }
}
```

---

## 7. 受け入れテストの台本

1. 起床フロー: 通知→前面化→「OK」→洗面→呼吸→終了宣言
2. ナッジ: アプリ滞在検知→通知→30秒介入→再開宣言
3. クローンボイス: 録音→生成→プレビュー→本番再生
4. オフライン: 回線断→ローカル台本→復帰同期

---

## 8. 運用とロールバック

1. フィーチャーフラグでRealtimeとDeepgram/ElevenLabsを切替
2. 重大障害時はオフライン台本モードで最低限を提供

---

## 9. 提出チェックリスト

1. 権限文言の整合とプライバシーポリシーURL
2. Time‑Sensitive 運用の根拠説明
3. Critical Alertのエンタイトルメント申請文書
4. スクリーンショットと動画（音声誘導の説明字幕付き）

以上。上から順に着手すれば、音声のみ運用に適したMVPが完成する。各タスクは単独でマージ可能な粒度に分割してあるため、Codexは順次PRを作成し検証できる。
