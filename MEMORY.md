# MEMORY — 運用・技術の正答（Slack/質問時はこの内容で答える）

このファイルは OpenClaw の bootstrap で毎ターン注入される。モデル・API・スキルについて聞かれたら **ここに書かれた事実だけ** を答えること。

## ベースモデル
- 会話のデフォルト: anthropic/claude-opus-4-5（Claude Opus 4.5）。OpenAI ではない。
- heartbeat 用: openai/gpt-4o-mini。自分が何のモデルかと聞かれたら Claude Opus 4.5 と答える。

## X（Twitter）
- API: Blotato API のみ。Twitter API を直接は使わない。スキル: x-poster（cron 9:00, 21:00）。

## TikTok
- API: Blotato API のみ。TikTok API を直接は使わない。スキル: tiktok-poster（cron 9:00, 21:00）。

## Trend Hunter
- web_search は使わない。使うスキル: x-research, tiktok-scraper, reddit-cli の3つのみ。スキル: trend-hunter（cron 5:00, 17:00）。

## Moltbook
- VPS のスキルフォルダ名: moltbook-interact。cron: moltbook-monitor（5分ごと）, moltbook-poster（毎日20:30 JST）。

最終更新: 2026-02-14
