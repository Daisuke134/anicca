---
name: x-research
description: "X の検索とリサーチ（最新の反応・論点・メトリクス）を取得する"
metadata: {"openclaw":{"emoji":"🔎","os":["linux"]}}
---

# X Research（Anicca 用）

**インストール:** VPS で `~/.openclaw/skills/x-research` に [rohunvora/x-research-skill](https://github.com/rohunvora/x-research-skill) を clone する（trend-hunter がこのパスを参照）。コピペで同じコードを置かない。README のセットアップ（Bun, **X_BEARER_TOKEN** を `~/.openclaw/.env` に設定、openclaw.json）を実行する。X 検索は X_BEARER_TOKEN 必須（Firecrawl では X をスクレイプできない）。初回: `scripts/openclaw-vps/install-full-skills-on-vps.sh` を参照。

## いつ使うか

- OpenClaw の新プラグイン・セットアップ・メモリ・セキュリティ・ベストプラクティスを X で検索するとき
- spec 用に「この投稿・スレッドの全文」が欲しいとき（要約ではなく生データ）
- 特定ユーザー（例: アプリ開発をガチで自動化している人）の直近を追うとき

要約だけ欲しい場合は Grok（xAI）系を検討する。開発まわりのループは **anicca-auto-development** スキルに任せる。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 実行（VPS）

```bash
cd ~/.openclaw/skills/x-research
bun run x-search.ts <command> [options]
```

## 例（自己改善向け）

```bash
# 検索（コスト抑えは --quick）
bun run x-search.ts search "OpenClaw plugin" --sort likes --limit 20
bun run x-search.ts search "OpenClaw automation app development" --since 7d --quality --quick
bun run x-search.ts search "from:someone_automating_everything" --sort recent --limit 10

# スレッド取得
bun run x-search.ts thread <tweet_id>

# ユーザー直近
bun run x-search.ts profile <username>

# 保存して報告/spec に渡す
bun run x-search.ts search "OpenClaw OR openclaw setup" --save --markdown
```

全オプション・watchlist・cache は clone したリポの README / SKILL を参照。
