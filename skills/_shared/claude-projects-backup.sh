#!/usr/bin/env bash
# claude-projects-backup.sh — ~/.claude/projects (Claude Code session transcripts)
# の日次世代バックアップ。copy+tweak元: browser-state-backup.sh（同じ
# ~/.cloak/state-backups/<YYYY-MM-DD>/ 世代保持パターンを踏襲、他backupと
# 同じ date ディレクトリを共有するのでプルーニングは自分のサブディレクトリ
# 「claude-projects」だけを対象にする＝他backupの世代を巻き込んで消さない）。
#
# なぜ要るか(2026-07-16 incident): Claude Code は起動の度に settings.json の
# cleanupPeriodDays より古い session transcript(*.jsonl) を自前で削除する
# (公式: docs.claude.com/en/docs/claude-code/settings, "at startup")。この削除は
# SessionStart hook より先に走るため、floor-guard.py の guard_cleanup_period()
# (値を99999へ復旧するだけ)では「値が壊れてから次回起動までの間」に消えた
# transcript を守れない(順序穴)。ここで日次スナップショットを取っておき、
# floor-guard.py の guard_restore_transcripts() が復元できる元を用意する。
#
# memory/ は不可侵 store(feedback: 消すな/動かすな)だが「読み取って backup に
# 含める」のは問題ない(backup は追加のみ、既存 memory を書き換えない)。
# 復元側(floor-guard.py)が memory/ に一切触れないことで担保する。
set -uo pipefail

SRC="$HOME/.claude/projects"
BACKUP_ROOT="$HOME/.cloak/state-backups"
LOG="$HOME/.local/state/life-manager/logs/claude-projects-backup.log"
KEEP_GENERATIONS=14
mkdir -p "$BACKUP_ROOT" "$(dirname "$LOG")"

_log() { echo "$(date '+%F %T') claude-projects-backup: $*" >>"$LOG"; }

date_tag="$(date '+%F')"
dest="$BACKUP_ROOT/$date_tag/claude-projects"
mkdir -p "$dest"

rsync -a --update "$SRC/" "$dest/" 2>>"$LOG"
rc=$?

count=$(find "$dest" -maxdepth 2 -name '*.jsonl' 2>/dev/null | wc -l | tr -d ' ')

# prune generations beyond KEEP_GENERATIONS. 自分のサブディレクトリ(claude-projects)
# だけを消す。$BACKUP_ROOT/<date>/ 全体は browser-state-backup.sh も共有しているので
# rm -rf してはいけない。
all_dates=""
for d in "$BACKUP_ROOT"/*/; do
  dtag="$(basename "$d")"
  [[ "$dtag" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || continue
  [ -d "$d/claude-projects" ] || continue
  all_dates="$all_dates$dtag"$'\n'
done
all_dates="$(printf '%s' "$all_dates" | grep -v '^$' | sort)"
total="$(printf '%s\n' "$all_dates" | grep -c . || true)"
if [ "$total" -gt "$KEEP_GENERATIONS" ]; then
  to_remove=$((total - KEEP_GENERATIONS))
  printf '%s\n' "$all_dates" | head -n "$to_remove" | while read -r old; do
    [ -n "$old" ] && rm -rf "${BACKUP_ROOT:?}/${old}/claude-projects" && _log "pruned old generation: $old"
  done
fi

if [ "$rc" -eq 0 ]; then
  _log "ok: date=$date_tag jsonl_in_backup=$count dest=$dest"
else
  _log "WARN: rsync exit=$rc date=$date_tag jsonl_in_backup=$count"
fi
if [ "$rc" -eq 0 ]; then ok=true; else ok=false; fi
echo "{\"ok\": $ok, \"date\": \"$date_tag\", \"jsonl_count\": $count, \"dest\": \"$dest\"}"
