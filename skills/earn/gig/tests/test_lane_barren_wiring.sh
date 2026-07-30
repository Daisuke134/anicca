#!/usr/bin/env bash
# X7: the barren-lane alarm is wired into the single per-pass choke point and
# actually reaches the Telegram outbox.
#
# The unit tests prove the streak arithmetic and the outbox dedupe. These prove the
# whole chain: three ledger-measured barren attempts -> lane_health state ->
# `telegram_report.py lane-barren` -> one real outbox dispatch through a stub
# openclaw -> a second run sends nothing. And they pin the call site: exactly one
# invocation, in launch_gig_worker.sh after the pass report, never fatal, stderr to
# ~/gig/.lane-health.err.log -- the alarm must ride the one path every pass takes.
set -uo pipefail

G="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LH="$G/scripts/lane_health.py"
TR="$G/scripts/telegram_report.py"
LAUNCHER="$G/scripts/launch_gig_worker.sh"
fails=0
check() {
  if [ "$2" = "$3" ]; then echo "PASS  $1"
  else echo "FAIL  $1  expected=$2 got=$3"; fails=$((fails+1)); fi
}

WORK="$(mktemp -d)"
export GIG_STATE_DIR="$WORK/gig"
export GIG_REPORT_CHAT="fixture-chat"
TELEGRAM_DB="$WORK/telegram.sqlite3"
SENDS_LOG="$WORK/openclaw-sends.log"

# Stub openclaw: records every send and returns a well-formed ACK.
FAKE_OPENCLAW="$WORK/openclaw"
cat > "$FAKE_OPENCLAW" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$SENDS_LOG"
printf '{"payload":{"ok":true},"messageId":"stub-%s"}\n' "\$\$"
EOF
chmod +x "$FAKE_OPENCLAW"

# --- build the outage shape from measured state: 3 attempts, ledger gains nothing --
for _ in 1 2 3; do
  python3 "$LH" record apply success --detail "barren-wiring" >/dev/null
done
streak="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["barren_streak"])' \
  "$GIG_STATE_DIR/state/lanes/apply.json" 2>/dev/null || echo missing)"
check "three unproductive attempts leave a measured streak of 3" 3 "$streak"

# --- first pass through the hook command sends exactly one alert -------------------
out1="$(python3 "$TR" lane-barren --telegram-database "$TELEGRAM_DB" \
  --openclaw "$FAKE_OPENCLAW" 2>"$WORK/first.err")"
rc1=$?
check "lane-barren exits 0 on send" 0 "$rc1"
check "first run reports one sent" '{"sent":1,"delivery_unknown":0}' "$out1"
check "the stub transport saw exactly one send" 1 "$(grep -c . "$SENDS_LOG" 2>/dev/null || echo 0)"

# readback: the alert exists as a durable outbox row, keyed by lane + streak anchor.
row_state="$(sqlite3 "$TELEGRAM_DB" \
  "SELECT state FROM telegram_reports WHERE event_key LIKE 'gig:telegram:lane-barren:v1:apply:%'")"
check "the outbox holds the sent barren alert row" sent "$row_state"

# --- same streak, next pass: the outbox dedupe swallows the repeat -----------------
out2="$(python3 "$TR" lane-barren --telegram-database "$TELEGRAM_DB" \
  --openclaw "$FAKE_OPENCLAW" 2>"$WORK/second.err")"
check "second run within the same streak sends nothing" '{"sent":0,"delivery_unknown":0}' "$out2"
check "the stub transport still saw only one send" 1 "$(grep -c . "$SENDS_LOG")"

# --- recovery silences the alarm, and no recovery notification is emitted ----------
python3 "$LH" productive apply --records 2 --detail "barren-wiring-recovery" >/dev/null
out3="$(python3 "$TR" lane-barren --telegram-database "$TELEGRAM_DB" \
  --openclaw "$FAKE_OPENCLAW" 2>"$WORK/third.err")"
check "after recovery nothing is sent" '{"sent":0,"delivery_unknown":0}' "$out3"

# --- launcher wiring: one invocation, at the per-pass choke point, never fatal -----
bash -n "$LAUNCHER"
check "launch_gig_worker.sh parses" 0 "$?"
check "the launcher invokes lane-barren exactly once" 1 "$(grep -c 'lane-barren' "$LAUNCHER")"
barren_line="$(grep -n 'lane-barren' "$LAUNCHER" | head -1 | cut -d: -f1)"
pass_line="$(grep -n 'telegram_report\.py" pass' "$LAUNCHER" | head -1 | cut -d: -f1)"
check "the alarm rides the same choke point, after the pass report" yes \
  "$([ -n "$barren_line" ] && [ -n "$pass_line" ] && [ "$barren_line" -gt "$pass_line" ] && echo yes || echo "no(barren=${barren_line:-none} pass=${pass_line:-none})")"
hook_block="$(sed -n "${barren_line:-0},$((${barren_line:-0}+1))p" "$LAUNCHER")"
case "$hook_block" in
  *"|| true"*) never_fatal=yes ;;
  *) never_fatal=no ;;
esac
check "the alarm can never fail the pass exit path" yes "$never_fatal"
case "$hook_block" in
  *".lane-health.err.log"*) err_routed=yes ;;
  *) err_routed=no ;;
esac
check "alarm stderr goes to ~/gig/.lane-health.err.log" yes "$err_routed"

echo
[ "$fails" -gt 0 ] && { echo "$fails failed"; exit 1; }
echo "all lane barren wiring tests passed"
