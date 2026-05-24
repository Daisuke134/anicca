---
name: naist-events
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] {{profile.education.institution}}の今週のイベント（講演会・セミナー）をSlackに週次通知する。Use when user says 「今週の{{profile.education.institution}}イベントは？」「イベントを確認して」「{{profile.education.institution}}のセミナーは？」「イベント通知して」or related {{profile.education.institution}} event queries.
disable-model-invocation: true
---

# {{profile.education.institution}} Events Notifier

{{profile.education.institution}}のイベントページをFirecrawlでスクレイプし、今週開催予定のイベントをSlackに通知する。

## 実行コマンド

```bash
# 通知実行（本番）
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-events
node scripts/scan.js

# テスト実行（Slack投稿なし）
DRY_RUN=1 node scripts/scan.js

# 自動テスト
npm test
```

## スクリプト構成

| ファイル | 役割 |
|---------|------|
| `scripts/scan.js` | エントリーポイント。fetch + notify を呼ぶ |
| `scripts/fetch.js` | Firecrawlでnaist.jpをスクレイプし今週イベントを返す |
| `scripts/notify.js` | 重複除外してSlackに投稿、cache更新 |
| `scripts/add-to-calendar.js` | gogでGoogleカレンダーに登録 |
| `scripts/utils/storage.js` | cache.json 読み書き |
| `scripts/utils/slack.js` | openclaw message send ラッパー |

## スクレイプ対象

- Primary: `https://www.naist.jp/event/`
- Fallback: `https://www.naist.jp/seminar/`

## データ

- キャッシュ: `data/cache.json`（通知済みID一覧）
- SLACK_CHANNEL_ID: 解決順序は `~/.openclaw/state/naist/<slug>/slack_channel.txt` → 環境変数 `SLACK_CHANNEL_ID` → デフォルト `{{profile.channels.reportChannel}}`（#metrics）

## 状態ファイル（cron `naist-events-weekly` 用）

cron 実行時は `~/.openclaw/state/naist/<slug>/slack_channel.txt` を読み、無ければ `#metrics` に "naist not yet onboarded" を1行で投稿して終了。`<slug>` は `~/.openclaw/state/naist/` 配下のディレクトリ一覧から全ユーザー分。

## Cronスケジュール

毎週月曜 10:00 JST（`0 10 * * 1`、id=`naist-events-weekly`）に自動実行。
