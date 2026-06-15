---
name: daily-memory
description: Aggregates today's OpenClaw cron run results (succeeded/failed/lost + terminal_summary/error from runs.sqlite) plus any roundtable-standup output into a structured diary at ~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md, then appends a one-line learning to lessons-learned.md. The diary is the upstream input for build-in-public (23:10 JST) and article-writer (23:30 JST).
---

# daily-memory SKILL

## 目的

毎日 23:00 JST に発火する cron。今日（JST 0:00〜23:59）の cron 実行結果を `~/.openclaw/tasks/runs.sqlite` から集計し、roundtable-standup の出力もあれば取り込んで、`~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` に **構造化された日記ファイル** を書く。

このファイルは **build-in-public（23:10）** と **article-writer（23:30）** の必須入力。だから「daily-memory 自身の bootstrap」のような自己言及プレースホルダではなく、その日に実際に何が起きたかを raw data ベースで残すのが本タスクのゴール。

## 必須 env

なし（読み取りのみで動く: sqlite3 経由で `~/.openclaw/tasks/runs.sqlite`、ファイル glob で `~/.openclaw/workspace/roundtable-*/`）。

## 必須 tools

- `bash` / `python3`（macOS 標準。`sqlite3` モジュールは標準ライブラリ）
- ファイル書き込み（diary と lessons-learned）

## 入力

- `~/.openclaw/tasks/runs.sqlite` の `task_runs` テーブル
  - 主要カラム: `label`, `status` (`succeeded` / `failed` / `lost`), `ended_at` (epoch ms), `terminal_summary`, `error`
- `~/.openclaw/workspace/roundtable-*/run_YYYY-MM-DD.json`（あれば）

## 出力

- `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md`（今日の日記、JST 日付）
- `~/.openclaw/workspace/daily-memory/lessons-learned.md`（1 行追記）

---

## 実行手順

### Step 1: diary をデータから生成（headless / LLM 不要）

`runs.sqlite` を read-only で開いて今日（JST 00:00〜翌日 00:00）に `ended_at` が入る行を全部引き、succeeded / failed / lost に分類して構造化 markdown を書く。LLM 判断は使わない — 純データ集約。

このステップは下記のシェル/Python ワンショットで完結する。**この一塊をそのまま実行すること。** 出力先は `diary-${TODAY}.md`。

```bash
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
TODAY=$(TZ=Asia/Tokyo date +%Y-%m-%d)
DIARY_DIR="/Users/anicca/.openclaw/workspace/daily-memory"
mkdir -p "$DIARY_DIR"

python3 - <<'PY'
import datetime, glob, json, pathlib, sqlite3, zoneinfo

JST = zoneinfo.ZoneInfo('Asia/Tokyo')
now = datetime.datetime.now(JST)
today = now.date()
start = datetime.datetime(today.year, today.month, today.day, tzinfo=JST)
end = start + datetime.timedelta(days=1)
start_ms = int(start.timestamp() * 1000)
end_ms = int(end.timestamp() * 1000)

HOME = pathlib.Path.home()
DB = HOME / '.openclaw' / 'tasks' / 'runs.sqlite'
DIARY_DIR = HOME / '.openclaw' / 'workspace' / 'daily-memory'
DIARY_DIR.mkdir(parents=True, exist_ok=True)
diary_path = DIARY_DIR / f'diary-{today.isoformat()}.md'

# Read-only — daily-memory itself is running so the DB has live writers.
uri = f'file:{DB}?mode=ro'
try:
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
except sqlite3.OperationalError as e:
    diary_path.write_text(
        f'# {today.isoformat()} Diary\n\n'
        f'_runs.sqlite を開けませんでした: {e}_\n', encoding='utf-8')
    print(f'wrote {diary_path} (db open failed)')
    raise SystemExit(0)

c = conn.cursor()
c.execute('''
  SELECT label, status, ended_at,
