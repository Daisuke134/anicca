---
name: youtube-shorts-poster
description: Daily YouTube Shorts poster for the reelclaw card accounts (anicca-en-card-1 EN, anicca-ja-card-1 JA). Reuses larry's slot JSON for content. Posts via Postiz API. Use when youtube-shorts-poster cron fires.
---

# youtube-shorts-poster SKILL

## 概要

Postiz API 経由で YouTube Shorts を 2 アカウント（EN + JA）に投稿する。動画は larry slot で生成済みのものを参照。Bible compliance: `SELF_ONLY+UPLOAD`。

| 項目 | 値 |
|------|-----|
| 投稿先 | YT × 2（reelclaw card 1） |
| 入力 | larry の slot JSON + 生成済み video |
| 出力 | YT Short URL → Slack `{{profile.channels.reportChannel}}` 通知 |
| 環境変数 | `POSTIZ_API_KEY` (~/.openclaw/.env) |

## ウィザード

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `POSTIZ_API_KEY` | (.env) | Postiz API key |
| `youtube.dry_run` | `true` | true なら投稿せずプレビューのみ |
| `youtube.slack_channel` | `{{profile.channels.reportChannel}}` | 完了通知先 |
| `youtube.shorts_max_duration_sec` | `60` | Shorts は60s上限 |

## Postiz integrations

| 用途 | integration_id | handle | language |
|------|---------------|--------|----------|
| reelclaw YT EN | `cmmzukbkw04ulp30yfvijrwio` | anicca-en-card-1 | en |
| reelclaw YT JA | `cmn1oukj9012nnq0yqhouc3ib` | anicca-ja-card-1 | ja |

## Bible compliance

| ルール | 実装 |
|--------|------|
| `SELF_ONLY` | 1 POST = 1 integration |
| `UPLOAD` | video は Postiz uploader 経由でアップ→ media_id 参照 |
| `clean BG` | YT Shorts の opening は clean BG 必須（intro slate なし） |

## 実行フロー

```
1. source ~/.openclaw/.env
2. LANG=ja|en で実行
3. 当日の Shorts video パスを決定: ~/.openclaw/workspace/youtube-shorts/${YYYY-MM-DD}/${LANG}.mp4
4. 動画存在確認（duration ≤ 60s, vertical 9:16）
5. media を Postiz /upload に POST → media_id
6. /posts に POST: integration_id, value, media, type=YOUTUBE_SHORTS
7. レスポンス → Slack 通知
```

## スクリプト

`scripts/run.sh` — エントリ。LANG=ja|en, dry_run対応。

## エラーハンドリング

| エラー | 対処 |
|--------|------|
| video が見つからない | Slack 🚨 + 終了（larry の上流に依存） |
| duration > 60s | Shorts 違反 → reject |
| Postiz 4xx | retry 30s × 3 |

## 絶対禁止

| 禁止 | 理由 |
|------|------|
| 1 POST に複数YT integrationを束ねる | SELF_ONLY 違反 |
| 横長動画を投稿 | Shorts feed に乗らない |
| Slack報告スキップ | MANDATORY |
