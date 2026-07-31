#!/bin/bash
# Announce an unattended recovery. Runs once at login (i.e. once per boot).
#
# The point of the whole recovery setup is that nobody has to notice a blackout.
# This is the one thread back: a message that says the Mac came back on its own,
# so Dais learns about the outage instead of discovering dead loops hours later.
set +e

DIR=/Users/anicca/recovery-setup
STATE="$DIR/last-boot.txt"
LOG="$DIR/boot-notify.log"
TS=/opt/homebrew/bin/tailscale
mkdir -p "$DIR"

# Boot time is stable within a boot and changes across boots -- use it to fire once.
BOOT=$(sysctl -n kern.boottime 2>/dev/null | sed 's/.*sec = \([0-9]*\).*/\1/')
[ -z "$BOOT" ] && exit 0
PREV=$(cat "$STATE" 2>/dev/null)
[ "$BOOT" = "$PREV" ] && exit 0

# Wait for the network before trying to report; a boot notice that fails to send
# is worse than one that arrives a minute late.
for _ in $(seq 1 30); do
  /sbin/ping -c 1 -t 3 1.1.1.1 >/dev/null 2>&1 && break
  sleep 10
done

set -a; . /Users/anicca/.openclaw/.env 2>/dev/null; set +a
TG="$TELEGRAM_BOT_TOKEN"
CHAT="${TELEGRAM_ALERT_CHAT_ID:-8547730585}"
[ -z "$TG" ] && exit 0

BOOT_HUMAN=$(date -r "$BOOT" '+%Y-%m-%d %H:%M:%S')
NOW=$(date '+%H:%M:%S')

# Was this an unclean shutdown? Cause 5 is a normal restart; 0 and negative codes
# mean the power went away. `log show` also emits its own noise lines, so match the
# code strictly rather than trusting the last line.
CAUSE=$(log show --last 20m --predicate 'eventMessage CONTAINS "Previous shutdown cause"' \
  --style compact 2>/dev/null \
  | grep -oE 'Previous shutdown cause: -?[0-9]+' | tail -1 | grep -oE '\-?[0-9]+$')
case "$CAUSE" in
  5)  CAUSE_TXT="5 (通常の再起動)" ;;
  3)  CAUSE_TXT="3 (ハードリセット)" ;;
  0)  CAUSE_TXT="0 (電源断 ⚡)" ;;
  -*) CAUSE_TXT="$CAUSE (異常停止 ⚡)" ;;
  "") CAUSE_TXT="記録なし" ;;
  *)  CAUSE_TXT="$CAUSE" ;;
esac

# Give the loops a moment, then report what actually came back.
sleep 60
LANES=$(tail -1 "$DIR/health.log" 2>/dev/null)
AGENTS=$(launchctl list 2>/dev/null | grep -c '^[0-9-]')
TSSTAT=$(pgrep -x tailscaled >/dev/null 2>&1 && echo up || echo down)

MSG="🔌 Mac mini が自力で復帰しました

起動: $BOOT_HUMAN
通知: $NOW
直前の停止理由: $CAUSE_TXT

$LANES
launchd ジョブ: $AGENTS 本
tailscaled: $TSSTAT

誰も何もしていません。"

curl -s -X POST "https://api.telegram.org/bot${TG}/sendMessage" \
  -d chat_id="$CHAT" --data-urlencode "text=$MSG" >/dev/null 2>&1

echo "$BOOT" > "$STATE"
echo "$(date '+%Y-%m-%d %H:%M:%S') notified boot=$BOOT cause=$CAUSE_TXT" >> "$LOG"
