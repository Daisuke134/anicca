---
name: gmail-digest
description: "Gmail の過去24h未読メールを要約し、workspace に保存する"
metadata: {"openclaw":{"emoji":"📧","os":["darwin","linux"]}}
---

# gmail-digest

## 目的
Dais の Gmail（{{profile.contact.personalEmail}}）の過去24時間の未読メールを取得・要約。重要なメールを見逃さないようにする。

## 保存先
| 種類 | フルパス |
|------|----------|
| ダイジェスト | `/Users/anicca/.openclaw/workspace/gmail-digest/digest_YYYY-MM-DD.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `GOG_KEYRING_PASSWORD` | gog キーリング認証 |

## 実行手順

### 1. Gmail 取得（ローカル）
```bash
export PATH=/opt/homebrew/bin:$PATH && export GOG_ACCOUNT={{profile.contact.personalEmail}} && export GOG_KEYRING_PASSWORD=<password> && gog gmail search 'newer_than:1d is:unread' --max 20 --json
```

### 2. 重要度分類
各メールを以下に分類:
- 🔴 **緊急**: 請求、セキュリティ、期限付き
- 🟡 **要確認**: 仕事関連、返信必要
- 🟢 **参考**: ニュースレター、通知
- ⚪ **スキップ**: プロモーション、自動通知

### 3. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "ISO8601",
  "status": "success|error",
  "errorMessage": null,
  "totalUnread": 10,
  "{{profile.lateness.stakeholders.channel}}s": [
    {
      "id": "xxx",
      "from": "sender@example.com",
      "subject": "件名",
      "date": "ISO8601",
      "priority": "urgent|review|info|skip",
      "summary": "2行要約",
      "actionNeeded": true,
      "suggestedAction": "返信する/無視してOK/支払い確認"
    }
  ],
  "dailySummary": "今日のメール要約（3行以内）"
}
```

### 4. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。全て日本語。

```
📧 gmail-digest (HH:mm JST)
━━━━━━━━━━━━━━━
📬 未読: X件 (🔴X 🟡X 🟢X)
[重要メールの1行要約 × 最大5件]
🎯 要対応: [具体的アクション]
```

## 失敗時
- SSH/Mac接続失敗 → status: error、理由記録

## Cron
- 1回/日: 05:40 JST
