#!/usr/bin/env bash
MR_BOT_REPO="${MR_BOT_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$MR_BOT_REPO" ] || { echo "MR_BOT_REPO could not be resolved" >&2; exit 2; }
export MR_BOT_REPO
# mr-bot-loop healthcheck — thin wrapper over the shared supervisor (FIND-011). launchd runs this every 5min.
# NOTE: LM's "real success" = a new paid Stripe subscriber, which is rare and cannot be a daily-freshness gate, so
# HC_OUTPUT is intentionally unset (liveness + stuck-detection only). Revenue truth is verified by verify-loops.sh.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
source "$MR_BOT_REPO/skills/self/healthcheck-lib.sh"
HC_LOOP="mr-bot-loop" \
HC_SOCK="/tmp/anicca-mr-bot-loop-tmux.sock" HC_SESSION="anicca-mr-bot-loop" \
HC_HB="$HOME/.local/state/mr-bot/state/.mr-bot-loop-last-pass" HC_START="$HOME/.local/state/mr-bot/state/.mr-bot-loop-last-start" \
HC_STALE_MIN=1560 HC_CLI="$MR_BOT_REPO/skills/self/mr-bot-loop/mr-bot-loop-cli.sh" \
hc_run
