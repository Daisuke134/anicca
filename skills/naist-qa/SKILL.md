---
name: naist-qa
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] {{profile.education.institution}}関連のことを何でも答える。Use when user says 「DC1って何？」「履修登録どうやる？」「科研費の申請書は？」「{{profile.education.institution}}の学費は？」「奨学金の条件は？」or any {{profile.education.institution}}-related question.
---

# {{profile.education.institution}} QA

{{profile.education.institution}}公式サイト・JSPS・JSTをFirecrawlで検索し、質問に答えて#ai-<username>に投稿する。

## 実行コマンド

```bash
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-qa

# 質問して答えを受け取る（Slackに投稿）
node scripts/qa.js "DC1の申請書は日本語で書くべきですか？"

# DRY_RUN（Slack投稿なし・テスト用）
DRY_RUN=1 node scripts/qa.js "{{profile.education.institution}}の学費は？"

# テスト
npm test
```

## スクリプト構成

| ファイル | 役割 |
|---------|------|
| `scripts/qa.js` | エントリーポイント。質問→回答→Slack投稿 |
| `scripts/answer.js` | Firecrawlで検索→関連段落抽出→回答生成 |
| `scripts/utils/slack.js` | openclaw message send ラッパー |

## 検索対象

| キーワード | 検索先 |
|-----------|--------|
| DC1・DC2・学振・JSPS | jsps.go.jp/j-pd/ |
| JST・ACT-X・さきがけ | jst.go.jp |
| その他全て | naist.jp |

## Cronなし（オンデマンドのみ）

Aniccaが「DC1とは？」等のSlackメッセージを受信したとき自動実行。

## 投稿先 Slack チャンネル

回答は問い合わせ元のチャンネルに返す。問い合わせ元が分からない場合は `~/.openclaw/state/naist/<slug>/slack_channel.txt` を読む。両方とも無ければ `#metrics` (`{{profile.channels.reportChannel}}`) に投稿。
