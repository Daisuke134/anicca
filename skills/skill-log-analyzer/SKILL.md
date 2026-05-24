---
name: skill-fixer
description: 全cronのログを読み、失敗原因を調査し、SKILL.mdを直接修正して次回成功させる。
---

# skill-fixer SKILL

## 核心ルール

1. **Slackを絶対に信用しない。** 実物確認のみ。
2. **ルール追記で済ませない。** レシピの間違い箇所を直接修正する。
3. **修正には必ずweb_searchで正しいやり方を調べる。** 推測で直さない。
4. **Slack報告は必ず送信先を明示する。** `message` / `openclaw message send` は `target: {{profile.channels.reportChannel}}` を必ず付ける。省略すると `Delivering to Slack requires target <channelId|user:ID|channel:ID>` で失敗する。
5. **直せないもの（外部API障害等）はSlack通知のみ。**
6. **この cron からは Slack を直接送らない。** cron delivery が配信する前提で、SKILL.md 側の手順だけ直す。
7. **SKILL.mdの削除は禁止。編集・追記のみ。**

## 実行手順

### Step 1: 全有効cronの状態を取得

cron tool → action=list で全cronを取得。
各cronの state.lastRunStatus, state.lastError, state.consecutiveErrors を確認。
consecutiveErrors >= 1 のcronだけ深掘りする。
全部OKなら「✅ 全cron正常」報告して終了。

### Step 2: 失敗cronの実物を確認

各失敗cronタイプごとに実物確認:

| cronタイプ | 確認方法 | 成功条件 |
|-----------|---------|---------|
| article-writer | curl https://zenn.dev/anicca/articles/{slug} | HTTP 200 |
| slideshow-* | Postiz API GET /posts → state | PUBLISHED |
| reelclaw-* | Postiz API GET /posts → state | PUBLISHED |
| mau-tiktok-* | Postiz API GET /posts → state | PUBLISHED |
| app-metrics | cat metrics_YYYY-MM-DD.json → .status | success |
| trend-hunter-* | jq '.hooks[-1].addedDate' hooks-*.json | 今日 |
| factory-bp-* | ls workspace/factory-evolution/*-YYYY-MM-DD.md | 存在 |

### Step 3: 失敗の原因を調査して修正する

各失敗cronについて以下を実行:

1. そのスキルのSKILL.mdを read で読む
2. エラーメッセージからどの行/ステップが失敗したか特定する
3. 原因を調べる:
   - "Message failed" → SKILL.md内のSlack報告部分を探す→文字数確認
   - "0件" → SKILL.md内の検索クエリを探す→実際に同じクエリを試す
   - "404" → SKILL.md内のURLを探す→curlで確認
   - "timeout" → SKILL.md内のAPI呼び出しを探す→タイムアウト設定確認
   - 不明 → web_search "エラーメッセージ 原因 修正方法" で調べる
4. SKILL.mdの該当行を edit で直接修正する:
   修正箇所に注釈を付ける:
   ```
   # FIX by skill-fixer YYYY-MM-DD:
   # 原因: [エラーメッセージ]
   # 修正: [何を変えたか]
   ```
5. 直せないもの（外部APIエラー等）はSlack通知のみ:
   "⚠️ 手動対応: [cron名] [エラー内容]"

### Step 4: 結果保存

~/.openclaw/workspace/skill-evolution/log-analysis-YYYY-MM-DD.md

フォーマット:
```markdown
# Skill-Fixer Report — YYYY-MM-DD
## Checked: N crons (N failed)
## Fixes Applied
### [cron名]
- Error: [エラーメッセージ]
- Cause: [原因]
- File: [修正したファイルパス]
- Change: [何を変えたか]
## Manual Action Required
- [cron名]: [理由]
```

### Step 5: Slack報告（100文字以内）

Slack送信時は必ず `target: {{profile.channels.reportChannel}}` を明示する。

"🔧 skill-fixer | 全Ncron | 失敗:N | 修正:N | 手動:N"
