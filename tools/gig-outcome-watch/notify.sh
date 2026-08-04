#!/usr/bin/env bash
# Run the outcome watch and tell Dais only when something is wrong.
#
# Intentionally outside skills/gig-work: the loop must not be able to edit the thing that
# judges it. Also intentionally dumb — no model call, no browser, so it cannot fail for the
# same reasons the loop fails.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-/opt/homebrew/bin/python3}"
STATE="$HOME/.local/state/anicca/gig-outcome-watch"
mkdir -p "$STATE"

set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
CHAT_ID="${GIG_WATCH_CHAT_ID:-8547730585}"

json="$("$PY" "$HERE/outcome_watch.py" --window-hours "${WINDOW_HOURS:-24}" --json 2>/dev/null)"
text="$("$PY" "$HERE/outcome_watch.py" --window-hours "${WINDOW_HOURS:-24}" 2>/dev/null)"
rc=$?

printf '%s\n' "$json" >> "$STATE/history.jsonl"

alerts="$(printf '%s' "$json" | "$PY" -c 'import json,sys; print(",".join(json.load(sys.stdin)["alerts"]))' 2>/dev/null)"
if [ -z "$alerts" ]; then
  echo "ok: no alerts"
  exit 0
fi

# One message per alert-set per day: a detector that repeats itself hourly gets muted by
# the human, and a muted detector is the same as no detector.
stamp="$(date +%F)-${alerts}"
if [ -f "$STATE/last-sent" ] && [ "$(cat "$STATE/last-sent")" = "$stamp" ]; then
  echo "suppressed duplicate: $stamp"
  exit 0
fi

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  curl -sS -m 30 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${CHAT_ID}" \
    --data-urlencode "text=${text}" >/dev/null 2>&1 \
    && printf '%s' "$stamp" > "$STATE/last-sent" \
    && echo "sent: $alerts"
else
  echo "no TELEGRAM_BOT_TOKEN; alerts=$alerts" >&2
fi
exit 0
