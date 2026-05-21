---
name: hookpost-ttl-cleaner
description: "古い hook の TTL を掃除し、実行結果を workspace に保存する"
metadata: {"openclaw":{"emoji":"🧹","os":["linux"]}}
---

# hookpost-ttl-cleaner

## 目的
TTL 経過した低 relevance の hook_post をアーカイブ・削除。DB の肥大化を防ぐ。

## 保存先（Anicca 内・フルパス）

| 種類 | フルパス |
|------|----------|
| 実行結果 | `/home/anicca/.openclaw/workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json` |

VPS 相対: `~/.openclaw/workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json`。

## 必須 env
| キー | 説明 |
|------|------|
| （実装が参照する DB 等があればその認証） |  |

## 必須 tools
- `web_fetch`（実装で API 利用する場合）

## 入力
- なし（cron 起動）。

## 実行手順
1. VPS 上で TTL 経過した hook_post のアーカイブ・削除を実行する。
2. 結果を `workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json` に書く。
3. 失敗時は Slack に notifyDLQEntry（実装に従う）。

## 出力 / 監査ログ
- `{ archived, deleted, failed }` を上記パスに記録。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 失敗時処理
- 5xx: 次回 cron で再実行。
- hookPost モデル未対応: safe no-op で終了。

## 禁止事項
- なし。

## Cron
`0 3 * * *` (03:00 JST 毎日)
