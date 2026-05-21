# OpenClaw 技術仕様リファレンス

> ソース: https://github.com/openclaw/openclaw (v2026.2.6-3)
> ドキュメント: https://docs.openclaw.ai
> 最終更新: 2026-02-07

---

## 1. アーキテクチャ全体像

```
WhatsApp / Telegram / Slack / Discord / Signal / iMessage / ...
               │
               ▼
┌───────────────────────────────┐
│            Gateway            │
│       (WS control plane)      │
│     ws://127.0.0.1:18789      │
└──────────────┬────────────────┘
               │
               ├─ Pi agent (RPC) ← エージェントランタイム
               ├─ CLI (openclaw …)
               ├─ WebChat UI
               ├─ macOS app
               └─ iOS / Android nodes
```

| コンポーネント | 場所 | 役割 |
|--------------|------|------|
| Gateway Server | `src/gateway/` | WebSocket制御プレーン。セッション、チャンネル、ツール、イベントを管理 |
| Pi Agent Runtime | `src/agents/` | エージェント実行。ツール実行、ストリーミング |
| Channels | `src/channels/`, `src/slack/`, `src/telegram/` 等 | マルチチャンネル抽象化 |
| Cron | `src/cron/` | スケジュール実行 |
| Memory | `src/memory/` | ベクトル検索 + FTS |
| CLI | `src/cli/`, `src/commands/` | コマンドラインインターフェース |
| Skills | `skills/` | エージェントスキル定義 |
| Extensions | `extensions/` | チャンネルプラグイン |

**技術スタック:**

| 項目 | 技術 |
|------|------|
| 言語 | TypeScript (ESM) |
| ランタイム | Node.js 22+ |
| パッケージ | pnpm |
| テスト | Vitest (70%カバレッジ閾値) |
| Lint | Oxlint + Oxfmt |
| DB | SQLite + sqlite-vec (ベクトル検索) |
| ビルド | tsdown |

---

## 2. Gateway アーキテクチャ

### 接続フロー

```
Client → Connect (ConnectParams + device signature)
→ Server: connect.challenge (nonce)
→ Client: resend Connect with signed nonce
→ Server: HelloOk (auth token, policy)
→ Bidirectional: req/resp frames (RPC), evt frames (broadcasts)
```

### プロトコル（AJV検証済み）

| フレームタイプ | 構造 |
|--------------|------|
| Request | `{ type: "req", id: uuid, method: string, params?: {} }` |
| Response | `{ type: "resp", id: uuid, ok: boolean, payload?: {}, error?: {} }` |
| Event | `{ type: "evt", seq: number, event: string, payload?: {} }` |

### 主要RPC メソッド

| カテゴリ | メソッド |
|---------|---------|
| Agent | `agent.*`, `agents.list`, `agents.files.*`, `agent.wait` |
| Session | `sessions.list`, `sessions.resolve`, `sessions.patch`, `sessions.compact`, `sessions.reset` |
| Chat | `chat.send`, `chat.history`, `chat.abort`, `chat.inject` |
| Cron | `cron.list`, `cron.add`, `cron.update`, `cron.remove`, `cron.run`, `cron.runs` |
| Config | `config.get`, `config.set`, `config.apply`, `config.patch`, `config.schema` |
| Channels | `channels.status`, `channels.logout` |
| Nodes | `node.list`, `node.describe`, `node.invoke`, `node.pair.*` |
| Skills | `skills.status`, `skills.install`, `skills.update`, `skills.bins` |
| Exec | `exec.approvals.get`, `exec.approvals.set`, `exec.approval.request` |
| Logs | `logs.tail` |
| Models | `models.list` |

### セッションモデル

| 項目 | 詳細 |
|------|------|
| Tick間隔 | 30秒（デフォルト） |
| 最大ペイロード | 25MB |
| スタック検出 | Tick timeout = 60秒 |
| 再接続 | 指数バックオフ（1s → 30s） |

---

## 3. エージェントランタイム

### ターンの実行フロー

```
1. Chat.send(message) → セッションにキューイング
2. runEmbeddedPiAgent() →
   - モデル/プロファイル選択（auth + cost aware）
   - システムプロンプト + ツール準備
   - ストリーミング: チャンクごとにコールバック
3. ツール呼び出し → Pi ランタイムがバッチ実行
4. ツール結果 → エージェントにストリーム返却
5. 最終テキスト → セッション transcript に保存
```

### 利用可能ツール

| ツール | 機能 |
|--------|------|
| `exec` | シェルコマンド実行（PTY対応、バックグラウンドジョブ、承認ゲート） |
| `fs` | ファイル操作（read, write, list, delete, watch） |
| `browser` | Puppeteer自動化（DOMスナップショット、スクリーンショット、PDF） |
| `image` | 画像生成（DALL-E）、分析（Claude Vision）、変換 |
| `memory` | ベクトル検索 + キーワード、引用追跡 |
| `message` | チャンネルへメッセージ送信（DM、スレッド、添付ファイル） |
| `cron` | ジョブ作成/管理/状態確認 |
| `sessions` | セッション管理（リスト、リセット、compaction） |
| `nodes` | リモートノード操作（P2P） |
| `gateway` | Gateway RPCメソッド呼び出し |
| `slack` | Slack API操作 |
| `discord` | Discord API操作 |
| `web_search` | Web検索（Brave Search API） |

### ツール権限

| 設定 | 効果 |
|------|------|
| `tools.alsoAllow` | ツール追加許可リスト |
| `tools.deny` | ツール拒否リスト |
| プロファイル制限 | `exec`, `fs`, `browser` はデフォルトOFF（制限プロファイル） |
| 承認ゲート | 危険な操作は承認が必要 |

---

## 4. Cron システム

### ジョブ種別

| 項目 | 詳細 |
|------|------|
| `systemEvent` | メインセッションにイベント送信（エージェント起動なし） |
| `agentTurn` | 隔離セッションでエージェント実行（メッセージ + ツール使用可能） |

### スケジュール種別

| タイプ | 説明 |
|--------|------|
| `at` | 一回限り（指定日時） |
| `every` | インターバル実行 |
| `cron` | Cron式（タイムゾーン対応） |

### 実行フロー

```
CronService (in-process)
→ Timer fires at nextRunAtMs
→ systemEvent の場合: メインセッションにイベント発行
→ agentTurn の場合: 隔離エージェント起動 → 実行 → 結果配信
→ Delivery (isolated only): mode="none" (サイレント) or "announce" (チャンネルに投稿)
→ State: nextRunAtMs, runningAtMs, lastStatus, lastError
```

### 重要ルール

| ルール | 詳細 |
|--------|------|
| `main` ジョブ | `kind="systemEvent"` 必須 |
| `isolated` ジョブ | `kind="agentTurn"` 必須 |
| `delivery` | `isolated` ジョブのみ対応 |
| スタック検出 | 2時間後に自動クリア（STUCK_RUN_MS） |
| `delivery.mode` | `"none"` または `"announce"` のみ（`"silent"` は無効） |

### Cron ジョブ データ構造

```typescript
{
  id: uuid,
  name: string,
  schedule: { kind: "at|every|cron", ... },
  sessionTarget: "main" | "isolated",
  payload: { kind: "systemEvent|agentTurn", ... },
  delivery?: { mode: "none|announce", channel, ... },
  state: { nextRunAtMs, runningAtMs, lastStatus, ... }
}
```

---

## 5. チャンネルシステム

### 対応チャンネル

| チャンネル | タイプ | 機能 |
|-----------|--------|------|
| Slack | DM, Group, Thread | コマンド、リアクション、ファイルアップロード |
| Telegram | DM, Group, Channel, Thread | コマンド、投票、メディア |
| Discord | DM, Guild, Thread | コマンド、ロール、モデレーション |
| WhatsApp | DM, Group | 投票、リアクション、メディア |
| Signal | DM, Group | テキスト、メディア |
| iMessage | DM, Group | テキスト、メディア |
| Google Chat | DM, Space | テキスト、メディア |
| Web | カスタム | ブラウザベース |
| MS Teams | Extension | テキスト、メディア |
| Matrix | Extension | テキスト、メディア |

### Channel Dock システム

| 機能 | 説明 |
|------|------|
| Capabilities | `chatTypes`, `nativeCommands`, `blockStreaming`, `media`, `polls`, `reactions` |
| Adapters | `groups`(メンション), `mentions`(テキスト除去), `threading`, `agentPrompt` |
| Output limits | プラットフォームごとのチャンクサイズ（例: Telegram 4000文字） |

### メッセージルーティング

```
受信メッセージ(channel)
→ ルーティング層: セッションターゲット決定 (main/isolated/channel固有)
→ allowFrom: 送信者IDフィルタ
→ コマンド: "/" で始まる特殊メッセージ
→ グループメンション: @bot ルール
→ スレッディング: コンテキストリプライ
```

---

## 6. スキルシステム

### 配置場所と優先順位

| 優先度 | 場所 | 説明 |
|--------|------|------|
| 最高 | `<workspace>/skills/` | エージェント固有 |
| 中 | `~/.openclaw/skills/` | managed/local（全エージェント共有） |
| 低 | バンドル（npm内 `skills/`） | 公式同梱 |
| 最低 | `skills.load.extraDirs` | 追加スキルフォルダ |

### SKILL.md フォーマット

```yaml
---
name: nano-banana-pro
description: Generate or edit images via Gemini 3 Pro Image
homepage: https://pypi.org/project/nano-pdf/
user-invocable: true
metadata: {"openclaw": {"emoji": "📄", "requires": {"bins": ["uv"], "env": ["GEMINI_API_KEY"]}, "primaryEnv": "GEMINI_API_KEY", "install": [...]}}
---
# スキル名
使い方の説明...
```

### ゲーティング（ロード時フィルタ）

| フィールド | 効果 |
|-----------|------|
| `requires.bins` | PATHに存在必須 |
| `requires.anyBins` | いずれか1つ存在必須 |
| `requires.env` | 環境変数が必要 |
| `requires.config` | `openclaw.json` のパスが truthy |
| `os` | OS制限（`darwin`, `linux`, `win32`） |
| `always: true` | 常に有効（ゲートスキップ） |

### トークン影響

```
合計文字数 = 195 + Σ (97 + len(name) + len(description) + len(location))
≈ 24トークン/スキル + フィールド長
```

### スキル設定（`openclaw.json`）

```json
{
  "skills": {
    "allowBundled": ["slack", "github", "weather"],
    "load": {
      "extraDirs": ["~/Projects/skills"],
      "watch": true,
      "watchDebounceMs": 250
    },
    "install": {
      "preferBrew": true,
      "nodeManager": "npm"
    },
    "entries": {
      "nano-banana-pro": {
        "enabled": true,
        "apiKey": "YOUR_KEY",
        "env": { "GEMINI_API_KEY": "YOUR_KEY" }
      },
      "sag": { "enabled": false }
    }
  }
}
```

### セキュリティノート

| ルール | 詳細 |
|--------|------|
| サードパーティスキルは untrusted code | 有効化前に中身を必ず読む |
| Sandbox推奨 | Docker sandboxで実行 |
| env/apiKey はホスト側のみ注入 | サンドボックスには渡されない |
| `allowBundled` が最強の防御 | ホワイトリスト方式でバンドルスキルを制限 |

---

## 7. バンドルスキル一覧（全52個）

### 安全 & 有用（VPS向けおすすめ）

| スキル | 説明 | APIキー |
|--------|------|---------|
| `weather` | 天気取得 | 不要 |
| `github` | gh CLI操作 | 不要 |
| `slack` | Slackリアクション・ピン操作 | 不要（チャンネル設定済み前提） |
| `healthcheck` | ホストセキュリティ監査 | 不要 |
| `session-logs` | セッションログ検索・分析 | 不要 |
| `summarize` | URL/動画/音声の要約・文字起こし | 不要 |
| `skill-creator` | スキル作成支援 | 不要 |
| `clawhub` | ClawHubレジストリ操作 | 不要 |
| `discord` | Discord操作 | 不要（チャンネル設定済み前提） |
| `nano-pdf` | PDF編集 | 不要 |
| `blogwatcher` | RSS/ブログ監視 | 不要 |

### APIキー必要だが有用

| スキル | 必要なキー | 説明 |
|--------|-----------|------|
| `nano-banana-pro` | `GEMINI_API_KEY` | Gemini 3画像生成/編集 |
| `gemini` | Gemini CLI auth | Q&A、要約 |
| `openai-image-gen` | `OPENAI_API_KEY` | 画像バッチ生成 |
| `openai-whisper-api` | `OPENAI_API_KEY` | 音声文字起こし |
| `sag` | ElevenLabs API | テキスト読み上げ |
| `goplaces` | Google Places API | 場所検索 |

### macOS 限定（VPSでは動かない）

| スキル | 説明 |
|--------|------|
| `apple-notes` | Apple Notes操作 |
| `apple-reminders` | Reminders操作 |
| `peekaboo` | macOS UI自動化 |
| `things-mac` | Things 3タスク管理 |
| `bear-notes` | Bear Notes操作 |
| `imsg` | iMessage/SMS |
| `canvas` | Canvas表示 |
| `blucli` | BluOS操作 |
| `sonoscli` | Sonos操作 |

### 要注意（リスクあり）

| スキル | リスク | 理由 |
|--------|--------|------|
| `coding-agent` | 中 | Codex/Claude Codeを子プロセス実行。権限エスカレーション |
| `tmux` | 中 | キーストローク送信。意図しないコマンド実行 |
| `1password` | 高 | パスワードマネージャーアクセス |
| `wacli` | 中 | WhatsApp送信。誤送信リスク |
| `food-order` | 中 | 食事注文。実際に注文走る |
| `gog` | 高 | Gmail/Calendar/Drive/Sheets全アクセス |
| `notion` | 中 | Notion API操作。誤削除 |
| `ordercli` | 中 | Foodora注文履歴 |

### ユーティリティ系

| スキル | 説明 |
|--------|------|
| `video-frames` | ffmpegでフレーム抽出 |
| `gifgrep` | GIF検索 |
| `songsee` | 音声スペクトログラム |
| `openai-whisper` | ローカル音声認識（APIキー不要） |
| `sherpa-onnx-tts` | ローカルTTS（オフライン） |
| `model-usage` | モデル使用量確認 |
| `oracle` | oracle CLI操作 |
| `himalaya` | メール管理（IMAP/SMTP） |
| `camsnap` | RTSP/ONVIFカメラ |

---

## 8. スラッシュコマンド

### コマンド vs ディレクティブ

| 概念 | 説明 |
|------|------|
| Commands | `/` で始まるスタンドアロンメッセージ。Gatewayが直接処理 |
| Directives | `/think`, `/model` 等。メッセージ内にインラインでも使える。モデルには見えない |
| user-invocable skills | `user-invocable: true` のスキルがスラッシュコマンドとして登録 |

### 主要コマンド一覧

| コマンド | 機能 |
|---------|------|
| `/help` | ヘルプ表示 |
| `/commands` | コマンド一覧 |
| `/skill <name> [input]` | スキル実行 |
| `/status` | ステータス（モデル使用量含む） |
| `/model <name>` | モデル切り替え |
| `/model list` | モデル一覧 |
| `/think <level>` | 思考レベル（off/minimal/low/medium/high/xhigh） |
| `/reset` / `/new [model]` | セッションリセット |
| `/stop` | 実行中タスク停止 |
| `/compact [instructions]` | コンテキスト圧縮 |
| `/context [list\|detail\|json]` | コンテキスト詳細（スキルごとのトークン消費量） |
| `/exec` | exec ツール設定確認・変更 |
| `/bash <cmd>` | ホストシェルコマンド（要 `commands.bash: true`） |
| `/config show\|get\|set\|unset` | 設定変更（要 `commands.config: true`） |
| `/debug show\|set\|unset\|reset` | ランタイムオーバーライド（要 `commands.debug: true`） |
| `/usage off\|tokens\|full\|cost` | 使用量フッター制御 |
| `/verbose on\|full\|off` | デバッグ詳細表示 |
| `/reasoning on\|off\|stream` | 推論表示 |
| `/elevated on\|off\|ask\|full` | 権限昇格モード |
| `/allowlist` | 許可リスト管理 |
| `/approve <id> allow-once\|allow-always\|deny` | exec承認 |
| `/subagents list\|stop\|log\|info\|send` | サブエージェント管理 |
| `/send on\|off\|inherit` | メッセージ送信制御 |
| `/queue <mode>` | キュー設定 |
| `/tts off\|always\|inbound\|tagged\|...` | TTS制御 |

### コマンド設定（`openclaw.json`）

```json
{
  "commands": {
    "native": "auto",
    "nativeSkills": "auto",
    "text": true,
    "bash": false,
    "bashForegroundMs": 2000,
    "config": false,
    "debug": false,
    "restart": false,
    "useAccessGroups": true
  }
}
```

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `native` | `"auto"` | ネイティブコマンド登録（Discord/Telegram=on, Slack=off） |
| `nativeSkills` | `"auto"` | スキルコマンドのネイティブ登録 |
| `text` | `true` | `/...` テキストコマンド解析 |
| `bash` | `false` | `! <cmd>` でホストシェル実行（危険） |
| `config` | `false` | `/config` による設定書き込み |
| `debug` | `false` | `/debug` によるランタイムオーバーライド |
| `useAccessGroups` | `true` | コマンドのアクセスリスト適用 |

---

## 9. メモリシステム

| コンポーネント | 役割 |
|--------------|------|
| MemoryIndexManager | ベクトル + FTS インデックス管理（SQLite + sqlite-vec） |
| Embedding Providers | OpenAI, Gemini, Voyage（バッチ + キャッシュ） |
| Chunk Storage | Markdownチャンキング（デフォルト512トークン + オーバーラップ） |
| Hybrid Search | BM25キーワード + ベクトル類似度のマージ |
| File Watching | エージェントメモリファイル自動同期（`.md`, `.txt`, `.pdf`） |

### 検索モード

| モード | アルゴリズム |
|--------|------------|
| `keyword` | FTS5ランキング |
| `vector` | Embedding + コサイン類似度 |
| `hybrid` | BM25 + vector の重み付きマージ |

---

## 10. Config システム（`openclaw.json`）

### 主要構造

```json
{
  "assistant": { "id": "...", "name": "...", "personality": "..." },
  "auth": {
    "profiles": {
      "default": { "provider": "anthropic", "mode": "api_key" }
    },
    "order": { "anthropic": ["default"] }
  },
  "models": {
    "primary": "opus",
    "providers": [{ "id": "anthropic", "models": [...] }]
  },
  "agents": { "dirs": [...], "defaults": { "maxConcurrent": 3, "sandbox": "docker" } },
  "channels": { "slack": {...}, "telegram": {...}, "discord": {...} },
  "session": { "compaction": {...}, "pruning": {...} },
  "tools": { "exec": {...}, "fs": {...}, "browser": {...} },
  "memory": { "provider": "openai", "model": "text-embedding-3-large" },
  "skills": { "allowBundled": [...], "entries": {...} },
  "commands": { "bash": false, "config": false, "debug": false }
}
```

### モデルエイリアス

| エイリアス | 実体 |
|-----------|------|
| `opus` | `anthropic/claude-opus-4-6` |
| `sonnet` | `anthropic/claude-sonnet-4-5` |
| `gpt` | `openai/gpt-5.2` |
| `gpt-mini` | `openai/gpt-5-mini` |
| `gemini` | `google/gemini-3-pro-preview` |
| `gemini-flash` | `google/gemini-3-flash-preview` |

---

## 11. セキュリティ & 認証

| レイヤー | メカニズム |
|---------|----------|
| Device Auth | ED25519署名 + 公開鍵配布 |
| Token Storage | デバイス・ロールごとに `~/.openclaw/auth/` |
| Auth Profiles | 複数LLMプロバイダ、ローテーション可能 |
| Exec Approval | 危険コマンドは非同期承認キュー |
| Tool Gating | エージェントごとの allow/deny リスト |
| Channel AllowFrom | 送信者ID/番号フィルタリング |
| DM Policy | `pairing`（ペアリングコード）/ `open`（全許可） |
| Skills Gating | `allowBundled` ホワイトリスト + `requires.*` フィルタ |

---

## 12. 設計パターン

| パターン | 使用箇所 | 理由 |
|---------|---------|------|
| Immutability | Config, agent state, sessions | 安全性 + 再現性 |
| Schema Validation (AJV) | Gateway protocol, config | 型安全性 |
| Lazy Loading | Plugins, profiles, memory indexes | 起動パフォーマンス |
| Event-Driven | Gateway broadcasts, channel events | 疎結合 |
| Backoff & Reconnect | Gateway client (1s → 30s) | 耐障害性 |
| Heartbeat/Tick | 30秒ごとのping/pong | スタック検出 |
| Streaming | Pi runs, logs | メモリ効率 |
| Batch API | Embeddings, provider APIs | コスト + 速度最適化 |
| SQLite + Extensions | Memory/sessions | ハイブリッド検索 |

---

## 13. 起動シーケンス

```
entry.ts
├─ normalizeEnv() → NODE_OPTIONS, NO_COLOR 等
├─ parseCliProfileArgs() → --profile=name
├─ applyCliProfileEnv() → OPENCLAW_STATE_DIR, CONFIG_PATH
├─ import cli/run-main.js
│  ├─ Commander.js program setup
│  ├─ Config load + AJV validation
│  ├─ Initialize:
│  │  ├─ Gateway (WebSocket server)
│  │  ├─ Cron service (jobs.json → timers)
│  │  ├─ Memory manager (agent dirs scan → embeddings sync)
│  │  ├─ Plugin registry (channels load)
│  │  └─ Logging (structured logs)
│  └─ Execute command
```

---

## 14. Anicca VPS 推奨スキル構成

```json
{
  "skills": {
    "allowBundled": [
      "slack",
      "github",
      "weather",
      "healthcheck",
      "session-logs",
      "summarize",
      "skill-creator",
      "clawhub"
    ],
    "entries": {
      "slack": { "enabled": true },
      "github": { "enabled": true },
      "weather": { "enabled": true },
      "healthcheck": { "enabled": true },
      "session-logs": { "enabled": true },
      "summarize": { "enabled": true }
    }
  }
}
```

**`allowBundled` を必ず設定する。** 未設定だと全52スキルが有効化され、トークン消費膨大 + 不要な権限が開く。

---

## 15. 関連リファレンス

| ファイル | 内容 |
|---------|------|
| `openclaw-anicca.md` | Anicca OpenClaw 現在の状態・機能・スキル一覧 |
| `openclaw-learnings.md` | OpenClaw スキル作成ルール、失敗から学んだこと |
| `secrets.md` | VPS情報、APIキー |
| `infrastructure.md` | Cronジョブ構成、Railway運用 |
