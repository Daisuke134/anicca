---
name: autonomy-check
description: "運用監査。失敗率やDLQなどをチェックし、結果を workspace に保存する"
metadata: {"openclaw":{"emoji":"🧯","os":["darwin","linux"]}}
---

# autonomy-check

## 目的
規約違反（X 返信ゼロ等）、DLQ 滞留、失敗率等を合否判定し通知。長期運用で劣化しないよう自己点検。

## 保存先（フルパス）

| 種類 | フルパス |
|------|----------|
| 監査ログ | `~/.openclaw/workspace/autonomy-check/audit_YYYY-MM-DD.json` |

## チェック項目

| # | チェック | 合否基準 |
|---|---------|---------|
| 1 | X 返信ゼロ確認 | 直近7日の ops events に `x_reply` が0件 |
| 2 | DLQ 滞留 | `~/.openclaw/workspace/ops/` 内のDLQが5件以下 |
| 3 | cron 失敗率 | 直近24hのcronで失敗が3件以下 |
| 4 | workspace ディスク使用量 | `~/.openclaw/workspace/` が5GB以下 |
| 5 | ゲートウェイ稼働確認 | `pgrep -f "openclaw.*gateway"` が1件以上 |

## 実行手順

1. 今日の日付（Asia/Tokyo）を取得する
2. 各チェック項目を exec ツールで実施する
3. 結果を `audit_YYYY-MM-DD.json` に記録する:
   ```json
   {
     "timestamp": "ISO8601",
     "overall": "PASS" or "WARN" or "FAIL",
     "checks": {
       "x_reply_zero": {"status": "PASS", "count": 0},
       "dlq_backlog": {"status": "PASS", "count": 0},
       "cron_failure_rate": {"status": "PASS", "failed": 0},
       "disk_usage": {"status": "PASS", "gb": 1.2},
       "gateway_running": {"status": "PASS", "pid": 603}
     }
   }
   ```
4. Slack #metrics に結果を投稿する

## 必須 tools
- `exec`（pgrep, du, ls 等）
- `message`（結果通知 — `slack` ツールではなく **ビルトインの `message` ツール** を使う）

<!-- FIX by skill-fixer 2026-04-05:
  原因: isolated session で `slack` ツールを呼ぼうとして "Message failed" エラー
  修正: `message` ツール（action=send, channel=slack, target={{profile.channels.reportChannel}}）を使う
  shell の `openclaw message send` も禁止
-->

## Slack 報告
**【絶対】** 実行結果を Slack #metrics（チャンネル ID: `{{profile.channels.reportChannel}}`）に **`message` ツール** で投稿する。

```
message tool:
  action: send
  channel: slack
  target: {{profile.channels.reportChannel}}
  message: |
    🧯 autonomy-check — ...
```

`slack` ツール・`openclaw message send` コマンドは **絶対に使わない**。

```
🧯 autonomy-check — ✅ PASS / ⚠️ WARN / ❌ FAIL

日時: YYYY-MM-DD HH:MM JST
X返信: ✅ 0件
DLQ滞留: ✅ 0件
cron失敗率: ✅ 正常
ディスク: ✅ <N>GB
Gateway: ✅ 稼働中（PID <N>）
```

## 注意
- **launchd LoadFailed の警告は無視してよい**。ゲートウェイは nohup + .zprofile 自動起動で稼働中。macOS の SSH セッションからは GUI launchd ドメインにアクセスできないため launchctl bootstrap は常に失敗するが、これは正常動作。
- ゲートウェイの生死確認は `pgrep -f "openclaw.*gateway"` で行う。

## 失敗時処理
- 外部コマンド失敗時: WARN として継続（FAILにしない）
- 違反検出: Slack 通知後も次回実行を継続する

## Cron
`0 3 * * *`（03:00 JST 毎日）
