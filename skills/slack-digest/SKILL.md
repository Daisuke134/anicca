---
name: slack-digest
description: "Slack #metrics の過去24hメッセージを要約し、日次ダイジェストを作る"
metadata: {"openclaw":{"emoji":"💬","os":["darwin","linux"]}}
---

# slack-digest

## 目的
Slack #metrics チャンネルの過去24時間のメッセージを取得・要約し、全 cron の実行状況・アラート・重要な会話をまとめる。

## 保存先
| 種類 | フルパス |
|------|----------|
| ダイジェスト | `/Users/anicca/.openclaw/workspace/slack-digest/digest_YYYY-MM-DD.json` |

## 必須 env
なし（OpenClaw の Slack 統合を使用）

## 実行手順

### 1. Slack メッセージ取得
message tool の `read` アクションで #metrics の過去24hメッセージを取得:
```
action: read
channel: slack
target: {{profile.channels.reportChannel}}
limit: 100
```

### 2. メッセージ分類・要約
各メッセージを以下に分類:
- **cron 結果**: 成功/失敗/部分成功
- **アラート**: エラー、閾値超過
- **会話**: Dais とのやり取り
- **その他**

### 3. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "ISO8601",
  "status": "success|error",
  "errorMessage": null,
  "period": "24h",
  "totalMessages": 50,
  "cronResults": {
    "success": 15,
    "error": 2,
    "partial": 1,
    "jobs": [
      {"name": "trend-hunter-5am", "status": "success", "summary": "3 trends found"},
      {"name": "moltbook-interact", "status": "error", "summary": "Unknown model error"}
    ]
  },
  "alerts": [
    {"severity": "high", "message": "X API credits depleted", "time": "HH:mm"}
  ],
  "conversations": [
    {"with": "Dais", "topic": "Sonnet migration", "summary": "全cronをSonnetに変更完了"}
  ],
  "dailySummary": "昨日の全体要約（5行以内）",
  "unresolvedIssues": ["X API クレジット補充が必要"]
}
```

### 4. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。

```
💬 slack-digest (HH:mm JST)
━━━━━━━━━━━━━━━
📊 cron: ✅XX / ❌XX / ⚠️XX
🚨 アラート: [件数と要約]
💬 会話: [重要なやり取り要約]
📝 未解決: [対応が必要な項目]
🎯 今日の優先: [最も重要な1アクション]
```

## 失敗時
- Slack 取得失敗 → status: error

## Cron
- 1回/日: 05:35 JST
