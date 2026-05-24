---
name: naist-calendar
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] Google Calendarの予定を取得してSlackに投稿する。Use when user says 「スケジュール確認して」「今日の予定は？」「カレンダー見せて」「予定追加して」「明日の予定」or similar calendar requests in #ai-<name> channels.
metadata:
  source: gcal-digest (Mac Mini既存スキル)
  requires:
    bins: [gog]
    env: [GOG_KEYRING_PASSWORD, GOG_ACCOUNT]
---

# naist-calendar

ユーザーのGoogle Calendarを読む・予定を追加する。

## 実行手順

### 予定を確認する

```bash
export PATH=/opt/homebrew/bin:$PATH
export GOG_ACCOUNT={{profile.contact.personalEmail}}
export GOG_KEYRING_PASSWORD=<password>

# 今日
TODAY=$(date +%Y-%m-%d)
gog calendar events primary --from ${TODAY}T00:00:00+09:00 --to ${TODAY}T23:59:59+09:00 --json

# 明日
TOMORROW=$(date -v+1d +%Y-%m-%d)
gog calendar events primary --from ${TOMORROW}T00:00:00+09:00 --to ${TOMORROW}T23:59:59+09:00 --json
```

### 予定を追加する

```bash
export PATH=/opt/homebrew/bin:$PATH
export GOG_ACCOUNT={{profile.contact.personalEmail}}
export GOG_KEYRING_PASSWORD=<password>

gog calendar events add primary \
  --title "イベント名" \
  --start "2026-02-24T10:00:00+09:00" \
  --end "2026-02-24T11:00:00+09:00" \
  --location "D207"
```

## Slack出力フォーマット

```
📅 本日 MM/DD（曜日）のスケジュール

HH:mm  イベント名 @ 場所
HH:mm  イベント名

📅 明日 MM/DD（曜日）
→ 予定なし  / または予定リスト
```

## 予定追加時の承認フロー

slack-approval を使って確認を取ってから追加する:
- 確認メッセージ: 「HH:mm イベント名 @ 場所 を追加しますか？」
- [✅ 追加する] [❌ キャンセル]

## 投稿先 Slack チャンネル

オンデマンド呼び出しは問い合わせ元のチャンネルに返す。`~/.openclaw/state/naist/<slug>/slack_channel.txt` も参照可能。Cronなし。
