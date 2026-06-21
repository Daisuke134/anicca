#!/bin/bash
# 24/7 UBI payout daemon wrapper (run by launchd, KeepAlive).
# Sources secrets, then runs the watcher in --loop mode. NOT a session/background hack.
set -a
. "$HOME/.openclaw/.env" 2>/dev/null
set +a
export UBI_STIPEND_BASE="${UBI_STIPEND_BASE:-250000}"   # $0.25 per recipient
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
exec /opt/homebrew/bin/node "$HOME/anicca/skills/ubi/ubi-payout-watcher.mjs" --loop
