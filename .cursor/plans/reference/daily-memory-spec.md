# daily-memory 仕様・TODO（Anicca 用メモリ）

## 決めたこと

- **毎日やる仕組み:** OpenClaw の cron 1 本。毎日 **23:00 JST** にスキル `daily-memory` を実行する。
- **スキル名:** `daily-memory`
- **スキル置き場（VPS）:** `/home/anicca/.openclaw/skills/daily-memory/`
- **メモリ置き場（VPS）:** `/home/anicca/.openclaw/memory/anicca/`（`workspace/anicca.ai` は使わない）

## パス一覧（VPS）

| 用途 | パス |
|------|------|
| 何を見るか | `/home/anicca/.openclaw/memory/anicca/AGENTS.md` |
| 学び（追記のみ） | `/home/anicca/.openclaw/memory/anicca/lessons-learned.md` |
| 日記（1日1ファイル） | `/home/anicca/.openclaw/memory/anicca/diary-YYYY-MM-DD.md` |
| スキル | `/home/anicca/.openclaw/skills/daily-memory/` |
| cron 定義 | `/home/anicca/.openclaw/cron/jobs.json` |

## スキルがやること

1. `/home/anicca/.openclaw/memory/anicca/AGENTS.md` を読む
2. 今日の学びを `/home/anicca/.openclaw/memory/anicca/lessons-learned.md` に追記する
3. 今日の日記を `/home/anicca/.openclaw/memory/anicca/diary-YYYY-MM-DD.md` に書く（実行日の日付）

## TODO リスト（実行順）

| # | やること | 実行場所 |
|---|----------|----------|
| 1 | VPS に `memory/anicca` を作る | VPS: `mkdir -p /home/anicca/.openclaw/memory/anicca` |
| 2 | スキル `daily-memory` をリポジトリに追加し、VPS に rsync | ローカル→VPS: `rsync -av --exclude='jobs.json' openclaw-skills/ anicca@46.225.70.241:/home/anicca/.openclaw/skills/` |
| 3 | `jobs.json` に daily-memory ジョブを追加し、VPS に送る | ローカルで jobs.json 編集 → Gateway 停止 → scp → Gateway 起動 |
| 4 | openclaw.json の skills.entries に daily-memory を追加（必要なら） | VPS で確認・編集 |
| 5 | AGENTS.md を 1 回用意する（中身は人間が書く） | VPS: `/home/anicca/.openclaw/memory/anicca/AGENTS.md` |

## Cron ジョブ定義

- jobId: `daily-memory`
- schedule: `0 23 * * *` (23:00 JST 毎日)
- payload.message: Execute daily-memory skill. Read /home/anicca/.openclaw/memory/anicca/AGENTS.md. Append today's learnings to /home/anicca/.openclaw/memory/anicca/lessons-learned.md. Write today's diary to /home/anicca/.openclaw/memory/anicca/diary-YYYY-MM-DD.md (use today's date in YYYY-MM-DD).
