---
name: instagram-poster
description: Daily Instagram Reels/Feed poster for the larry persona accounts (@anicchasan JA, @anicca.monk EN) and the reelclaw card accounts (anicca-en-card-1, anicca-ja-card-1). Posts via Postiz API. Use when instagram-poster-morning or instagram-poster-evening cron fires.
---

# instagram-poster SKILL

## 概要

Postiz API 経由で 4 つの IG アカウントに Reels/Feed を投稿する。larry の slot JSON を再利用。Bible compliance に従い `SELF_ONLY+UPLOAD`（= 各投稿は単一integration、native upload, no cross-post）を厳守。

| 項目 | 値 |
|------|-----|
| 投稿先 | 4 IG accounts（larry × 2、reelclaw × 2） |
| 入力 | larry の slot JSON（morning-{ja,en}.json, evening-{ja,en}.json） |
| 出力 | Postiz post URL → Slack `{{profile.channels.reportChannel}}` 通知 |
| 環境変数 | `POSTIZ_API_KEY` (~/.openclaw/.env から source) |

## ウィザード（初回起動時）

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `POSTIZ_API_KEY` | (.env) | Postiz API key |
| `instagram.dry_run` | `true` | true なら投稿せずプレビューのみ |
| `instagram.slack_channel` | `{{profile.channels.reportChannel}}` | 完了通知先 |

## Postiz integrations

| 用途 | integration_id | handle | language |
|------|---------------|--------|----------|
| larry IG JA | `cmmzujxpa04ujp30yxqpg1vci` | @anicchasan | ja |
| larry IG EN | `cmmzzg2es0539p30ycb94ayx0` | @anicca.monk | en |
| reelclaw IG EN | `cmn8y95rg02d2qx0y09bbk5pb` | anicca-en-card-1 | en |
| reelclaw IG JA | `cmnipef7g00oerm0y3dz4lamx` | anicca-ja-card-1 | ja |

## Bible compliance

| ルール | 実装 |
|--------|------|
| `SELF_ONLY` | post payload で integration を 1 つだけ指定。複数IDを同一POSTにまとめない |
| `UPLOAD` | media は Postiz uploader 経由でアップロード後 `posts[].media[].id` で参照（外部URL共有禁止） |
| `clean BG` | slot JSON の `cleanBg: true` を尊重。背景画像は `assets/6-slide-images/clean/` から取る |

## 実行フロー

```
1. source /Users/anicca/.openclaw/.env
2. LANG=ja|en, SLOT=morning|evening を env で受け取る
3. larry slot JSON を読む: ~/.openclaw/workspace/tiktok-marketing/slots/${SLOT}-${LANG}.json
4. integration_id を決定（上記マッピング）
5. media を Postiz /upload に POST → media_id を取得
6. /posts に POST: { posts: [{ integration: { id }, value, media }] } + flags: ["SELF_ONLY","UPLOAD"]
7. レスポンスから post URL 抽出 → Slack に通知
```

## スクリプト

`scripts/run.sh` — メインエントリ。`LANG` と `SLOT` を env で受ける。`dry_run=true` ならプレビューのみ。

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| POSTIZ_API_KEY 未設定 | `source ~/.openclaw/.env` を必ず実行 |
| slot JSON 不在 | Slack に🚨報告して終了 |
| Postiz 4xx | retry-postiz.py（build-in-public の retry wrapper を再利用）30s × max 3 |
| upload 失敗 | dry_run ログを `~/.openclaw/logs/instagram-poster/` に保存 |

## 絶対禁止

| 禁止 | 理由 |
|------|------|
| 複数integrationを単一POSTで送る | `SELF_ONLY` 違反 |
| 外部画像URLを直接 value に貼る | `UPLOAD` 違反（native upload必須） |
| Slack報告をスキップ | MANDATORY |
