#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# life-manager-loop healthcheck — thin wrapper over the shared supervisor (FIND-011). launchd runs this every 5min.
# NOTE: LM's "real success" = a new paid Stripe subscriber, which is rare and cannot be a daily-freshness gate, so
# HC_OUTPUT is intentionally unset (liveness + stuck-detection only). Revenue truth is verified by verify-loops.sh.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
source "$LIFE_MANAGER_REPO/skills/self/healthcheck-lib.sh"
HC_LOOP="life-manager-loop" \
HC_SOCK="/tmp/anicca-life-manager-loop-tmux.sock" HC_SESSION="anicca-life-manager-loop" \
HC_HB="$HOME/.local/state/life-manager/state/.life-manager-loop-last-pass" HC_START="$HOME/.local/state/life-manager/state/.life-manager-loop-last-start" \
HC_STALE_MIN=1560 HC_CLI="$LIFE_MANAGER_REPO/skills/self/life-manager-loop/life-manager-loop-cli.sh" \
hc_run
