# Skill Interface Contracts: naist-events

## fetch.js

### Input
なし（環境変数 `NAIST_EVENTS_DATA_DIR` でデータディレクトリをオーバーライド可能）

### Output
```javascript
// 成功時
NaistEvent[]  // 今週（月〜日）のイベント配列（空配列あり）

// 失敗時（スクレイピングエラー）
throw new Error("fetch failed: <理由>")
```

### Contract
- Firecrawl CLIで `https://www.naist.jp/event/` をスクレイプ
- 今週（実行時点の月曜0時〜日曜23:59 JST）のイベントのみ返す
- URLが404の場合は `/seminar/` をフォールバック試行

---

## notify.js

### Input
```javascript
notifyEvents(events: NaistEvent[]): { posted: number, skipped: number }
```

### Output
```javascript
{ posted: number, skipped: number }
```

### Contract
- cache.jsonに含まれるIDはスキップ（重複投稿なし）
- DRY_RUN=1 の場合はSlack投稿なし、cache更新なし
- 新規イベントがある場合のSlackフォーマット（下記参照）
- 新規イベントが0件の場合「今週の開催予定イベントはありません」を投稿

### Slack投稿フォーマット
```
📅 今週のNAISTイベント（MM/DD〜MM/DD）

• [タイトル]
  📍 場所  🕐 日時
  🔗 URL

• [タイトル]
  ...
```

---

## scan.js

### Input
なし（cron/手動実行エントリーポイント）

### Output
stdout: `[naist-events] スキャン完了: 新着N件 / スキップN件`

### Contract
- `loadEnv()` で `/Users/anicca/.openclaw/.env` を読む
- エラー時: Slackにエラーメッセージ投稿してexit 0

---

## add-to-calendar.js

### Input (CLI args)
```bash
node scripts/add-to-calendar.js "<title>" "<date>" "<startTime>" "[endTime]" "[location]"
```

### Output
stdout: `[naist-events] カレンダーに追加しました: <title>`

### Contract
- `gog calendar events add primary` を呼び出す
- `--start` は `${date}T${startTime}:00+09:00` 形式
- `--end` は endTimeが不明な場合startTime + 1時間
- 失敗時は stderr に出力してexit 1

---

## utils/storage.js

```javascript
loadCache(): { notified: string[], lastFetchedAt: string|null }
saveCache(cache): void   // atomic write
```

環境変数 `NAIST_EVENTS_DATA_DIR` でデータディレクトリをオーバーライド（テスト用）。

---

## utils/slack.js

```javascript
sendMessage(message: string): void
```

- `DRY_RUN=1` の場合はコンソール出力のみ
- `SLACK_CHANNEL_ID` 環境変数（デフォルト: `C091G3PKHL2`）
