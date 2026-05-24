---
name: gcal-digest
description: "Google Calendar の今日と明日の予定を取得し、workspace に保存する"
metadata: {"openclaw":{"emoji":"📅","os":["darwin","linux"]}}
---

# gcal-digest

## 目的
Dais の Google Calendar（{{profile.contact.personalEmail}}）から今日・明日の予定を取得。スケジュール管理を支援。

## 保存先
| 種類 | フルパス |
|------|----------|
| ダイジェスト | `/Users/anicca/.openclaw/workspace/gcal-digest/digest_YYYY-MM-DD.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `GOG_KEYRING_PASSWORD` | gog キーリング認証 |

## 実行手順

### 1. Calendar 取得（ローカル）
```bash
# 今日
export PATH=/opt/homebrew/bin:$PATH && export GOG_ACCOUNT={{profile.contact.personalEmail}} && export GOG_KEYRING_PASSWORD=<password> && gog calendar events primary --from YYYY-MM-DDT00:00:00+09:00 --to YYYY-MM-DDT23:59:59+09:00 --json

# 明日
export PATH=/opt/homebrew/bin:$PATH && export GOG_ACCOUNT={{profile.contact.personalEmail}} && export GOG_KEYRING_PASSWORD=<password> && gog calendar events primary --from TOMORROW_T00:00:00+09:00 --to TOMORROW_T23:59:59+09:00 --json
```

### 2. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "ISO8601",
  "status": "success|error",
  "errorMessage": null,
  "today": {
    "eventCount": 3,
    "events": [
      {
        "title": "イベント名",
        "start": "HH:mm",
        "end": "HH:mm",
        "location": "場所",
        "description": "説明（短縮）"
      }
    ]
  },
  "tomorrow": {
    "eventCount": 1,
    "events": []
  },
  "freeSlots": ["10:00-12:00", "15:00-17:00"],
  "advisory": "今日は午後に空きあり。集中作業に使えます。"
}
```

### 3. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。全て日本語。

```
📅 gcal-digest (HH:mm JST)
━━━━━━━━━━━━━━━
📋 今日: X件の予定
  [時間] イベント名 @ 場所
  [時間] イベント名 @ 場所
📋 明日: X件の予定
  [時間] イベント名
🕐 空き: [フリースロット]
💡 [スケジュールに関するアドバイス]
```

## 失敗時
- SSH/Mac接続失敗 → status: error
- 予定0件 → 正常（status: success）

## Cron
- 1回/日: 05:45 JST
