---
name: hookpost-ttl-cleaner
description: "workspace/hooks の古いJSONファイルをアーカイブ・削除してディスク肥大化を防ぐ"
metadata: {"openclaw":{"emoji":"🧹","os":["darwin","linux"]}}
---

# hookpost-ttl-cleaner

## 目的
`~/.openclaw/workspace/hooks/` 配下の古い JSON ファイル（9am/9pm スロット）を TTL に基づきアーカイブ・削除。ディスク肥大化を防ぐ。

## TTL ルール

| 対象 | TTL | 処理 |
|------|-----|------|
| `hooks/9am/` の JSON | 30日以上 | `archive/9am/` に移動 |
| `hooks/9pm/` の JSON | 30日以上 | `archive/9pm/` に移動 |
| `archive/` の JSON | 90日以上 | 完全削除 |

## 保存先（フルパス）

| 種類 | フルパス |
|------|----------|
| アーカイブ先 | `~/.openclaw/workspace/hookpost-ttl-cleaner/archive/9am/` |
| アーカイブ先 | `~/.openclaw/workspace/hookpost-ttl-cleaner/archive/9pm/` |
| 実行結果 | `~/.openclaw/workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json` |

## 実行手順

1. 今日の日付（Asia/Tokyo）を取得する
2. `~/.openclaw/workspace/hooks/9am/` の全JSONファイルを一覧取得する
3. ファイル名（`YYYY-MM-DD.json`）の日付が30日以上前のものを `archive/9am/` へ移動する
4. `~/.openclaw/workspace/hooks/9pm/` も同様に処理する
5. `archive/` 内で90日以上前のファイルを削除する
6. 結果を `run_YYYY-MM-DD.json` に記録する:
   ```json
   {
     "timestamp": "ISO8601",
     "archived_9am": <件数>,
     "archived_9pm": <件数>,
     "deleted": <件数>,
     "archived_files": ["2025-11-20.json", ...],
     "deleted_files": ["2025-08-01.json", ...]
   }
   ```
7. Slack #metrics に結果を投稿する

## 必須 tools
- `exec`（ファイル操作：mv, rm, ls コマンド）
- `slack`（結果通知）

## Slack 報告
**【絶対】** 実行結果を Slack #metrics（チャンネル ID: `{{profile.channels.reportChannel}}`）に投稿する。

```
🧹 hookpost-ttl-cleaner — ✅ 完了 / ❌ 失敗

日時: YYYY-MM-DD HH:MM JST
アーカイブ: 9am <N>件 / 9pm <N>件
削除: <N>件
対象ファイル: <ファイル名リスト or "なし">
```

## 失敗時処理
- ファイルが見つからない場合: "対象なし" として正常終了（エラーにしない）
- ファイル移動失敗時: エラーをログに記録し Slack 通知

## Cron
`0 3 * * *`（03:00 JST 毎日）
