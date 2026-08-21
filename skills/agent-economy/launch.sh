#!/usr/bin/env bash
set -euo pipefail

REPO="${ANICCA_REPO:-${LIFE_MANAGER_REPO:-$HOME/loops/current}}"
case "$REPO" in
  */.worktrees/*)
    echo "agent-economy: refusing worktree runtime path: $REPO" >&2
    exit 2
    ;;
esac
[ -x "$REPO/runtime/anicca-daemon.sh" ] || {
  echo "agent-economy: missing daemon at $REPO/runtime/anicca-daemon.sh" >&2
  exit 2
}

export ANICCA_REPO="$REPO"
if [ "${ANICCA_ECONOMY_CREATE_EVM_WALLET:-0}" = "1" ]; then
  /usr/bin/env node "$REPO/runtime/compute-proxy/ensure-wallet.mjs" >/dev/null
fi
exec /bin/bash "$REPO/runtime/anicca-daemon.sh"
