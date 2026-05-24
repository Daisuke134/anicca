---
name: naist-metrics
description: [DEPRECATED v1 — replaced by ~/.openclaw/skills/naist/ unified v2; this stub is kept for ledger continuity] TikTokパフォーマンスレポートを毎朝Slackに投稿する（ダイス専用）。Use when user says 「TikTokのメトリクスは？」「昨日の再生数は？」「フォロワー増えた？」or any TikTok metrics request.
---

# {{profile.education.institution}} Metrics (TikTok パフォーマンスレポート)

Apify clockworks~tiktok-scraper でTikTokアカウントの最新動画メトリクスを取得し、#ai-<username>に投稿する。

## 実行コマンド

```bash
export PATH=/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:$PATH
cd /Users/anicca/.openclaw/skills/naist-metrics

# 実行（Slack投稿）
node scripts/metrics.js

# DRY_RUN（Slack投稿なし・テスト用）
DRY_RUN=1 node scripts/metrics.js

# テスト
npm test
```

## 必須 env

| キー | 説明 |
|------|------|
| `APIFY_API_TOKEN` | Apify API トークン（`~/.openclaw/.env` に設定済み） |
| `TIKTOK_USERNAME` | TikTokアカウント名（デフォルト: `your-handle`） |

## スクリプト構成

| ファイル | 役割 |
|---------|------|
| `scripts/report.js` | 数値フォーマット・レポート生成ロジック |
| `scripts/metrics.js` | エントリーポイント。Apify API呼び出し→Slack投稿 |
| `scripts/utils/slack.js` | openclaw message send ラッパー |

## 出力例

```
📊 *TikTok パフォーマンス（2026-02-24）*

▶️  総再生数: 12.8k
❤️  総いいね: 600
🎬  動画数: 2件
🏆  最高動画: 「AIエージェントの使い方...」(12.8k再生)
```

## Cron

毎朝09:25 JST（`25 9 * * *`）に自動実行。

## 状態ファイル

投稿先 Slack channel ID は `~/.openclaw/state/naist/<slug>/slack_channel.txt` を優先（無ければ従来通り `#ai-<username>` ハードコード）。`<slug>` 解決方法は他の naist-* skill と同様。
