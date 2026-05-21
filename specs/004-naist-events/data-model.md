# Data Model: naist-events

## Entities

### NaistEvent

NAISTの1件のイベント情報。

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `id` | `string` | Yes | `${title.slice(0,20)}:${date}` のユニーク識別子 |
| `title` | `string` | Yes | イベントタイトル |
| `date` | `string` (ISO8601 date) | Yes | 開催日（`YYYY-MM-DD`） |
| `time` | `string\|null` | No | 開催時刻（`HH:mm`形式、不明の場合null） |
| `endTime` | `string\|null` | No | 終了時刻（`HH:mm`形式、不明の場合null） |
| `location` | `string\|null` | No | 開催場所（例: `D207`、`大会議室`） |
| `url` | `string` | Yes | イベント詳細URL |
| `description` | `string\|null` | No | イベント概要（100文字以内） |

**バリデーションルール**:
- `title` は1文字以上
- `date` は `YYYY-MM-DD` 形式
- `url` はhttps://から始まる

### EventCache

通知済みイベントのキャッシュ（`data/cache.json`）。

```json
{
  "notified": ["イベントタイトル2...:2026-02-24", "..."],
  "lastFetchedAt": "2026-02-24T09:20:00.000Z"
}
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `notified` | `string[]` | 通知済みイベントIDの配列 |
| `lastFetchedAt` | `string\|null` | 最終取得時刻（ISO8601） |

**デフォルト値**（ファイル未存在時）:
```json
{ "notified": [], "lastFetchedAt": null }
```

## File System

```
/Users/anicca/.openclaw/skills/naist-events/
├── SKILL.md           # スキル定義（YAML frontmatter + 説明）
├── package.json       # Jest設定含む
├── scripts/
│   ├── fetch.js       # Firecrawl → NaistEvent[] 取得
│   ├── notify.js      # fetch → cache dedup → Slack投稿
│   ├── scan.js        # cron entrypoint
│   ├── add-to-calendar.js  # gog CLI呼び出し
│   └── utils/
│       ├── storage.js # cache.json読み書き
│       └── slack.js   # Slack投稿（DRY_RUN対応）
├── data/
│   └── cache.json     # 通知済みキャッシュ（自動生成）
└── tests/
    ├── storage.test.js
    ├── slack.test.js
    ├── fetch.test.js
    ├── notify.test.js
    ├── scan.test.js
    └── calendar.test.js
```
