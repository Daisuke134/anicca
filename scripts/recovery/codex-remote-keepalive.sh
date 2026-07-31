#!/bin/bash
# Keep BOTH ChatGPT accounts' Codex remote-control daemons connected so the
# phone always sees the Mac online. Runs at login and every 5 minutes;
# `remote-control start` is idempotent (returns alreadyRunning when healthy).
set +e
CODEX=/Users/anicca/.local/bin/codex
STATUS_PY=/Users/anicca/.codex-remote-status.py
PY=/usr/bin/python3
LOG=/Users/anicca/.codex-remote-keepalive.log
# launchd runs with a bare PATH; `timeout` is Homebrew coreutils, not /usr/bin.
TIMEOUT=/opt/homebrew/bin/timeout
[ -x "$TIMEOUT" ] || TIMEOUT=""

# Never let API-key auth shadow the ChatGPT subscription login.
unset OPENAI_API_KEY ANTHROPIC_API_KEY

stamp() { date '+%Y-%m-%d %H:%M:%S'; }

ensure() {
  home="$1"
  label="$2"

  out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
  status=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)

  # Only ONE failure mode justifies killing a live daemon: an app-server the
  # daemon no longer manages. Everything else (transient, connecting, an
  # unparsed status) is left alone -- killing a healthy daemon is exactly what
  # takes the phone offline.
  if printf '%s' "$out" | grep -q 'not managed by codex app-server daemon'; then
    for p in $(pgrep -f 'app-server'); do
      if ps eww -p "$p" 2>/dev/null | tr ' ' '\n' | grep -q "CODEX_HOME=$home"; then
        kill -9 "$p" 2>/dev/null
      fi
    done
    rm -f "$home/app-server-daemon/app-server.pid" 2>/dev/null
    sleep 3
    out=$(CODEX_HOME="$home" $TIMEOUT ${TIMEOUT:+90} "$CODEX" remote-control start --json 2>&1)
    status=$(printf '%s' "$out" | "$PY" "$STATUS_PY" 2>/dev/null)
  fi

  echo "$(stamp) $label status=${status:-empty}" >> "$LOG"
}

ensure /Users/anicca/.codex "acct1(keiodaisuke)"
ensure /Users/anicca/.codex-acct2 "acct2(daisukenarita53)"

tail -n 500 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
