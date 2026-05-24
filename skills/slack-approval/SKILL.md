---
name: slack-approval
description: "Slack Block Kitボタンで承認/却下を行う。OpenClaw ビルトイン Slack interaction イベントで完結。Use when any skill needs user confirmation before executing a destructive or external action ({{profile.lateness.stakeholders.channel}} send, form submit, install, deploy, etc.)"
metadata:
  source: "OpenClaw source (OPENCLAW_ACTION_PREFIX='openclaw:') + Slack Block Kit API (api.slack.com/reference/block-kit)"
  requires:
    bins: []
    npm: []
    env:
      - SLACK_BOT_TOKEN
---

# slack-approval

全スキル共通の承認ユーティリティ。**Slack Block Kitボタン（✅ Approve / ❌ Reject）でワンタップ承認。**

## なぜ Block Kit ボタン方式か

| 旧方式 (リアクションポーリング) | 新方式 (Block Kit ボタン) |
|-------------------------------|--------------------------|
| ✅❌ 絵文字リアクションをポーリング | ワンタップボタン |
| 30秒間隔でAPI叩く（無駄） | プッシュ（イベント駆動） |
| UX悪い（絵文字探す必要） | ボタン2つだけ |
| 古いメッセージでも反応しにくい | 8時間後でもボタン押せる |

ソース: Slack Block Kit API — https://api.slack.com/reference/block-kit/block-elements#button
ソース: OpenClawソースコード — `OPENCLAW_ACTION_PREFIX = "openclaw:"` （action_idにこのプレフィックスが必須）

## 仕組み

1. Slack API `chat.postMessage` でBlock Kitボタン付きメッセージを送信
2. ユーザーがボタンを押す
3. OpenClawがSocket Mode経由で `block_actions` イベントを受信
4. セッションに `Slack interaction: action=openclaw:<action_id> ...` として届く

**重要: `action_id` は必ず `openclaw:` プレフィックスを付けること。** これがないとOpenClawが受信しない。

## 使い方（全スキルからこの手順）

### Step 1: ボタン付きメッセージ送信

```bash
SLACK_BOT_TOKEN=$(grep SLACK_BOT_TOKEN ~/.openclaw/.env | head -1 | cut -d= -f2-)

curl -s -X POST https://slack.com/api/chat.postMessage \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "{{profile.channels.reportChannel}}",
    "text": "📋 承認リクエスト: <タイトル>",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "<承認内容のMarkdown>"
        }
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "button",
            "text": {"type": "plain_text", "text": "✅ Approve"},
            "style": "primary",
            "action_id": "openclaw:<スキル名>_approve",
            "value": "<識別子>"
          },
          {
            "type": "button",
            "text": {"type": "plain_text", "text": "❌ Reject"},
            "style": "danger",
            "action_id": "openclaw:<スキル名>_reject",
            "value": "<識別子>"
          }
        ]
      }
    ]
  }'
```

→ `action_id` の命名規則: `openclaw:<スキル名>_approve` / `openclaw:<スキル名>_reject`
→ `value` にスキル固有の識別子を入れる（例: スキル名、タスクID等）

### Step 2: イベント受信

ボタンが押されると、OpenClawのセッションに以下のシステムメッセージが届く:

```
[System Message] Slack interaction: action=openclaw:<スキル名>_approve type=button user=<userId> channel={{profile.channels.reportChannel}}
```

このメッセージの `action=` 部分を見て:
- `_approve` が含まれる → **承認** → アクション実行
- `_reject` が含まれる → **却下** → 停止、#metrics に報告

### Step 3: メッセージ更新（オプション）

承認/却下後、元のメッセージを更新してボタンを削除し、結果を表示:

```bash
curl -s -X POST https://slack.com/api/chat.update \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "{{profile.channels.reportChannel}}",
    "ts": "<元メッセージのts>",
    "text": "✅ Approved by <user>",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "✅ *Approved* by <user>\n\n<元の内容>"
        }
      }
    ]
  }'
```

## 表示される UI

```
┌─────────────────────────────────────┐
│  🏭 to-agents-skill discover        │
│                                     │
│  スキル: prompt-grader               │
│  なぜ: トークンコスト最適化...         │
│  価格: $0.005 USDC                   │
│                                     │
│  [✅ Approve]  [❌ Reject]           │
└─────────────────────────────────────┘
```

## 適用スキル

to-agents-skill / naist-mail / naist-portal / skill-for-you / 全ての新規スキル

## 動作確認済み (2026-02-25)

- ✅ Block Kitボタン送信: `chat.postMessage` with blocks
- ✅ ボタンクリック受信: OpenClaw Socket Mode → `slack:interaction action=openclaw:skill_approve`
- ✅ action_idプレフィックス: `openclaw:` 必須（OpenClawソースコード確認済み）
