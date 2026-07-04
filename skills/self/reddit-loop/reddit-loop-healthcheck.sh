#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
# reddit-loop-healthcheck.sh — launchd supervisor (5min). Ported from life-manager-loop-healthcheck.sh.
set -uo pipefail
SOCK="/tmp/anicca-reddit-loop-tmux.sock"; SESSION="anicca-reddit-loop"
HB="$HOME/.openclaw/state/.reddit-loop-last-pass"; START="$HOME/.openclaw/state/.reddit-loop-last-start"; STALE_MIN=1560
LOG="$HOME/.openclaw/logs/reddit-loop-healthcheck.log"; mkdir -p "$(dirname "$LOG")"
RESTART_LOG="$HOME/.openclaw/state/.reddit-loop-restart-log"; REQ="$HOME/.openclaw/state/reddit-loop-selfheal-request.json"
LOCK_DIR="/tmp/.reddit-loop-healthcheck.lock"; mkdir "$LOCK_DIR" 2>/dev/null || exit 0; trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT
restart(){ mkdir -p "$HOME/.openclaw/state"; local now count=0; now=$(date +%s)
  if [ -f "$RESTART_LOG" ]; then while IFS= read -r ts; do [ -n "$ts" ] && [ $(( now - ts )) -le 3600 ] && count=$(( count+1 )); done < "$RESTART_LOG"; fi
  if [ "$count" -ge 5 ]; then echo "$(date '+%F %T') backoff $count/60min — delegating to loop" >> "$LOG"
    if [ ! -f "$REQ" ] || [ "$(( $(date +%s) - $(stat -f %m "$REQ" 2>/dev/null||echo 0) ))" -gt 3600 ]; then
      printf '{"loop":"reddit","ts":"%s","reason":"%s","restarts_last_60min":%d,"note":"healthcheck gave up. Next wake: diagnose+fix yourself, verify, rm this; else self/issue-dev then rm."}\n' "$(date -u +%FT%TZ)" "${1:-unknown}" "$count" > "$REQ" 2>/dev/null; fi; return; fi
  echo "$now" >> "$RESTART_LOG"; pkill -f "claude --name $SESSION" 2>/dev/null||true; pkill -f "tmux -S $SOCK new-session" 2>/dev/null||true; sleep 1
  echo "$(date '+%F %T') ${1:-DEAD} → restart" >> "$LOG"; bash "$HOME/anicca/skills/self/reddit-loop/reddit-loop-cli.sh" --restart >> "$LOG" 2>&1||true; }
if ! tmux -S "$SOCK" has-session -t "$SESSION" 2>/dev/null; then restart "reddit-loop DEAD"
elif [ ! -f "$HB" ]; then M="$(stat -f %m "$START" 2>/dev/null||date +%s)"; A="$(( ($(date +%s)-M)/60 ))"; [ "$A" -ge "$STALE_MIN" ] && restart "no pass in ${A}min" || echo "$(date '+%F %T') ALIVE (pending ${A}min)" >> "$LOG"
elif [ "$(( ($(date +%s)-$(stat -f %m "$HB" 2>/dev/null||date +%s))/60 ))" -ge "$STALE_MIN" ]; then restart "STALE"
else echo "$(date '+%F %T') ALIVE+fresh" >> "$LOG"; fi
