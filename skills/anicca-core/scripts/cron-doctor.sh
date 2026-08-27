#!/usr/bin/env bash
# cron-doctor.sh — DETECTOR ONLY (Sutando friction-detector style).
#
# Does NOT fix anything. It gathers the FULL fault context for every cron in
# error/failed state and prints a "fault brief" for the heartbeat LLM (§3.5) to
# read, diagnose, and actually fix. Hardcoded fixes were removed 2026-05-25
# because they (a) mistook false-errors (posted OK but Slack-delivery failed) for
# real failures and (b) treated symptoms (timeout→900) not root causes.
#
# Per error cron it collects:
#   - name / id / schedule
#   - openclaw cron runs --id  →  error  +  summary (has post URLs / real result)
#                                 +  sessionKey (full session log handle)
#   - cron/runs/<name>.jsonl    →  last lines of the raw run log
# The LLM then decides false-vs-real, fixes the root cause, re-runs unposted
# social crons (`openclaw cron run <id>`), and reports "fixed X by Y".
#
# Usage: cron-doctor.sh        # print fault brief to stdout (for the beat)
# 2026-05-27: fixed O(N) openclaw-cron-list calls → 1 call; added timeouts throughout;
#             capped at 20 crons to prevent heartbeat hangs when many errors exist.
set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
MAX_CRONS=20  # cap to prevent heartbeat context explosion

# Single cron list call (with timeout to prevent hang)
LISTFILE=$(mktemp)
timeout 30 openclaw cron list 2>/dev/null > "$LISTFILE" || true

# Extract error cron IDs (first column) and names (second column)
ERRFILE=$(mktemp)
grep -iE "\berror\b" "$LISTFILE" | awk '{print $1, $2}' > "$ERRFILE"
ERRCOUNT=$(wc -l < "$ERRFILE" | tr -d ' ')

if [ "$ERRCOUNT" -eq 0 ]; then
  echo "cron-doctor: 0 error crons. nothing to diagnose."
  rm -f "$ERRFILE" "$LISTFILE"
  exit 0
fi

echo "🔧 cron-doctor DETECTED ${ERRCOUNT} cron(s) in error. §3.5 で1件ずつ診断・実修復せよ:"
echo "（status=error でも summary に投稿URL/成功があれば偽ok=配信だけ直す。本物は根本修正+未投稿は cron run で再実行。）"
if [ "$ERRCOUNT" -gt "$MAX_CRONS" ]; then
  echo "（多数エラー: 最初の${MAX_CRONS}件のみ表示。残り$((ERRCOUNT - MAX_CRONS))件は同様の transient と推定。）"
fi
echo ""

COUNT=0
while IFS=' ' read -r id name; do
  [ -z "$id" ] && continue
  [ "$COUNT" -ge "$MAX_CRONS" ] && break
  COUNT=$((COUNT + 1))
  echo "────────────────────────────────────────────────────────"
  echo "■ $name  ($id)"
  # full run record: error + summary(投稿URL/実結果) + sessionKey
  timeout 10 openclaw cron runs --id "$id" 2>/dev/null | python3 -c "
import json,sys,datetime
try: e=(json.load(sys.stdin).get('entries') or [{}])[0]
except Exception: e={}
ts=e.get('runAtMs')
when=datetime.datetime.fromtimestamp(int(ts)/1000).strftime('%m-%d %H:%M') if ts else '?'
print(f'  lastRun: {when}  status={e.get(\"status\",\"?\")}')
print(f'  error  : {(e.get(\"error\") or \"\")[:240]}')
print(f'  summary: {(e.get(\"summary\") or \"\")[:500]}')   # ←偽ok判定の鍵（投稿URL/成功ならば偽ok）
print(f'  session: {e.get(\"sessionKey\",\"\")}')
" 2>/dev/null || echo "  (runs fetch timed out)"
  # raw run log tail
  rl="$ANICCA_HOME/cron/runs/$name.jsonl"
  [ -f "$rl" ] && echo "  recent-log:" && tail -3 "$rl" 2>/dev/null | sed 's/^/    /'
done < "$ERRFILE"
rm -f "$ERRFILE" "$LISTFILE"
echo "────────────────────────────────────────────────────────"
echo "↑ 各件を §3.5 の手順で実修復し、#metrics に「原因→修正→(再実行)結果」を報告。"
