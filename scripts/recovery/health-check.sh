#!/bin/bash
# Post-blackout resilience monitor.
# Runs every minute as a LaunchAgent. Checks the three things that must be true
# for the iPhone to reach this Mac, and repairs only what is actually broken.
#
# Deliberately conservative: a repair that fires on a healthy component is worse
# than no repair at all (a keepalive that killed healthy daemons is exactly what
# took the phone offline on 2026-07-31).
set +e

DIR=/Users/anicca/recovery-setup
LOG="$DIR/health.log"
TS=/opt/homebrew/bin/tailscale
CODEX=/Users/anicca/.local/bin/codex
STATUS_PY=/Users/anicca/.codex-remote-status.py
PY=/usr/bin/python3
TIMEOUT=/opt/homebrew/bin/timeout
[ -x "$TIMEOUT" ] || TIMEOUT=""

mkdir -p "$DIR"
unset OPENAI_API_KEY ANTHROPIC_API_KEY

stamp() { date '+%Y-%m-%d %H:%M:%S'; }
say() { echo "$(stamp) $*" >> "$LOG"; }

problems=0

# 1. Internet reachability -------------------------------------------------
if /sbin/ping -c 1 -t 5 1.1.1.1 >/dev/null 2>&1; then
  net=ok
else
  net=DOWN
  problems=$((problems + 1))
fi

# 2. Tailscale (the path the phone and I use to reach this box) -------------
if [ -x "$TS" ]; then
  if "$TS" status >/dev/null 2>&1; then
    ts=ok
  else
    ts=DOWN
    problems=$((problems + 1))
    "$TS" up >/dev/null 2>&1 && ts=recovered
  fi
else
  ts=absent
fi

# 3. Codex remote-control for both ChatGPT accounts -------------------------
codex_status() {
  home="$1"
  out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
  st=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)
  # Only the "unmanaged app-server" case justifies killing a live daemon.
  if printf '%s' "$out" | grep -q 'not managed by codex app-server daemon'; then
    for p in $(pgrep -f 'app-server'); do
      if ps eww -p "$p" 2>/dev/null | tr ' ' '\n' | grep -q "CODEX_HOME=$home"; then
        kill -9 "$p" 2>/dev/null
      fi
    done
    rm -f "$home/app-server-daemon/app-server.pid" 2>/dev/null
    sleep 3
    out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
    st=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)
  fi
  echo "${st:-empty}"
}

c1=$(codex_status /Users/anicca/.codex)
c2=$(codex_status /Users/anicca/.codex-acct2)
[ "$c1" = "connected" ] || problems=$((problems + 1))
[ "$c2" = "connected" ] || problems=$((problems + 1))

# 4. Claude Remote Control --------------------------------------------------
cpid=$(launchctl list 2>/dev/null | awk '/com.anicca.claude-remote-control/{print $1}')
if [ -n "$cpid" ] && [ "$cpid" != "-" ]; then
  conns=$(lsof -nP -p "$cpid" 2>/dev/null | grep -c ESTABLISHED)
  if [ "$conns" -ge 1 ]; then
    claude=ok
  else
    claude=no_conn
    problems=$((problems + 1))
    launchctl kickstart -k gui/501/com.anicca.claude-remote-control >/dev/null 2>&1
  fi
else
  claude=DOWN
  problems=$((problems + 1))
  launchctl bootstrap gui/501 \
    /Users/anicca/Library/LaunchAgents/com.anicca.claude-remote-control.plist >/dev/null 2>&1
fi

say "net=$net ts=$ts codex1=$c1 codex2=$c2 claude=$claude problems=$problems"

# Rotate: keep the log bounded so a wedged loop cannot fill the disk.
if [ "$(wc -l < "$LOG" 2>/dev/null || echo 0)" -gt 5000 ]; then
  tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
