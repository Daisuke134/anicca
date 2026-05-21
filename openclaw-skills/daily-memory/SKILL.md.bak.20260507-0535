# daily-memory

## 目的
Anicca 用の日次メモリ（学び・日記）を VPS の `~/.openclaw/workspace/daily-memory/` に記録する。

## 必須 env
なし（ファイル読み書きのみ）。

## 必須 tools
- ファイル読み書きまたは `run_terminal_cmd`（lessons-learned への追記、diary ファイルの作成に使用）

## 入力
cron 起動。入力は今日のセッション履歴・roundtable-standup の結果・今日の cron の成功/失敗とする。

## 実行手順
1. 今日のセッション履歴・**standup の結果・cron の成功/失敗**を入力とし、学びを抽出する。
2. 学びを 1〜3 行でまとめ、`~/.openclaw/workspace/daily-memory/lessons-learned.md` に追記する（日付と内容を 1 行で追加）。
3. 今日の日記を `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` に書く。ファイル名の日付は実行日の日付（JST）。中身は短い日次サマリでよい。

## 出力 / 監査ログ
- lessons-learned.md への追記と diary ファイルの作成結果。失敗時は理由をログに残す。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 失敗時処理
- ファイルやディレクトリが無い: 必要なディレクトリ・ファイルを作成してから書く。

## 禁止事項
- `workspace/anicca.ai` 以下には書かない。メモリの**書き出し先**は必ず `~/.openclaw/workspace/daily-memory/`（lessons-learned.md, diary-YYYY-MM-DD.md）。AGENTS.md は読まない。
