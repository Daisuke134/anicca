#!/usr/bin/env bash
# The deaths no flag explains -- a crash, a hang, an unloaded LaunchAgent -- leave
# the stop flag clear and the launcher perfectly happy. The only witness is the
# pass's own completion heartbeat. Drive the real CLI against a backdated one and
# assert it alerts exactly once, then recovers exactly once.
# Everything lives in $TMP: no live outbox row, no real Telegram send.
set -euo pipefail

SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
REPORT="$SKILL_DIR/scripts/telegram_report.py"
AUDITOR="$SKILL_DIR/auditor.sh"
PY=/opt/homebrew/bin/python3
TMP=$(mktemp -d /tmp/gig-pass-silence.XXXXXX)
trap 'rm -rf "$TMP"' EXIT

GIG="$TMP/gig"
DB="$GIG/telegram-outbox.sqlite3"
HEARTBEAT="$GIG/.last-pass"
mkdir -p "$GIG" "$TMP/bin"

cat > "$TMP/bin/openclaw" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$OPENCLAW_STUB_LOG"
printf '{"messageId":"stub-%s"}\n' "$RANDOM"
EOF
chmod +x "$TMP/bin/openclaw"
export OPENCLAW_STUB_LOG="$TMP/openclaw-stub.log"
: > "$OPENCLAW_STUB_LOG"

test -f "$REPORT" || { echo 'missing telegram_report.py'; exit 1; }
grep -F 'telegram_report.py" pass-silence' "$AUDITOR" >/dev/null || {
  echo 'the auditor does not run the silence alarm; detection would stay in the log'
  exit 1
}

silence() {
  "$PY" "$REPORT" pass-silence \
    --gig-dir "$GIG" --telegram-database "$DB" --openclaw "$TMP/bin/openclaw" \
    | tee -a "$TMP/silence.log"
}

rows() {
  "$PY" - "$DB" "$1" <<'EOF'
import sqlite3, sys
from pathlib import Path
database, kind = Path(sys.argv[1]), sys.argv[2]
if not database.exists():
    print(0)
    raise SystemExit(0)
print(sqlite3.connect(database).execute(
    "SELECT COUNT(*) FROM telegram_reports WHERE kind=?", (kind,)
).fetchone()[0])
EOF
}

# A pass finished a minute ago: the loop is healthy and must stay silent.
touch "$HEARTBEAT"
silence | grep -q '"action":"none"' || { echo 'a healthy loop raised a false alarm'; exit 1; }
test "$(rows pass_outage)" -eq 0

# Backdate the heartbeat past the threshold: nothing has finished in ten hours.
BACKDATED=$(( $(date +%s) - 36000 ))
touch -t "$(date -r "$BACKDATED" +%Y%m%d%H%M.%S)" "$HEARTBEAT"
silence | grep -q '"action":"opened"' || { echo 'a ten-hour silence went unreported'; exit 1; }
test "$(rows pass_outage)" -eq 1

# The next hourly audit sees the same silence and must not repeat itself.
silence | grep -q '"action":"none"' || { echo 'the silence alarm repeated per audit'; exit 1; }
test "$(rows pass_outage)" -eq 1 || { echo 'a second outage row landed'; exit 1; }

# A pass completes: the heartbeat is fresh and recovery is announced exactly once.
touch "$HEARTBEAT"
silence | grep -q '"action":"recovered"' || { echo 'recovery was never announced'; exit 1; }
test "$(rows pass_recovered)" -eq 1
silence | grep -q '"action":"none"' || { echo 'recovery was announced twice'; exit 1; }
test "$(rows pass_recovered)" -eq 1

# A configurable threshold must be able to tighten the alarm, never to disable it.
touch "$HEARTBEAT"
GIG_PASS_SILENCE_SECONDS=1 "$PY" "$REPORT" pass-silence \
  --gig-dir "$GIG" --telegram-database "$DB" --openclaw "$TMP/bin/openclaw" > "$TMP/tight.json"
BACKDATED=$(( $(date +%s) - 60 ))
touch -t "$(date -r "$BACKDATED" +%Y%m%d%H%M.%S)" "$HEARTBEAT"
GIG_PASS_SILENCE_SECONDS=1 "$PY" "$REPORT" pass-silence \
  --gig-dir "$GIG" --telegram-database "$DB" --openclaw "$TMP/bin/openclaw" \
  | grep -q '"action":"opened"' || { echo 'GIG_PASS_SILENCE_SECONDS did not tighten the alarm'; exit 1; }

"$PY" - "$DB" <<'EOF'
import sqlite3, sys
from pathlib import Path
rows = sqlite3.connect(Path(sys.argv[1])).execute(
    "SELECT kind,message,state FROM telegram_reports ORDER BY report_id"
).fetchall()
assert rows, "no rows produced"
for kind, message, state in rows:
    assert state == "sent", f"{kind} never reached the transport: {state}"
    for jargon in ("78", "exit", "lane", "pass_id", "SLO", "heartbeat"):
        assert jargon not in message, f"{jargon!r} leaked into {kind}: {message}"
    print(f"--- {kind} ({state}) ---\n{message}")
EOF

echo 'PASS: a pass that stops finishing is announced once, and its recovery once'
