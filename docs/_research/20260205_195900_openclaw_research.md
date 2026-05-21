# OpenClaw ベストプラクティス調査結果

## 調査メタデータ

| 項目 | 値 |
|------|-----|
| **調査日時** | 2026-02-05 19:59:00 |
| **調査対象** | OpenClaw (旧Clawdbot/Moltbot) |
| **調査バージョン** | 2026年2月時点の最新版 |
| **主要情報源** | 公式ドキュメント (docs.openclaw.ai)、セキュリティ専門家記事、コミュニティベストプラクティス |

---

## 1. Session Management（セッション管理）

### 1.1 dmScope（ダイレクトメッセージスコープ）

| 設定値 | 推奨環境 | 理由 | 出典 |
|--------|---------|------|------|
| `per-channel-peer` | **複数ユーザー環境（推奨）** | 送信者ごとにDMを完全分離。共有インボックスでのメッセージ混在を防止 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |
| `main` | 単一ユーザー環境 | 全DMが同一セッションで継続。会話コンテキストを最大限保持 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |
| `per-channel` | 中間（非推奨） | チャネルごとに分離するが、送信者混在リスクあり | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |

**推奨設定:**
```json
{
  "session": {
    "dmScope": "per-channel-peer"
  }
}
```

### 1.2 session.reset（セッションリセット戦略）

| 戦略 | 設定方法 | 用途 | 出典 |
|------|---------|------|------|
| **Daily Reset（デフォルト）** | `reset: { type: "daily", at: "04:00" }` | 毎朝4時にメモリリセット。日次タスクボットに最適 | [Session Management Deep Dive](https://docs.openclaw.ai/reference/session-management-compaction) |
| **Idle Expiry** | `reset: { type: "idle", minutes: 60 }` | 非アクティブ60分でリセット。チャットボットに最適 | [Session Management Deep Dive](https://docs.openclaw.ai/reference/session-management-compaction) |
| **Hybrid（推奨）** | `resetByType`で`dm`, `group`, `thread`ごとに異なるポリシー | グループは長め、DMは短めなど柔軟に設定 | [Session Management Deep Dive](https://docs.openclaw.ai/reference/session-management-compaction) |

**推奨設定（コスト最適化）:**
```json
{
  "session": {
    "reset": {
      "type": "idle",
      "minutes": 60
    },
    "resetByType": {
      "dm": { "type": "idle", "minutes": 120 },
      "group": { "type": "daily", "at": "04:00" },
      "thread": { "type": "idle", "minutes": 30 }
    }
  }
}
```

### 1.3 トークン節約のベストプラクティス

| 手法 | 設定 | 効果 | 出典 |
|------|------|------|------|
| **Compaction Settings調整** | `reserveTokens: 16384`, `keepRecentTokens: 20000` | コンテキストとコストのバランス最適化 | [Session Management Deep Dive](https://docs.openclaw.ai/reference/session-management-compaction) |
| **Cache TTL最適化** | `cacheControlTtl: "1h"` (Anthropic), `cache-ttl` pruning有効化 | キャッシュ再利用率向上、トークン消費60-80%削減 | [Session Pruning](https://docs.openclaw.ai/concepts/session-pruning) |
| **Session Pruning活用** | `tools.allow/deny`で不要なツール結果を除外 | `cacheWrite`サイズ削減 | [Session Pruning](https://docs.openclaw.ai/concepts/session-pruning) |
| **短めのIdle設定** | `idle: 30-60分` | 不要なコンテキスト蓄積を防止 | [コミュニティベストプラクティス](https://help.apiyi.com/en/openclaw-token-cost-optimization-guide-en.html) |

**コスト削減実績:**
- Federico Viticciの事例: 月180M tokens（$3,600）→ 最適化後60-80%削減可能
- 典型的な削減率: 60-80%（適切なセッション管理 + キャッシュ活用）

---

## 2. Agent Configuration（エージェント設定）

### 2.1 maxConcurrent（同時実行数）

| 設定 | 推奨値 | 理由 | 出典 |
|------|--------|------|------|
| `agents.defaults.maxConcurrent` | **1（デフォルト・推奨）** | 各セッションを順序化。予測可能な動作とデバッグ容易性 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |
| `agents.defaults.maxConcurrent` | 2-3（高スループット時のみ） | 高負荷環境でのみ増加。ただし、エラー率上昇とデバッグ困難化のリスク | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |

### 2.2 subagents.maxConcurrent

| 設定 | 推奨値 | 理由 | 出典 |
|------|--------|------|------|
| `subagents.maxConcurrent` | **3-5（推奨）** | サブエージェント並列実行の最適値。5以上は効果逓減 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |
| `subagents.maxConcurrent` | 1-2（低リソース環境） | メモリ/CPU制約がある場合 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |

### 2.3 モデル選択（2026年2月時点）

| 用途 | 推奨モデル | 価格 (M tokens) | 理由 | 出典 |
|------|-----------|----------------|------|------|
| **日常アシスタント作業（推奨）** | `anthropic/claude-sonnet-4` | $3/$15 | Opus 4.5の90%の能力を20%のコストで。コスパ最強 | [Best Models for OpenClaw 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot) |
| **高度な推論・コード生成** | `anthropic/claude-opus-4.5` | $15/$75 | ツール呼び出し精度最高。ミッションクリティカルなタスク向け | [Best Models for OpenClaw 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot) |
| **コスト重視（フォールバック）** | `openai/gpt-5-mini` | $0.50/$1.50 | 簡単なタスクに最適。50倍安い | [Best Models for OpenClaw 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot) |
| **コスト重視（フォールバック）** | `openrouter/deepseek/deepseek-r1:free` | 無料 | 軽量タスク・実験用 | [公式ドキュメント](https://docs.openclaw.ai/gateway/configuration) |
| **プライバシー重視** | セルフホスト（Ollama等） | ハードウェアコスト | 完全ローカル実行。医療・金融データ向け | [Best Models for OpenClaw 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot) |

**推奨設定（プライマリ + フォールバック）:**
```json
{
  "agents": {
    "defaults": {
      "models": [
        "anthropic/claude-sonnet-4",
        "openai/gpt-5-mini",
        "openrouter/deepseek/deepseek-r1:free"
      ]
    }
  }
}
```

**選定基準（OpenClawにおいて重要な3要素）:**
1. **Tool Calling精度** - シェルコマンド/API呼び出しの構文エラー率
2. **Context Tracking** - 50メッセージ前の内容を記憶できるか
3. **Code Quality** - 生成コードが実行可能か

---

## 3. Slack Integration（Slack統合）

### 3.1 requireMention（メンション要件）

| 設定 | 推奨値 | 理由 | 出典 |
|------|--------|------|------|
| `channels.slack.channels[].requireMention` | **true（強く推奨）** | 誤応答防止。チャネルでの不要な反応をフィルタリング | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |
| `channels.slack.channels[].requireMention` | false | DMのみで使用する場合のみ許容 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |

### 3.2 groupPolicy（グループポリシー）

| 設定 | 推奨値 | 理由 | 出典 |
|------|--------|------|------|
| `channels.slack.groupPolicy` | **`allowlist`（強く推奨）** | 明示的許可チャネルのみ動作。セキュリティリスク最小化 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |
| `channels.slack.groupPolicy` | `open` | デフォルトだが危険。全チャネルで動作 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |

### 3.3 historyLimit（履歴コンテキスト制限）

| 設定 | 推奨値 | 理由 | 出典 |
|------|--------|------|------|
| `channels.slack.historyLimit` | **20-30件（推奨）** | コストと関連性のバランス最適 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |
| `channels.slack.historyLimit` | 50件（デフォルト） | コスト高。高関連性が必要な場合のみ | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |
| `channels.slack.historyLimit` | 0 | 完全無効化。リアルタイム応答のみ | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |

### 3.4 Socket Mode vs HTTP Webhook

| モード | 推奨環境 | メリット | デメリット | 出典 |
|--------|---------|---------|-----------|------|
| **Socket Mode（推奨）** | ローカル/VPS環境 | HTTPSエンドポイント不要。ファイアウォール内部から動作可能 | WebSocketオーバーヘッド | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |
| **HTTP Webhook** | HTTPS公開サーバー | レイテンシ低い。スケーラブル | HTTPS証明書必須。外部アクセス必須 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |

**推奨設定:**
```json
{
  "channels": {
    "slack": {
      "groupPolicy": "allowlist",
      "historyLimit": 25,
      "channels": [
        {
          "id": "#allowed-channel",
          "requireMention": true
        }
      ]
    }
  }
}
```

---

## 4. Plugin/Skill Management（プラグイン/スキル管理）

### 4.1 Bundled Skills vs Workspace Skills

| タイプ | 保存場所 | 用途 | 管理方法 | 出典 |
|--------|---------|------|---------|------|
| **Bundled Skills** | OpenClawパッケージ内 | 公式スキル（`github`, `gog`, `weather`等） | 自動更新。削除非推奨 | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **Workspace Skills** | `~/clawd/skills/<<skill-name>>/SKILL.md` | カスタムスキル、コミュニティスキル | ユーザー管理。ClawHub経由でインストール | [OpenClaw Skills](https://openclaw-ai.online/skills/) |

### 4.2 スキルの有効化/無効化

| コマンド | 説明 | 用途 | 出典 |
|---------|------|------|------|
| `openclaw skills list` | インストール済みスキル一覧表示 | 現在のスキル確認 | [OpenClaw Skills](https://openclaw-ai.online/skills/) |
| `clawhub install <skill-name>` | ClawHubからスキルインストール | 700+コミュニティスキルから選択 | [OpenClaw Skills](https://openclaw-ai.online/skills/) |
| スキルフォルダ削除 | `rm -rf ~/clawd/skills/<skill-name>` | 不要なスキル削除 | [OpenClaw Skills](https://openclaw-ai.online/skills/) |

### 4.3 推奨スキルセット（用途別）

| 用途 | 推奨スキル | インストール数 | 出典 |
|------|-----------|---------------|------|
| **開発者** | `github` (171), `coding-agent` (164), `skill-creator` (247) | 580+ | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **生産性** | `gog` (342), `summarize` (150), `weather` (153) | 645+ | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **ソーシャルメディア** | `bird` (139 - X/Twitter CLI) | 139+ | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **画像生成** | `nano-banana-pro` (Gemini 3 Pro Image) | - | [Skills.sh](https://skills.sh/openclaw/openclaw) |

### 4.4 スキル間の依存関係管理

| 推奨事項 | 理由 | 出典 |
|---------|------|------|
| **`skill-creator`を最初にインストール** | 新規スキル作成ガイド。他スキルのテンプレートとして機能 | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **`clawhub`をインストール** | ClawHubからのスキル検索・インストール・バージョン管理に必須 | [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **依存関係をSKILL.mdに明記** | スキル説明ファイルに前提スキルをリスト化 | [OpenClaw Skills](https://openclaw-ai.online/skills/) |

---

## 5. Security（セキュリティ）

### 5.1 APIキーの安全な管理方法

| 手法 | 実装方法 | セキュリティレベル | 出典 |
|------|---------|-------------------|------|
| **環境変数（推奨）** | `.env`ファイル + `.gitignore`追加 | 中 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |
| **Composio Vault（最強）** | OAuth + Backend Injection | 最高 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| **ファイルシステムパーミッション** | `chmod 600 ~/.openclaw/agents/*/auth-profiles.json` | 中 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |
| **Secrets Manager（エンタープライズ）** | AWS Secrets Manager / HashiCorp Vault | 最高 | [AIエージェント時代のセキュリティ](https://ai.reinforz.co.jp/2525) |

**禁止事項:**
| NG行為 | リスク | 出典 |
|--------|--------|------|
| APIキーをコードにハードコード | GitHub流出で即悪用 | [OpenAI API Safety](https://help.openai.com/ja-jp/articles/5112595-best-practices-for-api-key-safety) |
| `.env`をGitコミット | 公開リポジトリで即流出 | [GitGuardian BP](https://constella-sec.jp/blog/cyber-security/secrets-api-management/) |
| 同一キーを複数人で共有 | 責任所在不明。不正使用追跡不可 | [OpenAI API Safety](https://help.openai.com/ja-jp/articles/5112595-best-practices-for-api-key-safety) |

**推奨ファイルパーミッション:**
```bash
chmod 700 ~/.openclaw
chmod 600 ~/.openclaw/agents/*/auth-profiles.json
chmod 600 ~/.openclaw/credentials/oauth.json  # レガシー
```

### 5.2 OAuth認証のベストプラクティス

| 推奨事項 | 実装方法 | 理由 | 出典 |
|---------|---------|------|------|
| **Composio統合（最強）** | OAuth認証をComposio経由で実行 | エージェントが生の認証情報を見ない。窃取不可能 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| **トークンローテーション** | 1. 新トークン生成 → 2. Gateway再起動 → 3. 旧トークンで接続不可確認 | 漏洩時の影響最小化 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |
| **スコープ最小化** | 読み取り専用スコープのみ許可（例: `userTokenReadOnly: true`） | 破壊的操作を防止 | [Slack公式ドキュメント](https://docs.openclaw.ai/channels/slack) |

**Composio統合の利点:**
1. **ゼロ・トラスト・アーキテクチャ** - エージェントは参照IDのみ保持
2. **Backend Injection** - API呼び出し時にComposioが認証情報を注入
3. **即座取り消し** - ダッシュボードのキルスイッチで即座にアクセス終了

### 5.3 ログに機密情報を出さない方法

| 設定 | 推奨値 | 効果 | 出典 |
|------|--------|------|------|
| `logging.redactSensitive` | **`"tools"`（デフォルト・推奨）** | ツールサマリー難読化。トークン/URL保護 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |
| `logging.redactPatterns` | カスタム正規表現リスト | 内部URL、ホスト名、カスタムトークン除外 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |
| セッショントランスクリプト削除 | 定期的に`~/.openclaw/agents/*/sessions/*.jsonl`をクリーンアップ | 古いセッションに含まれる機密情報削除 | [OpenClaw Security](https://docs.openclaw.ai/gateway/security) |

**推奨設定:**
```json
{
  "logging": {
    "redactSensitive": "tools",
    "redactPatterns": [
      "sk-[A-Za-z0-9]{48}",
      "Bearer [A-Za-z0-9_-]+",
      "https://internal\\.company\\.com/.*"
    ]
  }
}
```

**診断情報共有時:**
```bash
# 難読化済みステータス出力（安全）
openclaw status --all

# 生ログ共有は禁止（機密情報含む）
# cat ~/.openclaw/gateway/gateway.log  # NG
```

### 5.4 Docker Hardening（コンテナ強化）

| 設定 | 効果 | 理由 | 出典 |
|------|------|------|------|
| `--read-only` | ルートファイルシステム読み取り専用化 | 永続化攻撃を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| `--security-opt=no-new-privileges` | 権限昇格防止 | setuidバイナリ経由の攻撃を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| `--cap-drop=ALL` | 全Linuxケイパビリティ削除 | システム改変を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| `-u 1000:1000` | 非rootユーザー実行 | root権限での攻撃を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| `--cpus`, `--memory` | リソース制限 | DoS攻撃を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |

**推奨Dockerコマンド:**
```bash
docker run -d \
  --name openclaw \
  --read-only \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  -u 1000:1000 \
  --cpus=2 \
  --memory=4g \
  -v openclaw-data:/home/openclaw/.openclaw \
  -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
  openclaw/openclaw:latest
```

### 5.5 ネットワーク制限

| 手法 | 実装方法 | 効果 | 出典 |
|------|---------|------|------|
| **Egress Filtering（出力フィルタリング）** | 許可リストプロキシ経由で`api.openai.com`, `api.anthropic.com`のみ許可 | データ流出試行を防止 | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup) |
| **ファイアウォールルール** | iptables/nftablesで不要な外部接続をブロック | 攻撃面縮小 | [セキュリティベストプラクティス](https://design.dev/guides/openclaw-security/) |

---

## 6. 現在の設定との差分（openclaw.json）

**注意:** プロジェクト内に`openclaw.json`ファイルが見つかりませんでした。以下は、ゼロから構築する場合の推奨最小構成です。

### 推奨最小構成（セキュア + コスト最適化）

```json
{
  "agents": {
    "defaults": {
      "models": [
        "anthropic/claude-sonnet-4",
        "openai/gpt-5-mini"
      ],
      "maxConcurrent": 1
    }
  },
  "session": {
    "dmScope": "per-channel-peer",
    "reset": {
      "type": "idle",
      "minutes": 60
    },
    "resetByType": {
      "dm": { "type": "idle", "minutes": 120 },
      "group": { "type": "daily", "at": "04:00" }
    }
  },
  "channels": {
    "slack": {
      "groupPolicy": "allowlist",
      "historyLimit": 25,
      "channels": [
        {
          "id": "#your-allowed-channel",
          "requireMention": true
        }
      ]
    }
  },
  "logging": {
    "redactSensitive": "tools",
    "redactPatterns": [
      "sk-[A-Za-z0-9]{48}",
      "Bearer [A-Za-z0-9_-]+"
    ]
  }
}
```

---

## 7. セキュリティチェックリスト（導入前必須）

| # | 項目 | ステータス | 優先度 |
|---|------|-----------|--------|
| 1 | APIキーを環境変数に保存（`.env` + `.gitignore`） | ☐ | 🔴 必須 |
| 2 | `~/.openclaw/`のパーミッションを`700`に設定 | ☐ | 🔴 必須 |
| 3 | `auth-profiles.json`のパーミッションを`600`に設定 | ☐ | 🔴 必須 |
| 4 | `logging.redactSensitive: "tools"`を有効化 | ☐ | 🔴 必須 |
| 5 | Slack `groupPolicy: "allowlist"`を設定 | ☐ | 🔴 必須 |
| 6 | Slack `requireMention: true`を設定 | ☐ | 🔴 必須 |
| 7 | Docker `--read-only`フラグを使用 | ☐ | 🟡 推奨 |
| 8 | Docker `--security-opt=no-new-privileges`を使用 | ☐ | 🟡 推奨 |
| 9 | Composio統合でOAuth認証を実装 | ☐ | 🟡 推奨 |
| 10 | 定期的なセッショントランスクリプトクリーンアップ | ☐ | 🟢 任意 |

---

## 8. コスト最適化サマリー

| 施策 | 削減率 | 実装難易度 | 優先度 |
|------|--------|-----------|--------|
| **Session Idle Reset（60分）** | 30-40% | 低 | 🔴 最優先 |
| **Cache TTL最適化** | 40-50% | 低 | 🔴 最優先 |
| **モデルフォールバック（Sonnet→Mini）** | 20-30% | 低 | 🔴 最優先 |
| **historyLimit削減（50→25）** | 10-15% | 低 | 🟡 推奨 |
| **Session Pruning設定** | 5-10% | 中 | 🟢 任意 |

**総合削減見込み:** 60-80%（全施策実施時）

---

## 9. 参考リンク

| カテゴリ | リンク |
|---------|--------|
| **公式ドキュメント** | [Configuration](https://docs.openclaw.ai/gateway/configuration), [Session Management](https://docs.openclaw.ai/reference/session-management-compaction), [Security](https://docs.openclaw.ai/gateway/security), [Slack Integration](https://docs.openclaw.ai/channels/slack) |
| **セキュリティ** | [Composio Security Guide](https://composio.dev/blog/secure-openclaw-moltbot-clawdbot-setup), [JFrog Security Analysis](https://jfrog.com/blog/giving-openclaw-the-keys-to-your-kingdom-read-this-first/), [Design.dev Security](https://design.dev/guides/openclaw-security/) |
| **モデル選定** | [Best Models for OpenClaw 2026](https://haimaker.ai/blog/posts/best-models-for-clawdbot), [AI Models for Coding 2026](https://www.faros.ai/blog/best-ai-model-for-coding-2026) |
| **コスト最適化** | [Token Cost Optimization](https://help.apiyi.com/en/openclaw-token-cost-optimization-guide-en.html) |
| **スキル管理** | [OpenClaw Skills](https://openclaw-ai.online/skills/), [Skills.sh](https://skills.sh/openclaw/openclaw) |
| **日本語ガイド** | [OpenClaw完全入門（note）](https://note.com/enushi817/n/n715fecd99ad9), [AIエージェント時代のセキュリティ](https://ai.reinforz.co.jp/2525) |

---

## 10. 次のアクションアイテム

| # | アクション | 期限 | 担当 |
|---|-----------|------|------|
| 1 | 推奨最小構成をベースに`openclaw.json`を作成 | 即時 | 開発者 |
| 2 | 環境変数でAPIキーを設定（`.env` + `.gitignore`） | 即時 | 開発者 |
| 3 | Slack `groupPolicy: "allowlist"`を適用 | 即時 | 開発者 |
| 4 | セッションリセット戦略をテスト（Idle 60分） | 1週間 | 開発者 |
| 5 | トークン消費量をモニタリング（目標: 30%削減） | 1ヶ月 | 開発者 |
| 6 | Composio統合を検討（エンタープライズ導入時） | 3ヶ月 | チーム |

---

**調査完了日時:** 2026-02-05 19:59:00
**調査担当:** Claude Sonnet 4.5
**次回レビュー推奨日:** 2026-05-05（四半期ごと）
