#!/usr/bin/env bash
# capafy-loop healthcheck — thin wrapper over the shared supervisor (FIND-011). launchd runs this every 5min.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
source "$HOME/anicca/skills/self/healthcheck-lib.sh"
HC_LOOP="capafy-loop" \
HC_SOCK="/tmp/anicca-capafy-loop-tmux.sock" HC_SESSION="anicca-capafy-loop" \
HC_HB="$HOME/.openclaw/state/.capafy-loop-last-pass" HC_START="$HOME/.openclaw/state/.capafy-loop-last-start" \
HC_STALE_MIN=1560 HC_CLI="$HOME/anicca/skills/self/capafy-loop/capafy-loop-cli.sh" \
HC_OUTPUT="$HOME/.openclaw/skills/capafy-autopublish/state/published.jsonl" HC_OUTPUT_STALE_HRS=30 \
HC_SELFFIX_HINT="capafy publish pipeline produces no new skill (published.jsonl not growing). Likely drive_cp1.py CP1 broken." \
hc_run
