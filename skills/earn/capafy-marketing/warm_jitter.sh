#!/usr/bin/env bash
# warm_jitter.sh — human-like timing: sleep a random 0-3h before running the warmup, so the daily
# warmup does NOT fire at the exact same clock time every day. launchd fires this at a base time;
# the random sleep spreads the actual run across a window.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=account_state.sh
. "$SCRIPT_DIR/account_state.sh"
ACCOUNTS_FILE="$(capafy_ig_accounts_file)"
IG_HANDLE="$(resolve_capafy_ig_handle "$ACCOUNTS_FILE")"
if [ -z "$IG_HANDLE" ]; then
  echo "capafy warmup: no active account -> PROVISION on daily pass" >&2
  exit 0
fi
sleep $(( RANDOM % 10800 ))   # 0..10800s = 0..3h jitter
exec /opt/homebrew/bin/python3 "$HOME/anicca/skills/earn/marketing-engine/warmer.py" "$ACCOUNTS_FILE"
