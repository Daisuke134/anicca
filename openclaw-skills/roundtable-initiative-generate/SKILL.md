---
name: roundtable-initiative-generate
description: "イニシアチブ生成を行い、結果を workspace に保存する"
metadata: {"openclaw":{"emoji":"🧪","os":["linux"]}}
---

# roundtable-initiative-generate

## 目的
Initiative を生成。次の打ち手として各 nudge（App/X/TikTok/Moltbook）に反映。

## 保存先（Anicca 内・フルパス）

| 種類 | フルパス |
|------|----------|
| 実行結果 | `/home/anicca/.openclaw/workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json` |

VPS 相対: `~/.openclaw/workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json`。

## 必須 env
| キー | 説明 |
|------|------|
| （実装が参照する場合のみ） |  |

## 必須 tools
- `web_fetch`（実装で外部 API 利用時）

## 入力
- なし（cron 起動）。

## 実行手順
1. VPS 上で Initiative を生成・保存する処理を実行する。
2. 結果を `workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json` に書く。

## 出力 / 監査ログ
- 上記パスに結果を記録。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 失敗時処理
- 5xx: 次回 cron で再実行。

## 禁止事項
- なし。

## Cron
`5 9 * * *` (09:05 JST)
