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
         COALESCE(terminal_summary,''),
         COALESCE(error,'')
  FROM task_runs
  WHERE ended_at >= ? AND ended_at < ?
    AND label IS NOT NULL AND label != ''
  ORDER BY ended_at ASC
''', (start_ms, end_ms))
rows = c.fetchall()

c.execute("SELECT status, COUNT(*) FROM task_runs GROUP BY status")
lifetime = dict(c.fetchall())
conn.close()

succeeded = [r for r in rows if r[1] == 'succeeded']
failed    = [r for r in rows if r[1] == 'failed']
lost      = [r for r in rows if r[1] == 'lost']
other     = [r for r in rows if r[1] not in ('succeeded', 'failed', 'lost')]

def fmt_time(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, JST).strftime('%H:%M')

def truncate(s, n=600):
    s = (s or '').strip()
    return s if len(s) <= n else s[:n].rstrip() + ' …'

def first_line(s, n=200):
    s = (s or '').strip()
    if not s:
        return ''
    head = s.splitlines()[0].strip()
    return truncate(head, n)

# Roundtable-standup outputs for today (any roundtable-* directory)
standup_blocks = []
for path in sorted(glob.glob(str(HOME / '.openclaw' / 'workspace' /
                                  'roundtable-*' / f'run_{today.isoformat()}.json'))):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        standup_blocks.append((pathlib.Path(path).parent.name, data))
    except Exception as e:
        standup_blocks.append((pathlib.Path(path).parent.name, {'_read_error': str(e)}))

lines = []
lines.append(f'# {today.isoformat()} Diary')
lines.append('')
lines.append(f'_Generated {now.strftime("%Y-%m-%d %H:%M %Z")} by daily-memory from runs.sqlite._')
lines.append('')

# --- Summary -----------------------------------------------------------
lines.append('## Summary')
parts = [f'{len(succeeded)} succeeded', f'{len(failed)} failed', f'{len(lost)} lost']
if other:
    parts.append(f'{len(other)} other')
lines.append(f'- Tasks ended today (JST): **{len(rows)}** — ' + ', '.join(parts))
lines.append(f'- Lifetime: {lifetime.get("succeeded", 0)} succeeded / '
             f'{lifetime.get("failed", 0)} failed / {lifetime.get("lost", 0)} lost')
lines.append('')

# --- What I worked on today -------------------------------------------
lines.append('## What I worked on today')
if not rows:
    lines.append("_No task_runs ended in today's window._")
else:
    for label, status, ended_at, summary, error in rows:
        lines.append(f'### {label} — {status} @ {fmt_time(ended_at)}')
        if status == 'succeeded':
            lines.append(truncate(summary) or '_(no terminal_summary)_')
        else:
            if error:
                lines.append(f'**error:** {truncate(error, 400)}')
            if summary:
                lines.append(f'**summary:** {truncate(summary)}')
            if not error and not summary:
                lines.append('_(no error / no summary)_')
        lines.append('')

# --- Wins (compact list for build-in-public) --------------------------
lines.append('## Wins')
if succeeded:
    for label, _, ended_at, summary, _ in succeeded:
        head = first_line(summary)
        if head:
            lines.append(f'- **{label}** ({fmt_time(ended_at)}): {head}')
        else:
            lines.append(f'- **{label}** ({fmt_time(ended_at)}): completed')
else:
    lines.append('_None today._')
lines.append('')

# --- Failures / blockers (postmortem fodder for article-writer) -------
lines.append('## Failures / blockers')
if failed or lost:
    for label, status, ended_at, summary, error in failed + lost:
        msg = first_line(error) or first_line(summary)
        lines.append(f'- **{label}** ({status} @ {fmt_time(ended_at)}): {msg or "_no message_"}')
else:
    lines.append('_None today._')
lines.append('')

# --- Roundtable-standup ------------------------------------------------
lines.append('## Roundtable-standup')
if standup_blocks:
    for name, data in standup_blocks:
        lines.append(f'### {name}')
        if list(data.keys()) == ['_read_error']:
            lines.append(f'_(read error: {data["_read_error"]})_')
            lines.append('')
            continue
        report = data.get('standup_report', data)
        emitted = False
        for key in ('current_focus', 'recent_achievements', 'next_priorities', 'blockers'):
            vals = report.get(key)
            if not vals:
                continue
            emitted = True
            lines.append(f'**{key}:**')
            if isinstance(vals, list):
                for v in vals:
                    lines.append(f'- {v}')
            else:
                lines.append(f'- {vals}')
        if not emitted:
            # Fallback: dump the JSON keys we have so it's still useful
            lines.append('```json')
            lines.append(json.dumps(report, ensure_ascii=False, indent=2)[:1500])
            lines.append('```')
        lines.append('')
else:
    lines.append('_No roundtable-standup output for today._')
lines.append('')

# --- Themes for write-ups (hint for article-writer) -------------------
lines.append('## Themes for write-ups')
themes = []
if failed:
    themes.append('Postmortem candidates: ' + ', '.join(sorted({r[0] for r in failed})))
if lost:
    themes.append('Lost runs to investigate: ' + ', '.join(sorted({r[0] for r in lost})))
big = sorted([r for r in succeeded if len(r[3]) > 400], key=lambda r: -len(r[3]))[:3]
if big:
    themes.append('Notable detailed runs: ' + ', '.join(r[0] for r in big))
if not themes:
    themes.append('Routine day — consider writing about pipeline reliability or process.')
for t in themes:
    lines.append(f'- {t}')
lines.append('')

diary_path.write_text('\n'.join(lines), encoding='utf-8')
print(f'wrote {diary_path} ({len(rows)} rows)')
PY
```

このステップが終わると `${DIARY_DIR}/diary-${TODAY}.md` に「実際の本日の cron 実行結果」が書き込まれている。**プレースホルダ（自己言及テキスト）になっていないか、必ず開いて確認すること。**

### Step 2: lessons-learned.md に 1 行追記

Step 1 で生成された diary を読み、今日の最重要の学びを 1 行で抽出して追記する（失敗があれば失敗から、なければ目立った成功や工程上の気づきから）。**ここだけは LLM が判断する。**

ルール:
- 形式: `YYYY-MM-DD: <1〜3 行の自然言語>`
- 既存行を書き換えない（append のみ）
- diary に書かれていない事実を追加しない（hallucination 禁止）
- 「daily-memory 自身が動いた」のような自己言及は **書かない**

```bash
LESSONS_FILE="/Users/anicca/.openclaw/workspace/daily-memory/lessons-learned.md"
DIARY_PATH="/Users/anicca/.openclaw/workspace/daily-memory/diary-${TODAY}.md"
# diary を読んで 1 行で要約 → echo "${TODAY}: ..." >> "$LESSONS_FILE"
```

### Step 3: Slack 報告

cron delivery (`announce` mode) が自動で Slack #metrics (`{{profile.channels.reportChannel}}`) に投稿するため、**cron から呼ばれた場合は何もしない**。手動実行のときのみ `message` ツール（ビルトイン）で報告する。`openclaw message send` の shell CLI は使わない。

---

## 失敗時処理

| 失敗 | 対処 |
|------|------|
| `runs.sqlite` が無い / 開けない | Step 1 のスクリプトが警告だけ書いた diary を残す。後段は昨日の diary にフォールバックできる。 |
| `daily-memory` ディレクトリが無い | `mkdir -p` で作成する（スクリプトでハンドル済み） |
| roundtable-standup が今日無い | 「_No roundtable-standup output for today._」と明示する（既にハンドル済み） |

---

## 禁止事項

- `workspace/anicca.ai` 以下に書かない。
- `~/.openclaw/memory/` に書かない。
- 出力先は必ず `~/.openclaw/workspace/daily-memory/`（`lessons-learned.md` と `diary-YYYY-MM-DD.md` のみ）。他の場所にコピー・重複を作らない。
- AGENTS.md は読まない。
- diary に「daily-memory が動いた」「ツールがロードされた」のような自己言及プレースホルダを書かない。Step 1 のデータパイプラインを信頼してその出力を上書きしない。
- cron delivery が Slack 投稿を担うので、自前で `message` を送らない（cron 経由のとき）。
