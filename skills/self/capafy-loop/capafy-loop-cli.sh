#!/usr/bin/env bash
# Compatibility entrypoint: the single production owner is launchd.
set -euo pipefail

MR_BOT_REPO="${MR_BOT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$MR_BOT_REPO" ] || { echo "MR_BOT_REPO could not be resolved" >&2; exit 2; }
CONTROL="${CAPAFY_LAUNCHCTL_SAFE:-$MR_BOT_REPO/bin/launchctl-safe}"
TARGET="${CAPAFY_LAUNCHCTL_DOMAIN:-gui/$(id -u)}/ai.anicca.capafy-loop-daily"

case "${1:-}" in
  --status)
    "$CONTROL" print "$TARGET" >/dev/null
    echo "capafy-loop launchd owner loaded"
    ;;
  ""|--restart)
    "$CONTROL" preflight >/dev/null
    "$CONTROL" kickstart "$TARGET" >/dev/null
    echo "capafy-loop launchd owner kicked"
    ;;
  *)
    echo "usage: $0 [--status|--restart]" >&2
    exit 2
    ;;
esac
