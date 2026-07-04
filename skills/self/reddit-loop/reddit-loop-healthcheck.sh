#!/usr/bin/env bash
# reddit-loop healthcheck — thin wrapper over the shared supervisor (FIND-011). launchd runs this every 5min.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
source "$HOME/anicca/skills/self/healthcheck-lib.sh"
HC_LOOP="reddit-loop" \
HC_SOCK="/tmp/anicca-reddit-loop-tmux.sock" HC_SESSION="anicca-reddit-loop" \
HC_HB="$HOME/.openclaw/state/.reddit-loop-last-pass" HC_START="$HOME/.openclaw/state/.reddit-loop-last-start" \
HC_STALE_MIN=1560 HC_CLI="$HOME/anicca/skills/self/reddit-loop/reddit-loop-cli.sh" \
HC_OUTPUT="$HOME/anicca/skills/self/reddit-loop/state/posts.jsonl" HC_OUTPUT_STALE_HRS=30 \
HC_SELFFIX_HINT="reddit loop makes no real post (posts.jsonl not growing) — likely stuck on account provisioning or the ethics fork; find the honest autonomous path and make it post." \
hc_run
