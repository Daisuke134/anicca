#!/usr/bin/env bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# capafy-loop healthcheck — thin wrapper over the shared supervisor (FIND-011). launchd runs this every 5min.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
source "$LIFE_MANAGER_REPO/skills/self/healthcheck-lib.sh"
HC_LOOP="capafy-loop" \
HC_SOCK="/tmp/anicca-capafy-loop-tmux.sock" HC_SESSION="anicca-capafy-loop" \
HC_HB="$HOME/.local/state/life-manager/state/.capafy-loop-last-pass" HC_START="$HOME/.local/state/life-manager/state/.capafy-loop-last-start" \
HC_STALE_MIN=1560 HC_CLI="$LIFE_MANAGER_REPO/skills/self/capafy-loop/capafy-loop-cli.sh" \
HC_OUTPUT="$LIFE_MANAGER_REPO/skills/capafy-autopublish/state/.capafy-healthy-pass" HC_OUTPUT_STALE_HRS=30 \
HC_SELFFIX_HINT="capafy publish loop reached NO healthy terminal state in >30h. daily_loop.sh touches .capafy-healthy-pass on every healthy pass — a real publish OR a correctly-drained/cap-full idle run (this is a DRAIN-ONLY loop over finite inventory; 'no new skill' is NOT itself a bug). A stale marker means the loop is genuinely stuck: daily_loop.sh not running, Capafy auth/network down (SERVER_UNREADABLE), or a PUBLISHABLE item whose publish keeps failing (CP1 cp1_agent.py -> CP2 -> CP3). Read state/daily_loop.log for the last verdict; do NOT assume drive_cp1.py is broken." \
hc_run
