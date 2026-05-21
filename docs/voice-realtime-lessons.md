# Anicca 音声接続アーキテクチャ — 学習メモ（2025-09-05）

## 目的と範囲
- 目的: 定刻（Cron）でも任意時（ユーザー発話）でも、安定して「Aniccaの声」で応答させるための設計知見を集約する。
- 範囲: OpenAI Agents SDK / Realtime API の前提、トークン/セッション/トランスポート、接続健全性、UXトリガ、電源管理、観測性。
- 非範囲: 具体的なコード変更・実装手順・パッチ。

## TL;DR（最重要の学び）
- エフェメラル client_secret は「クライアント直結で低遅延・安全」を両立するための標準。失効後は再利用不可。再接続は都度「新しい client_secret」で握り直す。
- 「ready になってから送る」送信ゲートが必須。connect 直後の早すぎる送信は落ちる。
- 接続の真偽は「物理層の実測」で判定（transport.open・lastServerEvent・TTLなど）。論理フラグ（session/apiKey の有無）ではダメ。
- 長寿命 1 本維持は非現実的（セッション上限・NAT/無線）。「必要時に短時間で確実に握る」ほうが堅牢。
- PC が完全スリープ中は発話不可。復帰後の遅延発話で取りこぼしを補うのが現実解。

## 用語
- エフェメラル client_secret: Proxy が本 API キーから発行する短命・単回の接続トークン（クライアント直結の認証に使用）。
- セッション: RealtimeSession とその下の物理接続（WebSocket または WebRTC）。
- healthy / stale（便宜定義）:
  - healthy: transport.open かつ lastServerEvent ≤ 10s、tokenTTL > 120s、sessionAge < 50 分
  - stale: 上記のいずれか不成立

## アーキテクチャ概観（テキスト図）
```
[User]──(音声/操作)──>[Hidden Window]──PCM16──>[Bridge(SessionManager)]
                                   |               |
                                   |               +──(client_secretで直結)──> OpenAI Realtime
                                   |               |
                                   +──WS──<──audio_output/イベント───+
[Proxy(Railway)]──本APIキー保持──/desktop-session（client_secret発行）
```

## エフェメラル client_secret の前提
- なぜ必要か: クライアント（Electron/ブラウザ）に本 API キーを配らず、直接 Realtime と双方向通信するための“短命・単回”トークン。
- ライフサイクル: 短命（TTL あり）・単回利用。切断/失効後に同じトークンで再接続は不可。
- 失敗モード:
  - 再利用 → 「Ephemeral token expired」
  - セッション上限到達 → 「session_expired」
- 学び: 「再接続＝新しい client_secret を必ず取得してから connect」が正道。トークン無効化ではなく“正しく更新”が解。

## 接続管理パターン（学んだベストプラクティス）
- 単一ゲート ensureConnected（全入口に適用）
  - 対象: ユーザー発話開始 / ボタン操作 / 定刻の直前（T−60〜90 秒）
  - 動作: healthy なら何もしない。stale なら「/desktop-session → 新 client_secret → connect → ready 待ち（100→200→400ms）」
- 送信ゲート（ready 待ち）
  - 指標: `session.created` 受信 or transport.open を ready とみなし、最初の sendMessage/音声送出は ready 後に行う。
- 実測ヘルスでの接続判定
  - `isConnected = transport.open && lastServerEvent ≤ 10s && tokenTTL > 120s`（例）
  - UI/API のステータスもこの値に一致させる（誤陽性防止）。
- セッションの先回りローテーション
  - セッション上限（例: 60 分）に対し 45〜50 分で静かに再接続（history 復元）→ 上限直撃を回避。
- 取りこぼし救済（遅延発話）
  - 切断/失効検知 → gate_reset（micPaused/isSpeaking/キュー初期化）→ 新トークン接続 → ready → 直近 N 分の未消化タスクを 1 回だけ実行。

## トランスポート選択（WebSocket / WebRTC / Twilio）
- WebSocket: Electron/Node 側で実装単純・デバッグ容易。ローカル経路なら遅延も小さい。今回の課題（鍵・ready・ヘルス）とは独立。
- WebRTC: ブラウザ直結や通話系で有利（ジッタ/エコー/NAT 越え）。ただし鍵・ready・ヘルスの前提は同一。
- Twilio 拡張: 電話/PSTN を Realtime に橋渡しするアダプタ。鍵の自動更新はしない（アプリ側で都度取得が前提）。

## UX トリガの学び（Cron / PTT / 将来 KWS）
- Cron（Anicca 起点）: T−60〜90 秒プレフライトで ready を保証 → 定刻に確実発話。
- PTT（ユーザー起点）: 押下開始で ensureConnected、離した瞬間に `commit + response.create` → 誤起動少・即復帰に強い。
- KWS（将来）: PTT より誤検出リスクがあるため、接続管理（鍵/ready/ヘルス）は引き続き必要。

## 電源管理の現実
- powerSaveBlocker: アプリ休止は抑止できるが、OS の“完全スリープ”は止められない。
- スリープ中の事実: CPU/ネットワーク停止 → 定刻ぴったりの発話不可。
- 学び: 「起床時刻付近の短時間は起きている」か「復帰後ただちに遅延発話でキャッチアップ」のどちらかで確実性を担保。

## 観測性（ログ/ステータス）
- 最低限のイベントタグ:
  - [TOKEN_ISSUED] / [CONNECT_OK] / [READY]
  - [SESSION_EXPIRED] / [TOKEN_EXPIRED] / [GATE_RESET]
  - [CRON_PREFLIGHT] / [TASK_SENT] / [TASK_CATCHUP]
- `/sdk/status` は物理層の実測接続に一致（論理フラグ禁止）。

## 代表シーケンス（例）
- Cron 正常系
```
T-90s: ensureConnected（healthy→スキップ / stale→新鍵→connect→READY）
T:     cron fire → TASK_SENT → 音声開始
```
- 日中の突然の発話
```
[PTT Down] → ensureConnected（sessionAge=55 分 → 新鍵→connect→READY）
[PTT Up]   → commit + response.create → 応答
```
- 切断中に定刻を跨いだ（遅延許容）
```
T:     sleep/断で未実行
T+Δ:  復帰検知 → GATE_RESET → 新鍵→connect→READY → 直近 N 分の未処理を 1 回だけ実行（遅延発話）
```

## リスク / 非目標
- ローカル TTS での代替は本ドキュメントの範囲外（“Anicca の声”前提）。ただしネット障害時は遅延発話で補う設計が現実的。
- 「エフェメラル無効化」は非推奨。セキュア直結の基本要件に反し、根本（上限/ready/ヘルス）解決にもならない。

## 参考（確認済みポイント）
- Agents SDK（packages/agents-realtime）:
  - エフェメラル前提（insecureApiKey は原則禁止）
  - `session.created` 等のイベントで ready を把握
  - トランスポートは状態を持つが、自動鍵更新/自動ローテはアプリ責務
- Realtime Agents（デモ）:
  - 毎回サーバでエフェメラルを発行 → `connect`
  - PTT / `response.create` の薄い実装。長寿命維持より「必要時に確実に握る」方針

## 実装イメージ（テキストダイアグラム）

### 1) アプリ起動〜常駐（初回接続の基本）
```
User           Desktop(Main)      SessionManager(Bridge)     Proxy        OpenAI Realtime
 |                   |                        |                |                 |
 |  起動              |-- startBridge -------->|                |                 |
 |                   |                        |                |                 |
 |                   |  (任意: 初回connect)   |-- GET /desktop-session -->         |
 |                   |                        |<-- client_secret(value,TTL) --     |
 |                   |                        |-- connect(Bearer client_secret) -->|
 |                   |                        |<------------ session.created ------|
 |                   |                        |                |                 |
```

### 2) Cron 事前プレフライト（T−75秒 標準）
```
Scheduler      SessionManager     Proxy                  OpenAI Realtime
   |                 |              |                           |
   |  T-75s          |-- ensureConnected(fresh-if-stale) ------>|
   |                 |              |-- /desktop-session ------>|
   |                 |              |<-- client_secret ---------|
   |                 |-- connect(newKey) ----------------------->|
   |                 |<-- session.created(=READY) --------------|
   |                 |                                          |
```

### 3) Cron 定刻発火〜発話
```
Scheduler      SessionManager(READY)       HiddenWindow(UI)
   |                 |                            |
   |   T=exact       |-- sendMessage("wake_up")-->|
   |                 |--(audio_output WS)-------> |  再生/半二重ゲート
   |                 |                            |
```

### 4) 任意発話（PTT/自動VADの“入口”で握る）
```
User         HiddenWindow         SessionManager        Proxy         OpenAI Realtime
 |   PTT↓/発話検知  |-- ensureConnected(fresh-if-stale) --->|            |
 |                  |                |-- /desktop-session ->|            |
 |                  |                |<-- client_secret ----|            |
 |                  |-- connect(newKey) -------------------------------> |
 |                  |<-- session.created(=READY) -----------------------|
 |   音声送出       |-- mic PCM16 ------------------------------------->|
 |   PTT↑/終端      |-- commit + response.create ---------------------->|
 |                  |<-- audio_output (WS) ---------------------------- |
```

### 5) 切断/期限到達 → 自動復帰 + 未消化タスクの遅延発話（最大3分）
```
OpenAI Realtime    SessionManager             Proxy
      |                   |                     |
      |-- close/expired ->|-- [GATE_RESET] ---->|
      |                   |-- /desktop-session ->|
      |                   |<-- client_secret ----|
      |                   |-- connect(newKey) -->|
      |                   |<-- session.created --|
      |                   |-- catch-up: scan last N=3min
      |                   |-- sendMessage(missed_tasks)
```

### 6) 健全性/表示判定（常時）
```
SessionManager
  - isConnected = (transport.open && lastServerEvent≤10s && tokenTTL>120s)
  - /sdk/status は上記に一致（論理フラグは禁止）
```
