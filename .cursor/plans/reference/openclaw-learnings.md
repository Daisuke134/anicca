# OpenClaw 学び（2026-02-05）

## 1. Slack 投稿の正しい方法

### 間違い（私がやったこと）

```bash
# exec ツールで bash コマンドを実行 ← 間違い
/opt/homebrew/bin/openclaw message send --channel slack --target "channel:C091G3PKHL2" --message "..."
```

### 正しい方法

```json
// slack ツールを JSON で呼び出す ← 正しい
{
  "action": "sendMessage",
  "to": "channel:C091G3PKHL2",
  "content": "メッセージ内容"
}
```

**根拠**: `/opt/homebrew/lib/node_modules/openclaw/skills/slack/SKILL.md` を参照

---

## 2. skill-creator スキルを使え

**手動で SKILL.md を書くな。`skill-creator` スキルに頼め。**

```
openclaw skills list
→ skill-creator (✓ ready)
```

スキルを作成・更新するときは:
1. Anicca に「skill-creator スキルを使って daily-metrics-reporter を修正して」と頼む
2. または `openclaw agent --message "skill-creator で..."`

---

## 3. OpenClaw スキルの仕組み

### スキル読み込み順序（優先度順）

| 優先度 | 場所 | 説明 |
|--------|------|------|
| 1 | `~/.openclaw/workspace/skills/` | ワークスペース（最優先） |
| 2 | `~/.openclaw/skills/` | ローカル |
| 3 | `/opt/homebrew/lib/node_modules/openclaw/skills/` | バンドル版 |

### SKILL.md の正しい構造

```yaml
---
name: skill-name
description: 説明
metadata: { "openclaw": { "emoji": "📊", "requires": { "config": ["channels.slack"], "env": ["API_KEY"] } } }
---

# スキル名

## Instructions

ここに指示を書く
```

**重要**: metadata は **単一行の JSON** でなければならない

---

## 4. ツールの使い分け

| やりたいこと | 使うツール | 形式 |
|-------------|-----------|------|
| Slack 投稿 | `slack` | JSON |
| ファイル読み込み | `read` | パス |
| ファイル書き込み | `write` | パス + 内容 |
| bash コマンド | `exec` | コマンド文字列 |
| GitHub 操作 | `github` (または exec + gh) | - |

**exec で代用できるが、専用ツールがあれば専用ツールを使う**

---

## 5. Anicca エージェントの利用可能ツール

`~/.openclaw/openclaw.json` の `agents.list[0].tools.allow`:

```json
["read", "write", "exec", "slack"]
```

---

## 6. cron ジョブの設定

### 一覧

```bash
openclaw cron list
```

### 追加（ワンショット）

```bash
openclaw cron add \
  --name "test" \
  --at "2026-02-05T22:00:00Z" \
  --session isolated \
  --wake now \
  --delete-after-run \
  --message "指示内容" \
  --deliver \
  --channel slack \
  --to "C091G3PKHL2"
```

### 追加（定期）

```bash
openclaw cron add \
  --name "daily-report" \
  --cron "0 9 * * *" \
  --tz "Asia/Tokyo" \
  --session isolated \
  --message "指示内容"
```

### 編集

```bash
openclaw cron edit <job-id> --message "新しい指示"
```

### 即時実行（デバッグ）

```bash
openclaw cron run <job-id>
```

---

## 7. Gateway 再起動

```bash
launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway
```

---

## 8. スキル一覧確認

```bash
openclaw skills list
```

---

## 9. 重要な参照先

| 項目 | パス/URL |
|------|---------|
| OpenClaw 設定 | `~/.openclaw/openclaw.json` |
| バンドルスキル | `/opt/homebrew/lib/node_modules/openclaw/skills/` |
| cron ジョブ | `~/.openclaw/cron/jobs.json` |
| cron ログ | `~/.openclaw/cron/runs/` |
| Gateway ログ | `~/Library/Logs/openclaw/` |
| 公式ドキュメント | https://docs.openclaw.ai/ |
| ClawHub（スキル検索） | https://clawhub.ai/ |

---

## 10. 今回の失敗から学んだこと

| 失敗 | 学び |
|------|------|
| SKILL.md を手動で書いた | `skill-creator` スキルを使え |
| exec + bash でSlack投稿 | `slack` ツール + JSON を使え |
| ドキュメントを読まなかった | まず https://docs.openclaw.ai/tools/skills を読め |
| 既存スキルを参考にしなかった | `/opt/homebrew/lib/node_modules/openclaw/skills/slack/SKILL.md` を参考にしろ |

---

## 11. 次回からの手順

1. **まずドキュメントを読む**: https://docs.openclaw.ai/
2. **既存スキルを参考にする**: `openclaw skills list` → 該当スキルの SKILL.md を読む
3. **skill-creator を使う**: 手動で書くな
4. **専用ツールを使う**: exec で代用するな
5. **テストする前に構造を確認**: Gateway ログを見る

---

最終更新: 2026-02-05 22:00 JST
