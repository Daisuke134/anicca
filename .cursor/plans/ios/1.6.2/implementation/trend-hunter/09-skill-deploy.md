## スキルファイル構成

> OpenClaw調査結果（2026-02-08）: スキルは **SKILL.md のみで動作可能**。
> エージェントがSKILL.mdの指示に従い、内蔵ツール（exec, slack, memory等）で実行する。
> `index.js` / `_meta.json` はカスタムツール実装時のみ必要（今回は不要）。

### ディレクトリ構造

```
/home/anicca/.openclaw/skills/trend-hunter/
└── SKILL.md          ← これだけ。エージェントがexec等で全てを実行する
```

**なぜ `~/.openclaw/skills/` か**: 全エージェント共有。ワークスペース専用より汎用性が高い。

### SKILL.md の構成（YAML Frontmatter + 本文）

```yaml
---
name: trend-hunter
description: 13 ProblemType のバイラルコンテンツをマルチソースから検出し、hook候補を生成する
homepage: https://github.com/Daisuke134/anicca.ai
metadata:
  openclaw:
    emoji: "🔍"
    requires:
      env:
        - TWITTERAPI_KEY
        - REDDAPI_API_KEY
        - APIFY_API_TOKEN
        - ANICCA_AGENT_TOKEN
    primaryEnv: TWITTERAPI_KEY
---

# trend-hunter

（本文: 実行指示、クエリ辞書、処理フロー、エラーハンドリング等）
（この設計書の「1. SKILL.md（改訂案）」〜「Step 4」の内容をここに記載）
```

### 環境変数の渡し方

| 方法 | 設定場所 | スコープ |
|------|---------|---------|
| **VPS `.env`** + systemd EnvironmentFile | `/home/anicca/.env` | プロセス全体（推奨） |
| `openclaw.json` の `skills.entries.trend-hunter.env` | `~/.openclaw/openclaw.json` | ホスト実行のみ |

**採用**: VPS `.env` 方式。既に `APIFY_API_TOKEN`, `ANICCA_AGENT_TOKEN` がこの方式で動作中。

> **P1 #5 解消: 優先順位**: VPS `.env`（systemd EnvironmentFile）が `openclaw.json` の skill env より優先される。
> 理由: systemd はプロセス起動時に `.env` を環境変数として注入 → `process.env` に設定済み。
> `openclaw.json` の skill env はホスト実行時（`openclaw skill run`）のみ適用され、VPS Gateway では無視される。
> **結論**: VPS では `.env` のみ管理すればよい。`openclaw.json` にスキル固有の env を設定する必要はない。

### スキルの自動リロード

| 設定 | デフォルト値 | 意味 |
|------|------------|------|
| `skills.load.watch` | `true` | SKILL.md変更を監視して自動リロード |
| `skills.load.watchDebounceMs` | `250` | 変更検出後250msでリロード |

**Gateway再起動は不要**。SKILL.md を編集・コピーすれば250ms後に自動反映。

### デプロイ手順

| # | ステップ | コマンド | 備考 |
|---|---------|---------|------|
| 1 | ディレクトリ作成 | `ssh anicca@46.225.70.241 "mkdir -p ~/.openclaw/skills/trend-hunter"` | 初回のみ |
| 2 | SKILL.md アップロード | `scp SKILL.md anicca@46.225.70.241:~/.openclaw/skills/trend-hunter/` | 変更時も同じ |
| 3 | 環境変数追加 | ユーザーGUI作業（上記「ユーザー事前作業」参照） | `TWITTERAPI_KEY`, `REDDAPI_API_KEY` |
| 4 | 動作確認 | `ssh anicca@46.225.70.241 "openclaw doctor"` | Skills loaded セクションで確認 |
| 5 | Cronジョブ追加 | `jobs.json` に trend-hunter エントリ追加 | Gateway再起動が必要 |
| 6 | Cron手動テスト | `openclaw agent --message "trend-hunterスキルを実行してください" --deliver` | Slack #trends で結果確認 |

### テスト手順

| # | テスト種別 | 方法 | 確認項目 |
|---|-----------|------|---------|
| 1 | **ロード確認** | `openclaw doctor` | trend-hunter が Skills loaded に表示 |
| 2 | **依存確認** | `openclaw doctor` | TWITTERAPI_KEY 等の警告なし |
| 3 | **単体実行** | `openclaw agent --message "..."` | 各APIへのcurl成功、Slack投稿成功 |
| 4 | **Cronテスト** | ジョブ追加後、次の4時間サイクルを待つ or 手動実行 | 自動実行 + Slack通知 |
| 5 | **障害テスト** | 一時的にTWITTERAPI_KEYを無効化して実行 | フォールバック動作確認 |

---

