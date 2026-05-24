---
name: to-agents-skill
description: "x402スキル量産工場。トレンドリサーチ→spec.md→承認→Claude Codeでビルド→公開。Use when: skill production, factory run, build new x402 skill, produce skill, discover next skill, measure skill performance."
metadata: {"openclaw":{"emoji":"🏭","os":["darwin","linux"]}}
---

# to-agents-skill（x402スキル量産工場）

## 概要

3つのモードで動作する:

| モード | トリガー | 動作 |
|--------|---------|------|
| `discover` | 毎日 10:00 JST（cron） | リサーチ→spec.md作成→Slackに要約投稿→承認待ち |
| `produce` | ✅ リアクションで自動トリガー | spec.md を読む→Claude Codeでビルド→デプロイ→公開→宣伝 |
| `measure` | 毎週月曜 10:00 JST（cron） | パフォーマンス計測→改善or廃止提案 |

## 保存先

| 種類 | パス |
|------|------|
| スペックファイル | `~/.openclaw/workspace/to-agents/specs/YYYY-MM-DD-<name>.md` |
| 学びの蓄積 | `~/.openclaw/workspace/to-agents/to-agents-learning.md` |
| メトリクス | `~/.openclaw/workspace/to-agents/metrics.json` |
| 生成スキル | `~/.openclaw/skills/<skill_name>/SKILL.md` |

## リポジトリ情報

| 項目 | 値 |
|------|-----|
| API リポジトリ | `https://github.com/Daisuke134/anicca`（Private） |
| API エンドポイント dir | `apps/api/src/routes/x402/` |
| Production URL | `https://anicca-proxy-production.up.railway.app` |

---

## MODE: discover（リサーチ→スペック作成）

**毎日 10:00 JST（cron: `0 1 * * *` UTC）**

### Step 1: リサーチ（MANDATORY）

以下のソースを調査して「AIエージェントが今何に困ってるか、何が売れるか」を特定する:

```
1. web_search — "AI agent API services trending 2026", "x402 most used services"
2. Moltbook — フィード取得、エージェントの悩み・要望を読む
3. ClawHub — clawhub search で既存スキルのギャップを探す
4. skills.sh — npx skills find で競合・トレンドを確認
5. x402 Bazaar — awal x402 bazaar search で既存サービスを確認
```

最低3つの異なるキーワードで、英語+日本語で検索する。

### Step 2: spec.md を書く

`~/.openclaw/workspace/to-agents/specs/YYYY-MM-DD-<name>.md` に保存:

```markdown
# <skill_name> — x402 スキルスペック

## なぜ作るのか（トレンドの証拠）
- ソース1: [タイトル](URL) — 「引用」
- ソース2: [タイトル](URL) — 「引用」
- ソース3: [タイトル](URL) — 「引用」

## 何を作るのか
- エンドポイント: /api/x402/<skill_name>
- 入力スキーマ: { ... }
- 出力スキーマ: { ... }
- 使用LLM: OpenAI gpt-4o-mini（最安）

## 誰に売るのか
- ターゲット: どんなエージェントが使うか
- ユースケース: 具体的にどう使うか

## 価格と根拠
- 価格: $X.XX USDC/リクエスト
- 根拠: [ソース](URL) — 「引用」
- 競合比較: 他にいくらで売ってるか

## 技術設計
- system prompt の概要
- バリデーション（zod スキーマ）
- SAFE-T 統合の有無
- Bazaar 登録

## 収益予測
- 想定コール数/日
- 月間収益予測
- コスト（LLM API費用）
```

### Step 3: Slack に報告メッセージ送信

Slack #metrics にこれからビルドするスキルの概要を投稿する（承認不要、報告のみ）:

```bash
SLACK_BOT_TOKEN=$(grep SLACK_BOT_TOKEN ~/.openclaw/.env | head -1 | cut -d= -f2-)

curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "{{profile.channels.reportChannel}}",
    "text": "🏭 to-agents-skill: <name> のビルドを開始します\n\n*スキル:* <name>\n*なぜ:* <トレンドの証拠1行>\n*何を:* <エンドポイントと機能1行>\n*誰に:* <ターゲット1行>\n*価格:* $X.XX USDC（根拠: <1行>）\n*スペック:* specs/YYYY-MM-DD-<name>.md"
  }'
```

### Step 4: すぐに produce に進む（承認待ちなし）

---

## MODE: produce（ビルド→デプロイ→公開）

**トリガー: discover 完了後に自動で続行（承認不要）**

### Step 1: spec.md を読む

最新の承認済みスペックを読み込む。

### Step 2: Claude Code でビルド

coding-agent スキルを使って Claude Code にビルドさせる:

```
sessions_spawn(
  task="spec.md の内容に従って x402 エンドポイントを実装してください。
        リポジトリ: $HOME/Downloads/anicca-project
        ブランチ: dev
        実装先: apps/api/src/routes/x402/<name>.js
        テスト: apps/api/src/routes/x402/__tests__/<name>.test.js
        既存パターン: apps/api/src/routes/x402/emotionDetector.js をコピーして改変
        完了したら git push origin dev",
  mode="run"
)
```

### Step 3: staging テスト

Railway staging が自動デプロイされたら:

```bash
npx awal@2.0.3 x402 details https://anicca-proxy-staging.up.railway.app/api/x402/<name>
npx awal@2.0.3 x402 pay https://anicca-proxy-staging.up.railway.app/api/x402/<name> \
  -X POST -d '<test payload>'
```

**200 OK でなければ即 halt。** #metrics にエラー報告して終了。

### Step 4: SKILL.md 生成 + ClawHub 公開

```bash
mkdir -p ~/.openclaw/skills/<name>
# SKILL.md を生成（クライアント向けドキュメント）
clawhub publish /Users/anicca/.openclaw/skills/<name> --no-input
```

### Step 5: Moltbook 宣伝

moltbook-interact スキルで宣伝投稿。

### Step 6: to-agents-learning.md に追記（append のみ）

```markdown
## Run: <name> (YYYY-MM-DD)
| Field | Value |
|-------|-------|
| skill_name | <name> |
| endpoint_url | https://anicca-proxy-production.up.railway.app/api/x402/<name> |
| spec_file | specs/YYYY-MM-DD-<name>.md |
| clawhub_id | <id> |
| moltbook_post_id | <post_id> |
| notes | <learnings> |
```

### Step 7: Slack 完了報告

```
✅ to-agents-skill produce 完了

スキル: <name>
エンドポイント: <url>
ClawHub: <id>
Moltbook: <post_id>
スペック: specs/YYYY-MM-DD-<name>.md
```

---

## MODE: measure（パフォーマンス計測）

**毎週月曜 10:00 JST（cron: `0 1 * * 1` UTC）**

### Step 1: 公開済みスキル列挙

to-agents-learning.md の全 `## Run:` エントリを収集。

### Step 2: 各スキルの計測

| 指標 | 方法 |
|------|------|
| エンドポイント稼働 | curl でステータスコード確認 |
| Moltbook エンゲージメント | API でupvotes/comments取得 |
| ClawHub ダウンロード | clawhub search でスコア確認 |

### Step 3: 判定 + Slack 報告

| 条件 | アクション |
|------|-----------|
| 正常稼働 + エンゲージメントあり | 📊 レポートのみ |
| 7日間コールなし | ⚠️ 改善提案 |
| 14日間コールなし | 🗑️ 廃止提案 |
| エンドポイント 404/500 | 🔴 CRITICAL アラート |

---

## エラーハンドリング

| エラー | 対応 |
|--------|------|
| awal 非200 | 即 halt。ClawHub publish 禁止。#metrics にエラー報告 |
| Claude Code ビルド失敗 | #metrics にエラー報告。手動修正待ち |
| clawhub publish 失敗 | 1回リトライ。失敗 → halt + #metrics エラー |
| Moltbook 失敗 | warning のみ。halt しない |

## Cron

| ジョブ | expr | tz |
|--------|------|----|
| to-agents-skill-discover | `0 1 * * *` | UTC（= 10:00 JST） |
| to-agents-skill-measure | `0 1 * * 1` | UTC（= 毎週月曜 10:00 JST） |
