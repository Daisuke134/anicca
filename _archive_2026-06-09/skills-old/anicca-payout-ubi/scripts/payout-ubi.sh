#!/usr/bin/env bash
# anicca-payout-ubi — cron entrypoint. Dry-run by default.
# Usage:
#   ./payout-ubi.sh                       # dry-run (default), exit 0
#   ./payout-ubi.sh --dry-run             # explicit dry-run
#   ./payout-ubi.sh --confirm             # without ANICCA_PAYOUT_LIVE=1 → refused-no-live-env
#   ANICCA_PAYOUT_LIVE=1 ./payout-ubi.sh --confirm   # REAL broadcast on Base
set -uo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$HOME/.hermes/state/payout.run.log"
mkdir -p "$HOME/.hermes/state"
# shellcheck disable=SC1090
[ -f "$HOME/.openclaw/.env" ] && set -a && . "$HOME/.openclaw/.env" && set +a
echo "=== payout-ubi $(date -u +%FT%TZ) $*" >> "$LOG"
/opt/homebrew/bin/timeout --kill-after=10 180 \
  /opt/homebrew/bin/python3 "$SKILL/scripts/payout-ubi.py" "$@"
RC=$?
echo "exit=$RC" >> "$LOG"
exit $RC
