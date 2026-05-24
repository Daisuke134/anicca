---
name: naist-funds
version: 1.0.0
description: >
  [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] {{profile.education.institution}}学生向け科研費・奨学金・研究助成金の新着情報をSlackで週次自動通知する。
  Use when user says 「助成金調べて」「奨学金情報」「科研費は？」「JSPSの公募」
  「学振の申請方法」「資金調達」「研究費」or wants grant/scholarship information.
author: anicca
commands:
  - trigger: "助成金情報を更新|奨学金を更新|refresh funds|科研費を更新"
    description: 助成金情報を即時取得してSlackに投稿する
    action: "node /Users/anicca/.openclaw/skills/naist-funds/scripts/scan.js"
  - trigger: "(.+)の申請方法|(.+)に申請|apply for (.+)"
    description: 申請手順をステップ形式で案内する
    action: "node /Users/anicca/.openclaw/skills/naist-funds/scripts/guide.js \"$1\""
---

# naist-funds スキル

JSPS・JST・JFUNDから助成金・奨学金・研究助成金の新着情報を取得し、Slackに投稿する。

## 自動実行（cron）

毎週月曜 09:00 JST に `scripts/scan.js` が自動起動（id=`naist-funds-weekly`）。

## 状態ファイル（cron 用）

cron 実行時は `~/.openclaw/state/naist/<slug>/slack_channel.txt` を読み、無ければ `#metrics` (`{{profile.channels.reportChannel}}`) に "naist not yet onboarded" を1行で投稿して終了。`<slug>` は `~/.openclaw/state/naist/` 配下のディレクトリ一覧から全ユーザー分。

## 手動実行

```bash
# 即時取得・投稿
node /Users/anicca/.openclaw/skills/naist-funds/scripts/scan.js

# ドライラン（Slack投稿なし）
DRY_RUN=1 node /Users/anicca/.openclaw/skills/naist-funds/scripts/scan.js

# 申請手順を検索
node /Users/anicca/.openclaw/skills/naist-funds/scripts/guide.js "学振DC1"
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| SLACK_CHANNEL_ID | 投稿先チャンネルID（state ファイルが優先） | {{profile.channels.reportChannel}} |
| DRY_RUN | 1に設定でSlack投稿スキップ | 未設定 |

## ソース

| サイト | URL | カテゴリ |
|--------|-----|---------|
| JSPS | https://www.jsps.go.jp/j-grantsinaid/ | 科研費 |
| JST | https://www.jst.go.jp/boshu.html | 研究助成 |
| JFUND | https://www.jfund.or.jp/ | 研究助成 |
