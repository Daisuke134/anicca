#!/usr/bin/env bash
# morning_report.sh — TG-3.2: post a summary of last night's + this morning's
# lateness calls to Slack #metrics (and Gmail if Slack absent). Pulls SID,
# timestamp, event summary, reason out of state/run.log; works no-LLM.
#
# Cron: bash morning_report.sh  every day at 09:00 JST (after the wake
# sequence has fully run).

set -uo pipefail
ANICCA_HOME="${ANICCA_HOME:-${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}}"
RUN_LOG="$ANICCA_HOME/skills/anicca-life-manager/state/run.log"
set -a; source "$ANICCA_HOME/.env" 2>/dev/null; set +a

today=$(date +%Y-%m-%d)
yesterday=$(date -v-1d +%Y-%m-%d)

if [ ! -f "$RUN_LOG" ]; then
  echo "[morning_report] no run.log yet — nothing to report"; exit 0
fi

# Extract today's + yesterday's lateness-fire blocks
hits=$(/opt/homebrew/bin/python3 - "$RUN_LOG" "$today" "$yesterday" <<'PY'
import sys, re, json
log, today, yesterday = sys.argv[1], sys.argv[2], sys.argv[3]
calls = []
current_ts = None
current_event = None
with open(log, errors="ignore") as f:
    for line in f:
        m = re.match(r"=== lateness run (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", line)
        if m:
            current_ts = (m.group(1), m.group(2))
            current_event = None
            continue
        if not current_ts:
            continue
        if current_ts[0] not in (today, yesterday):
            continue
        try:
            d = json.loads(line.strip())
            if d.get("action") == "call":
                current_event = d.get("event") or "(unknown)"
        except Exception:
            pass
        m_sid = re.search(r"placed lateness call sid=(\w+)", line)
        if m_sid:
            calls.append((current_ts[0], current_ts[1],
                          (current_event or "")[:50],
                          m_sid.group(1)))
for c in calls:
    print("\t".join(c))
PY
)

# Build report
report="📞 Morning verify — $today"$'\n\n'
if [ -z "$hits" ]; then
  report+="(= no lateness calls in the last 24 h — quiet hours / no events)"
else
  while IFS=$'\t' read -r d t event sid; do
    report+="• ${d} ${t}  ${event}  (sid ${sid})"$'\n'
  done <<< "$hits"
fi
report+=$'\n'"Run-log lines: $(wc -l < "$RUN_LOG" | tr -d ' ')"

# Post to Slack if configured
if [ -n "${SLACK_BOT_TOKEN:-}" ] && [ -n "${SLACK_METRICS_CHANNEL:-${SLACK_REPORT_CHANNEL:-}}" ]; then
  channel="${SLACK_METRICS_CHANNEL:-${SLACK_REPORT_CHANNEL}}"
  /opt/homebrew/bin/curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$(jq -n --arg c "$channel" --arg t "$report" '{channel:$c,text:$t}')" \
    >/dev/null 2>&1 || true
fi

# Always echo so the cron run-log captures it too
echo "$report"
