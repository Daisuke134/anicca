# daily-memory

## 目的
Anicca 用の日次メモリ（学び・日記）を `~/.openclaw/workspace/daily-memory/` に記録する。cron で毎日 1:00 JST に実行される。**AGENTS.md は読まない。** 入力は今日のセッション履歴・standup の結果・cron の成功/失敗とする。

## 必須 env
なし（ファイル読み書きのみ）。

## 必須 tools
- ファイル読み書きまたは `run_terminal_cmd`（lessons-learned への追記、diary ファイルの作成に使用）。AGENTS.md の読取は行わない。

## 入力
- **今日のセッション履歴**（cron 起動時のコンテキスト）
- **roundtable-standup の結果**（該当 run_YYYY-MM-DD.json や Slack 報告）
- **今日の cron の成功/失敗**（各スキルの実行結果）

上記を入力とし、学びを抽出して **lessons-learned.md と diary に書く。**

## 実行手順
1. 今日のセッション履歴・standup の結果・cron の成功/失敗を入力とし、学びを抽出する。
2. 学びを 1〜3 行でまとめ、`~/.openclaw/workspace/daily-memory/lessons-learned.md` に追記する（日付と内容を 1 行で追加）。
3. 今日の日記を `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` に書く。ファイル名の日付は実行日の日付（JST）。中身は短い日次サマリでよい。

## 出力 / 監査ログ
- lessons-learned.md と diary への書き込み結果。失敗時は理由をログに残す。

## Slack 報告
**【絶対】** 実行結果・要約は Slack #metrics（チャンネル ID: `C091G3PKHL2`）に投稿する。成功でも失敗でも必ず投稿する。投稿しないことは許されない。

## 失敗時処理
- ディレクトリ・ファイルが無い: 必要なディレクトリ・ファイルを作成してから書く。

## 禁止事項
- AGENTS.md の読取を一切行わない。学びの元はセッション履歴・standup・cron 結果のみ。
- `workspace/anicca.ai` 以下には書かない。出力先は `~/.openclaw/workspace/daily-memory/` のみ。

## Cron
`0 1 * * *` (1:00 JST 毎日)
