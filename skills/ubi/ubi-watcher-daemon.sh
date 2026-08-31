#!/bin/bash
MR_BOT_REPO="${MR_BOT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$MR_BOT_REPO" ] || { echo "MR_BOT_REPO could not be resolved" >&2; exit 2; }
export MR_BOT_REPO
# 24/7 UBI payout daemon wrapper (run by launchd, KeepAlive).
# Sources secrets, then runs the watcher in --loop mode. NOT a session/background hack.
set -a
. "$HOME/.local/state/mr-bot/.env" 2>/dev/null
set +a
export UBI_STIPEND_BASE="${UBI_STIPEND_BASE:-250000}"   # $0.25 per recipient
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
exec /opt/homebrew/bin/node "$MR_BOT_REPO/skills/ubi/ubi-payout-watcher.mjs" --loop
