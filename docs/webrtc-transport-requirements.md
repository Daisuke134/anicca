# Electron デスクトップ版 WebRTC 移行要件定義書

## 目的
OpenAI Realtime API が推奨する WebRTC トランスポートへ移行し、音声入出力、VAD、ノイズ制御をブラウザ環境に委譲して保守性と将来拡張性を高める。

## 前提条件
- アプリはトレイ常駐型であり、ユーザー向け UI は不要。隠し BrowserWindow を音声処理専用に継続利用する。
- 会話ロジック、MCP 連携、タスク制御は Electron main プロセス（`apps/desktop/src/agents/sessionManager.ts`）側で維持する。
- プロキシ (`apps/api`) から取得する `client_secret` を用いてユーザー単位のセッションを確立する。
- レンダラープロセスには API キーを渡さず、`client_secret` と `call_id` のみを IPC 経由で連携する。

## スコープ
1. WebRTC トランスポート導入と既存 WebSocket トランスポートの撤去。
2. Main ↔ Renderer 間 IPC／サイドバンド構成の刷新。
3. `call_id` ベースのサイドバンド WebSocket によるセッション制御の確立。
4. テストおよび運用フローの更新（ユニット／手動）。

## 非スコープ
- トレイ以外の新規 UI 追加。
- Proxy/API 側の課金ロジックや OAuth 実装変更。
- デプロイ／署名パイプラインの改修。

## アーキテクチャ概要

### レンダラープロセス（隠し BrowserWindow）
- 新規モジュール `apps/desktop/src/renderer/webrtcClient.ts` を追加し、`@openai/agents-realtime` の `OpenAIRealtimeWebRTC` でマイク取得・音声再生・VAD を担当する。
- `apps/desktop/src/preload.ts` に `window.electronAPI` を定義し、以下 API を提供する：
  - `getClientSecret(): Promise<{ value: string; expiresAt: number }>`
  - `notifyCallId(callId: string): void`
  - `setMode(mode: 'silent' | 'conversation', reason: string): Promise<void>`
  - `fetchStatus(): Promise<RendererStatus>`
- 初期化手順：
  1. `electronAPI.getClientSecret()` で `client_secret` を取得。
  2. `OpenAIRealtimeWebRTC.connect({ apiKey: client_secret })` を実行。
  3. 応答ヘッダーの `Location` から `call_id` を抽出し `electronAPI.notifyCallId(callId)` を送信。
  4. WebRTC から受け取るイベント（`audio_start` 等）を IPC 経由で main プロセスへ通知。
- 既存の手書き WebSocket／PCM16 音声処理スクリプトは完全に削除する。

### Main プロセス（`main-voice-simple.ts` ＋ `sessionManager.ts`）
- 隠し BrowserWindow 起動後、IPC ハンドラを登録する。
- `sessionManager.startBridge(port)` は維持しつつ、音声関連の WebSocket 処理を削除する。
- `sessionManager.getClientSecret(): Promise<ClientSecret>` を追加し、従来の `ensureConnected()` 内部ロジックを利用してプロキシから `client_secret` を取得する。
- IPC 実装：
  - `ipcMain.handle('realtime:get-client-secret', …)` で renderer へ `client_secret` を供給。
  - `ipcMain.on('realtime:call-id', …)` で `call_id` を受信し、`sessionManager.attachSideband(callId)` を実行。
- `sessionManager.attachSideband(callId)` は `OpenAIRealtimeWebSocket` を `wss://api.openai.com/v1/realtime?call_id=…` で接続し、`session.update`／`response.create` などを送受信する。
- `session.on('audio_start' | 'audio_stopped' | 'agent_end' …)` の結果を IPC で renderer へ中継し、ログ／状態管理を行う。

### サイドバンド WebSocket（`sessionManager.ts`）
- `connect(callId)` で `OpenAIRealtimeWebSocket` を初期化し、既存のイベントハンドラを再利用する。
- 音声バイナリのブロードキャスト処理は削除し、状態イベントとツール制御に役割を限定する。
- MCP 更新、wake スティッキー制御など Node 側ロジックは従来通り維持する。

## 実装タスク
1. **Renderer／Preload 基盤整備**
   - `preload.ts` に IPC ブリッジを追加し、既存のブラウザ内スクリプトを `webrtcClient.ts` に置き換える。
   - `createHiddenWindow()` のロード完了後に `initializeWebrtc()` を実行するよう変更する。
2. **Main ↔ Renderer IPC 実装**
   - `ipcMain.handle('realtime:get-client-secret', …)` と `ipcMain.on('realtime:call-id', …)` を実装。
   - `/sdk/status` などローカル HTTP 呼び出しを廃止し、IPC で置き換える。
3. **`sessionManager.ts` 改修**
   - `OpenAIRealtimeWebSocket` の生成を `attachSideband(callId)` に移行。
   - `connect(apiKey)` は `client_secret` 取得までに役割を縮小し、WebRTC 接続は renderer に委譲。
   - 音声バイナリ送受信ロジックを削除し、IPC 送信に切り替える。
4. **Proxy レスポンス拡張（必要時）**
   - Location ヘッダーから `call_id` が取得できない場合、`desktopSession` API を改修し JSON で `call_id` を返す。
5. **ローカル WebSocket ブリッジ整理**
   - `setupWebSocket()` の音声処理を削除し、タスク実行／状態通知のみを残す。
6. **ビルド整備**
   - `npm run voice:simple` で動作検証し、call_id 連携のログを確認する。

## テスト計画
- **自動テスト**
  - `attachSideband(callId)` の単体テストでイベント転送と IPC 通知を確認。
  - MCP ツール呼び出し時の `tool_execution_start/complete` イベントが renderer に届くことを検証。
- **手動テスト**
  1. アプリ起動で WebRTC 接続ログ（`call_id`）が出力されること。
  2. 会話モードで音声入力→応答→割込みが正しく機能すること。
  3. `wake_up` スティッキータスクが従来通り動作すること。
  4. オフライン復帰時に再初期化 IPC が正しく実行されること。
- **負荷／回帰テスト**
  - 5 分連続会話で音声の遅延や切断が無いこと。
  - MCP リフレッシュ（20 分周期）でセッションが破棄されないこと。

## 移行手順
1. ブランチ `feature/webrtc-transport` を作成。
2. 上記タスク順に実装し、コミット。
3. `npm run voice:simple` で手動検証。
4. ユニットテスト更新・実行。
5. PR 作成、レビュー、`main` へマージ。
6. 必要に応じてベータ配布 → ステージング検証 → 安定版リリース。

## 完了条件
- Renderer 側で `OpenAIRealtimeWebRTC` が稼働し、音声入出力が WebRTC に一本化されている。
- Main 側が `call_id` サイドバンド WebSocket を用いて制御し、MCP／タスク／モード制御が正常に機能している。
- 旧 WebSocket 音声処理コードが削除され、不要なローカル API が残っていない。
- 本要件で定義した自動・手動テストがすべて完了している。

## リスクと対策
- **call_id が取得できない**：Proxy 側で Location ヘッダーを露出し、JSON に `call_id` を含める。
- **Electron レンダラーの自動再生失敗**：`autoplayPolicy` 設定とマイク権限を確認し、失敗時は renderer から再初期化を要求する。
- **サイドバンド切断**：`transport.on('close')` で自動再接続を試み、失敗時は renderer に再初期化 IPC を送信する。

## 依存ライブラリ
- `@openai/agents-realtime` 最新版（WebRTC サポートを含む）。
- Electron 設定の変更が必要な場合は追加で調整する。

## ログ／監視
- WebRTC 接続成功時に `call_id` と `expires_at` をログ出力（PII を含めない）。
- サイドバンド接続状態を監視し、切断時には警告ログを記録する。
